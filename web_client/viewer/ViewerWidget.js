import View from 'girder/views/View';
import { getApiRoot, restRequest } from 'girder/rest';
import QueryDataModel from 'paraviewweb/src/IO/Core/QueryDataModel';
import MouseHandler from 'paraviewweb/src/Interaction/Core/MouseHandler';

import template from './viewerWidget.pug';
import './viewerWidget.styl';

const ViewerWidget = View.extend({
    className: 'g-interactive-thumbnail-viewer-container',

    initialize: function (settings) {
        this._indexJson = settings.indexJson || null;
        this._awaitRender = false;
        this._basePath = `item/${this.model.id}/interactive_thumbnail/`;
    },

    render: function () {
        if (!this._indexJson) {
            this._awaitRender = true;
            this._load();
            return this;
        }

        this.$el.html(template());
        this._initPvwViewer(this.$('.g-interactive-thumbnail-viewer')[0]);

        return this;
    },

    _load: function () {
        restRequest({
            url: `${this._basePath}index.json`
        }).done((resp) => {
            this._indexJson = resp;
            if (this._awaitRender) {
                this._awaitRender = false;
                this.render();
            }
        });
    },

    _initPvwViewer: function (container) {
        this._cleanupPvwViewer();
        this._qdm = new QueryDataModel(this._indexJson, `${getApiRoot()}/${this._basePath}`);
        this._qdm.onDataChange((data, envelope) => {
            container.innerHTML = '';
            container.appendChild(data.image.image);
        });
        this._mouseHandler = new MouseHandler(container, {preventDefault: false});
        this._qdm.fetchData();
        this._mouseHandler.attach(this._qdm.getMouseListener());
    },

    _cleanupPvwViewer: function () {
        if (this._mouseHandler) {
            this._mouseHandler.destroy();
        }
        if (this._qdm) {
            this._qdm.destroy();
        }

    },

    destroy: function () {
        this._cleanupPvwViewer();
        View.prototype.destroy.apply(this, arguments);
    }
});

export default ViewerWidget;
