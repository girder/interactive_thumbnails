import QueryDataModel from 'paraviewweb/src/IO/Core/QueryDataModel';
import MouseHandler from 'paraviewweb/src/Interaction/Core/MouseHandler';

export function bindTumbnailToImage(model, container, basepath) {
  const queryDataModel = new QueryDataModel(model, basepath);
  const mouseHandler = new MouseHandler(container);
  queryDataModel.onDataChange((data, envelope) => {
    container.innerHTML = '';
    container.appendChild(data.image.image);
  });
  queryDataModel.fetchData();
  mouseHandler.attach(queryDataModel.getMouseListener());
}

