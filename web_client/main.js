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

    items.pageLimit = 30;  // Choose page size with nice divisors for flow layout

    $.when(folder.fetch(), folder.fetch({extraPath: 'details'}), items.fetch({folderId: id})).then(() => {
        events.trigger('g:navigateTo', FolderListView, {
            folder,
            items
        }, {renderNow: true});
    });
});
