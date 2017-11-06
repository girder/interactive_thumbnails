import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import ViewerWidget from './viewer/ViewerWidget';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.model.get('has3dThumbnail')) {
            new ViewerWidget({
                parentView: this,
                model: this.model
            }).render().$el.insertAfter(this.$('.g-item-info'));
        }
    });
    return render.call(this);
});
