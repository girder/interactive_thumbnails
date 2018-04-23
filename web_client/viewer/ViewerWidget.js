import View from 'girder/views/View';
import { getApiRoot } from 'girder/rest';

import CinemaThumbnail from './CinemaThumbnail';
import template from './viewerWidget.pug';
import './viewerWidget.styl';

const ViewerWidget = View.extend({
    className: 'g-interactive-thumbnail-viewer-container',
    render: function () {
        this.$el.html(template());
        new CinemaThumbnail(
            this.$('.g-interactive-thumbnail-viewer')[0],
            `${getApiRoot()}/item/${this.model.id}/interactive_thumbnail`,
            20).updateImage();

        return this;
    },
});

export default ViewerWidget;
