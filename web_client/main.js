import $ from 'jQuery';
import events from 'girder/events';
import FolderModel from 'girder/models/FolderModel';
import ItemCollection from 'girder/collections/ItemCollection';
import router from 'girder/router';

import FolderListView from './folderListView/FolderListView';

router.route('folder/:id/interactive_thumbnails', (id) => {
    const items = new ItemCollection();
    const folder = new FolderModel({
        _id: id
    });
    $.when(folder.fetch(), items.fetch({folderId: id})).then(() => {
        events.trigger('g:navigateTo', FolderListView, {
            folder,
            items
        }, {renderNow: true});
    });
});
