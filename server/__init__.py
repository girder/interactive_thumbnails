import json
from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import filtermodel, getCurrentUser, RestException
from girder.constants import AccessType, TokenScope
from girder.models.file import File
from girder.models.item import Item
from girder.models.token import Token
from girder.plugins.jobs.models.job import Job
from girder.plugins.worker.utils import girderInputSpec, girderOutputSpec, jobInfoSpec
from girder_worker.docker.tasks import docker_run
from girder_worker.docker.transforms import VolumePath
from girder_worker.docker.transforms.girder import (
    GirderFileIdToVolume, GirderUploadVolumePathToItem)


_PHI_SAMPLES = 12
_THETA_SAMPLES = 3
_SIZE = 256
_CREATE_TASK = {
    'mode': 'docker',
    'docker_image': 'zachmullen/3d_thumbnails:latest',
    'container_args': [
        '--phi-samples', str(_PHI_SAMPLES),
        '--theta-samples', str(_THETA_SAMPLES),
        '--width', str(_SIZE),
        '--height', str(_SIZE),
        '$input{in}', '$output{out}'
    ],
    'inputs': [{
        'id': 'in',
        'target': 'filepath'
    }],
    'outputs': [{
        'id': 'out',
        'target': 'filepath'
    }]
}


def _handleUpload(event):
    upload, file = event.info['upload'], event.info['file']

    try:
        reference = json.loads(upload.get('reference'))
    except (TypeError, ValueError):
        return

    if isinstance(reference, dict) and 'interactive_thumbnail' in reference:
        item = Item().load(file['itemId'], force=True, exc=True)

        file['interactive_thumbnails_uid'] = file['name']
        file['attachedToId'] = item['_id']
        file['attachedToType'] = 'item'
        file['itemId'] = None
        File().save(file)

        if not item.get('hasInteractiveThumbnail'):
            Item().update({'_id': item['_id']}, {'$set': {
                'hasInteractiveThumbnail': True
            }}, multi=False)


def _removeThumbnails(item, saveItem=False):
    rm = File().remove

    for file in File().find({'attachedToId': item['_id']}):
        if 'interactive_thumbnails_uid' in file:
          rm(file)

    if saveItem:
        Item().update({'_id': item['_id']}, {'$set': {'hasInteractiveThumbnail': False}}, multi=False)


@access.cookie
@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Download an interactive thumbnail image for a given item.')
    .modelParam('id', model=Item, level=AccessType.READ)
    .param('uid', 'The UID (path) of the thumbnail file to retrieve.', paramType='path')
)
def _getThumbnail(item, uid):
    file = File().findOne({
        'attachedToId': item['_id'],
        'interactive_thumbnails_uid': uid
    })
    if not file:
        raise RestException('No such thumbnail for uid "%s".' % uid)

    return File().download(file)


@access.user(scope=TokenScope.DATA_WRITE)
@filtermodel(Job)
@autoDescribeRoute(
    Description('Generate a new set of interactive thumbnail images for an item.')
    .modelParam('id', model=Item, level=AccessType.WRITE)
    .param('preset', 'Volume rendering transfer function preset to use.',
           default='default', enum=('default', 'CT-AAA', 'CT-Bones', 'CT-Soft-Tissue'))
)
def _createThumbnail(item, preset):
    files = Item().childFiles(item, limit=2)
    if files.count() != 1:
        raise Exception('Can only generate thumbnails for items containing one file.')

    # Remove previously attached thumbnails
    _removeThumbnails(item, saveItem=True)

    user = getCurrentUser()

    # Schedule a job to produce new thumbnails
    jm = Job()
    job = jm.createJob(
        title='Interactive thumbnail creation: %s' % item['name'], type='interactive_thumbnails',
        handler='worker_handler', user=user)
    token = Token().createToken(user, days=3, scope={TokenScope.DATA_READ, TokenScope.DATA_WRITE})

    """outdir = VolumePath('__thumbnails_output__')
    return docker_run.delay('zachmullen/3d_thumbnails:latest', container_args=[
        '--phi-samples', str(_PHI_SAMPLES),
        '--theta-samples', str(_THETA_SAMPLES),
        '--width', str(_SIZE),
        '--height', str(_SIZE),
        '--preset', preset,
        GirderFileIdToVolume(str(files[0]['_id'])),
        outdir
    ], girder_result_hooks=[GirderUploadVolumePathToItem(outdir, item['_id'])]).job"""

    job['kwargs'] = {
        'task': _CREATE_TASK,
        'inputs': {
            'in': girderInputSpec(files[0], 'file', token=token)
        },
        'outputs': {
            'out': girderOutputSpec(
                item, token=token, parentType='item', reference=json.dumps({
                    'interactive_thumbnail': True
                }), name='__interactive_thumbnail__')
        },
        'jobInfo': jobInfoSpec(job)
    }
    job = jm.save(job)
    jm.scheduleJob(job)

    return job


def load(info):
    events.bind('model.item.remove', info['name'], lambda e: _removeThumbnails(e.info))
    events.bind('model.file.finalizeUpload.after', info['name'], _handleUpload)
    File().ensureIndex(([('interactive_thumbnails_uid', 1), ('attachedToId', 1)], {'sparse': True}))
    File().exposeFields(level=AccessType.READ, fields={'interactive_thumbnails_info'})
    Item().exposeFields(level=AccessType.READ, fields={'hasInteractiveThumbnail'})

    info['apiRoot'].item.route('GET', (':id', 'interactive_thumbnail', ':uid'), _getThumbnail)
    info['apiRoot'].item.route('POST', (':id', 'interactive_thumbnail'), _createThumbnail)
