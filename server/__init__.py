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

_PHI_SAMPLES = 8
_THETA_SAMPLES = 5
_SIZE = 512
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

    if isinstance(reference, dict) and '3d_thumbnail' in reference:
        item = Item().load(file['itemId'], force=True, exc=True)

        file['3d_thumbnails_uid'] = file['name']
        file['attachedToId'] = item['_id']
        file['attachedToType'] = 'item'
        file['itemId'] = None
        File().save(file)

        if not item.get('has3dThumbnail'):
            Item().update({'_id': item['_id']}, {'$set': {'has3dThumbnail': True}}, multi=False)


def _removeThumbnails(item, saveItem=False):
    rm = File().remove

    for file in File().find({'attachedToId': item['_id']}):
        if '3d_thumbnails_uid' in file:
          rm(file)

    if saveItem:
        Item().update({'_id': item['_id']}, {'$set': {'has3dThumbnail': False}}, multi=False)


@access.cookie
@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Download a 3d thumbnail image for a given item.')
    .modelParam('id', model=Item, level=AccessType.READ)
    .param('uid', 'The UID (path) of the thumbnail file to retrieve.', paramType='path')
)
def _get3dThumbnail(item, uid):
    file = File().findOne({
        'attachedToId': item['_id'],
        '3d_thumbnails_uid': uid
    })
    if not file:
        raise RestException('No such thumbnail for uid "%s".' % uid)

    return File().download(file)


@access.user(scope=TokenScope.DATA_WRITE)
@filtermodel(Job)
@autoDescribeRoute(
    Description('Generate a new set of 3D thumbnail images for an item.')
    .modelParam('id', model=Item, level=AccessType.WRITE)
)
def _create3dThumbnail(item):
    # Remove previously attached thumbnails
    _removeThumbnails(item, saveItem=True)

    user = getCurrentUser()

    # Schedule a job to produce new thumbnails
    jm = Job()
    job = jm.createJob(
        title='3D thumbnail creation: %s' % item['name'], type='3d_thumbnails',
        handler='worker_handler', user=user)
    token = Token().createToken(user, days=3, scope={TokenScope.DATA_READ, TokenScope.DATA_WRITE})

    job['kwargs'] = {
        'task': _CREATE_TASK,
        'inputs': {
            'in': girderInputSpec(item, 'item', token=token)
        },
        'outputs': {
            'out': girderOutputSpec(
                item, token=token, parentType='item', reference=json.dumps({'3d_thumbnail': True}),
                name='__3d_thumbnail__')
        },
        'jobInfo': jobInfoSpec(job)
    }
    job = jm.save(job)
    jm.scheduleJob(job)

    return job


def load(info):
    events.bind('model.item.remove', info['name'], lambda e: _removeThumbnails(e.info))
    events.bind('model.file.finalizeUpload.after', info['name'], _handleUpload)
    File().ensureIndex(([('3d_thumbnails_uid', 1), ('attachedToId', 1)], {'sparse': True}))
    File().exposeFields(level=AccessType.READ, fields={'3d_thumbnails_info'})
    Item().exposeFields(level=AccessType.READ, fields={'has3dThumbnail'})

    info['apiRoot'].item.route('GET', (':id', '3d_thumbnail', ':uid'), _get3dThumbnail)
    info['apiRoot'].item.route('POST', (':id', '3d_thumbnail'), _create3dThumbnail)
