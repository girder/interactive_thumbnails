import View from 'girder/views/View';

import { createViewer } from 'paraview-glance';
import template from './paraviewGlance.pug';

const ParaViewGlanceView = View.extend({
    render: function () {
        this.$el.html(template());

        this.glance = createViewer(this.$('.g-pv-glance-container')[0]);
        this.glance.openRemoteDataset(this.model.name(), this.model.downloadUrl());
        this.glance.updateTab('pipeline');

        return this;
    },

    destroy: function () {
        this.glance.unbind();
        View.prototype.destroy.call(this);
    }
});

export default ParaViewGlanceView;
