import View from 'girder/views/View';

import GlanceMain from 'pv-glance-embeddable';
import template from './paraviewGlance.pug';

const ParaViewGlanceView = View.extend({
    render: function () {
        this.$el.html(template());

        this.glance = new GlanceMain(this.$('.g-pv-glance-container')[0], this.model.downloadUrl());
        this.glance.render();

        return this;
    },

    destroy: function () {
        this.glance.destroy();
        View.prototype.destroy.call(this);
    }
});

export default ParaViewGlanceView;
