import View from 'girder/views/View';
import { getApiRoot, restRequest } from 'girder/rest';
import QueryDataModel from 'paraviewweb/src/IO/Core/QueryDataModel';
import MouseHandler from 'paraviewweb/src/Interaction/Core/MouseHandler';

import template from './viewerWidget.pug'
import './viewerWidget.styl';

const ViewerWidget = View.extend({
    className: 'g-3d-thumbnail-viewer-container',

    initialize: function (settings) {
        this._indexJson = settings.indexJson || null;
        this._awaitRender = false;
        this._basePath =  `item/${this.model.id}/3d_thumbnail/`;
    },

    render: function () {
        if (!this._indexJson) {
            this._awaitRender = true;
            this._load();
            return this;
        }

        this.$el.html(template());

        const container = this.$('.g-3d-thumbnail-viewer-inner')[0];
        const queryDataModel = new QueryDataModel(this._indexJson, `${getApiRoot()}/${this._basePath}`);
        const mouseHandler = new MouseHandler(container);

        queryDataModel.onDataChange((data, envelope) => {
            container.innerHTML = '';
            container.appendChild(data.image.image);
        });
        queryDataModel.fetchData();
        mouseHandler.attach(queryDataModel.getMouseListener());

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
    }
});

export default ViewerWidget;
