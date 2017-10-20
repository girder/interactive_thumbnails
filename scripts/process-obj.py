# -----------------------------------------------------------------------------
# Download data:
#  - Browser:
#      http://midas3.kitware.com/midas/folder/10409 => VisibleMale/vm_head_mri.mha
#  - Terminal
#      curl "http://midas3.kitware.com/midas/download?folders=&items=235237" -o vm_head_mri.mha
# -----------------------------------------------------------------------------

from vtk import *

from vtk.web.query_data_model import *
from vtk.web.dataset_builder import *

# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------

dataset_destination_path = '/Users/seb/Documents/code/girder-thumbnail/data-obj'
file_path = '/Users/seb/Desktop/UH-60 Blackhawk/uh60.obj'

# -----------------------------------------------------------------------------
# VTK Pipeline creation
# -----------------------------------------------------------------------------

reader = vtkOBJReader()
reader.SetFileName(file_path)
reader.Update()


mapper = vtkPolyDataMapper()
mapper.SetInputConnection(reader.GetOutputPort())


actor = vtkActor()
actor.SetMapper(mapper)

window = vtkRenderWindow()
window.SetSize(512, 512)

renderer = vtkRenderer()
window.AddRenderer(renderer)

renderer.AddVolume(actor)

camera = vtkCamera()
renderer.SetActiveCamera(camera)

window.Render()
renderer.ResetCamera()
window.Render()


# Camera setting
camera = {
    'position': [v for v in camera.GetFocalPoint()],
    'focalPoint': camera.GetFocalPoint(),
    'viewUp': [1,0,0]
}
camera['position'][2] += 100
update_camera(renderer, camera)
window.Render()
renderer.ResetCamera()
window.Render()

# -----------------------------------------------------------------------------
# Data Generation
# -----------------------------------------------------------------------------

# Create Image Builder
idb = ImageDataSetBuilder(dataset_destination_path, 'image/jpg', {'type': 'spherical', 'phi': range(0, 360, 45), 'theta': [0]})

idb.start(window, renderer)
idb.writeImages()
idb.stop()


