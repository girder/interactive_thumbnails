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

dataset_destination_path = '/Users/seb/Documents/code/girder-thumbnail/data'
file_path = '/Users/seb/Documents/code/girder-thumbnail/vm_head_mri.mha'

field = 'MetaImage'

# -----------------------------------------------------------------------------
# VTK Pipeline creation
# -----------------------------------------------------------------------------

reader = vtkMetaImageReader()
reader.SetFileName(file_path)
reader.Update()
fieldRange = reader.GetOutput().GetPointData().GetScalars().GetRange()


mapper = vtkGPUVolumeRayCastMapper()
mapper.SetInputConnection(reader.GetOutputPort())
mapper.RenderToImageOn()

colorFunction = vtkColorTransferFunction()
colorFunction.AddRGBPoint(fieldRange[0], 1.0, 1.0, 1.0)
colorFunction.AddRGBPoint(fieldRange[1], 1.0, 1.0, 1.0)

scalarOpacity = vtkPiecewiseFunction()
scalarOpacity.RemoveAllPoints()
scalarOpacity.AddPoint(fieldRange[0], 0.0)
scalarOpacity.AddPoint(fieldRange[1], 1.0)

volumeProperty = vtkVolumeProperty()
volumeProperty.ShadeOn()
volumeProperty.SetInterpolationType(VTK_LINEAR_INTERPOLATION)
volumeProperty.SetColor(colorFunction)
volumeProperty.SetScalarOpacity(scalarOpacity)

volume = vtkVolume()
volume.SetMapper(mapper)
volume.SetProperty(volumeProperty)

window = vtkRenderWindow()
window.SetSize(512, 512)

renderer = vtkRenderer()
window.AddRenderer(renderer)

renderer.AddVolume(volume)

camera = vtkCamera()
renderer.SetActiveCamera(camera)

window.Render()
renderer.ResetCamera()
window.Render()

# Camera setting
# camera = {
#     'position': [-0.508, -872.745, 5.1],
#     'focalPoint': [-0.508, -32.108, 5.1],
#     'viewUp': [0,0,1]
# }

# update_camera(renderer, camera)

# -----------------------------------------------------------------------------
# Data Generation
# -----------------------------------------------------------------------------

# Create Image Builder
idb = ImageDataSetBuilder(dataset_destination_path, 'image/jpg', {'type': 'spherical', 'phi': range(0, 360, 45), 'theta': [0]})

idb.start(window, renderer)
idb.writeImages()
idb.stop()


