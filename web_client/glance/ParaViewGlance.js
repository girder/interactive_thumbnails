import View from 'girder/views/View';

import Glance from 'pv-web-viewer/dist/embeddable';
import template from './paraviewGlance.pug';

const ParaViewGlanceView = View.extend({
    render: function () {
        this.$el.html(template());

        // It would be great if this API existed
        this.glance = new Glance({
            container: this.$('.g-pv-glance-container')[0],
            dataUrl: this.model.getDownloadUrl()
        });

        return this;
    },

    destroy: function () {
        this.glance.destroy();
    }
});

export default ParaViewGlanceView;
