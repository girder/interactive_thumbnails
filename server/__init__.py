import json
from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import RestException
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item


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
        del file['itemId']
        File().save(file)

        if 'has3dThumbnail' not in item:
            Item().update({'_id': item['_id']}, {'$set': {'has3dThumbnail': True}}, multi=False)


def _removeThumbnails(event):
  rm = File().remove

  for file in File().find({'attachedToId': event.info['_id']}):
    rm(file)


@access.public
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


def load(info):
    events.bind('model.item.remove', info['name'], _removeThumbnails)
    events.bind('model.file.finalizeUpload.after', info['name'], _handleUpload)
    File().ensureIndex(([('3d_thumbnails_uid', 1), ('attachedToId', 1)], {'sparse': True}))
    File().exposeFields(level=AccessType.READ, fields={'3d_thumbnails_info'})
    Item().exposeFields(level=AccessType.READ, fields={'has3dThumbnail'})

    info['apiRoot'].item.route('GET', (':id', '3d_thumbnail', ':uid'), _get3dThumbnail)

    # TODO figure out how to remove existing 3d thumbnails on an item when a new set is uploaded
