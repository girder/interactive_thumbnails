import _ from 'underscore';
import View from 'girder/views/View';

import ViewerWidget from '../viewer/ViewerWidget';
import template from './folderListView.pug';
import './folderListView.styl';

const FolderListView = View.extend({
    initialize: function (settings) {
        this.folder = settings.folder;
        this.items = settings.items;
        this._viewers = [];
    },

    render: function () {
        this.$el.html(template({
            folder: this.folder,
            items: this.items.toArray()
        }));

        this._cleanupViewers();
        this._viewers = _.map(this.$('.g-viewer-widget-wrapper'), (el) => {
            return new ViewerWidget({
                el,
                model: this.items.get($(el).attr('item-cid')),
                parentView: this
            }).render();
        });
    },

    _cleanupViewers: function () {
        _.each(this._viewers, (viewer) => {
            viewer.destroy();
        });
    }
});

export default FolderListView;
