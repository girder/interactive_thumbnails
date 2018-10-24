import json
from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import filtermodel, RestException
from girder.constants import AccessType, TokenScope
from girder.models.file import File
from girder.models.item import Item
from girder.plugin import getPlugin, GirderPlugin
from girder_jobs.models.job import Job
from girder_worker.docker.tasks import docker_run
from girder_worker.docker.transforms import VolumePath
from girder_worker.docker.transforms.girder import (
    GirderItemIdToVolume, GirderUploadVolumePathToItem)

_ANGLE_STEP = 20
_SIZE = 256


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
        Item().update(
            {'_id': item['_id']},
            {'$set': {'hasInteractiveThumbnail': False}},
            multi=False)


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
    # Remove previously attached thumbnails
    _removeThumbnails(item, saveItem=True)

    outdir = VolumePath('__thumbnails_output__')
    return docker_run.delay(
        'zachmullen/3d_thumbnails:latest', container_args=[
            '--angle-step', str(_ANGLE_STEP),
            '--width', str(_SIZE),
            '--height', str(_SIZE),
            '--preset', preset,
            GirderItemIdToVolume(item['_id'], item_name=item['name']),
            outdir
        ], girder_job_title='Interactive thumbnail generation: %s' % item['name'],
        girder_result_hooks=[
            GirderUploadVolumePathToItem(outdir, item['_id'], upload_kwargs={
                'reference': json.dumps({'interactive_thumbnail': True})
            })
        ]).job


class InteractiveThumbnailsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Interactive thumbnails'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        getPlugin('worker').load(info)

        events.bind('model.item.remove', __name__, lambda e: _removeThumbnails(e.info))
        events.bind('model.file.finalizeUpload.after', __name__, _handleUpload)
        File().ensureIndex(
            ([('interactive_thumbnails_uid', 1), ('attachedToId', 1)], {'sparse': True}))
        File().exposeFields(level=AccessType.READ, fields={'interactive_thumbnails_info'})
        Item().exposeFields(level=AccessType.READ, fields={'hasInteractiveThumbnail'})

        info['apiRoot'].item.route('GET', (':id', 'interactive_thumbnail', ':uid'), _getThumbnail)
        info['apiRoot'].item.route('POST', (':id', 'interactive_thumbnail'), _createThumbnail)
