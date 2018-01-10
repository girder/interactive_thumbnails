import $ from 'jQuery';
import events from 'girder/events';
import FolderModel from 'girder/models/FolderModel';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import ItemCollection from 'girder/collections/ItemCollection';
import router from 'girder/router';
import { wrap } from 'girder/utilities/PluginUtils'

import FolderListView from './folderListView/FolderListView';
import folderActionsExt from './folderActionsExt.pug';

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

// Add menu item to folder actions dropdown
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder') {
        $(folderActionsExt({
            folder: this.parentModel
        })).insertAfter(this.$('.g-folder-actions-menu > li:first'));
    }
    return this;
});
