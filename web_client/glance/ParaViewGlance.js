import View from 'girder/views/View';

import 'pv-glance-embeddable';
import template from './paraviewGlance.pug';

const ParaViewGlanceView = View.extend({
    render: function () {
        this.$el.html(template());

        this.glance = new window.pvGlanceMainView(this.$('.g-pv-glance-container')[0], this.model.downloadUrl());
        this.glance.render();

        return this;
    },

    destroy: function () {
        this.glance.destroy();
    }
});

export default ParaViewGlanceView;
