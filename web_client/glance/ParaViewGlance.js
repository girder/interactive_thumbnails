import View from 'girder/views/View';
import React from 'react';
import ReactDOM from 'react-dom';

import GlanceMain from 'pv-web-viewer/Sources/MainView';
import template from './paraviewGlance.pug';

const ParaViewGlanceView = View.extend({
    render: function () {
        this.$el.html(template());

        ReactDOM.render(<GlanceMain />, this.$('.g-pv-glance-container')[0]);
        return this;
    }
});

export default ParaViewGlanceView;
