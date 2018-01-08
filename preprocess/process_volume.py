# -----------------------------------------------------------------------------
# Download data:
#  - Browser:
#      http://midas3.kitware.com/midas/folder/10409 => VisibleMale/vm_head_mri.mha
#  - Terminal
#      curl "http://midas3.kitware.com/midas/download?folders=&items=235237" -o vm_head_mri.mha
# -----------------------------------------------------------------------------

import click
import ctypes
import os

__version__ = '0.1.0'
DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512

# Unfortunately this hack is necessary to get the libOSMesa symbols loaded into
# the global namespace, presumably because they are weakly linked by VTK
ctypes.CDLL('libOSMesa.so', ctypes.RTLD_GLOBAL)


def arc_samples(n_samples):
    step = 360. / n_samples
    return [step * i for i in range(n_samples)]


@click.command()
@click.argument('in_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('out_dir', type=click.Path(file_okay=False))
@click.option('--width', default=DEFAULT_WIDTH, help='output image width (px)')
@click.option('--height', default=DEFAULT_HEIGHT, help='output image height (px)')
@click.option('--phi-samples', default=4, help='number of samples in phi dimension')
@click.option('--theta-samples', default=3, help='number of samples in theta dimension')
@click.version_option(version=__version__, prog_name='Process a volume image into a 3d thumbnail')
def process(in_file, out_dir, width, height, phi_samples, theta_samples):
    # Importing vtk package can be quite slow, only do it if CLI validation passes
    from vtk import (
        vtkMetaImageReader, vtkGPUVolumeRayCastMapper, vtkColorTransferFunction,
        vtkPiecewiseFunction, vtkNrrdReader, vtkVolumeProperty, vtkVolume, vtkRenderWindow,
        vtkRenderer, vtkCamera, VTK_LINEAR_INTERPOLATION)

    from vtk.web.dataset_builder import ImageDataSetBuilder

    phi_vals = arc_samples(phi_samples)
    theta_vals = arc_samples(theta_samples)

    ext = os.path.splitext(in_file)[1].lower()
    if ext == '.mha':
        reader = vtkMetaImageReader()
    elif ext == '.nrrd':
        reader = vtkNrrdReader()
    else:
        raise Exception('Unknown file type, cannot read: ' + in_file)

    reader.SetFileName(in_file)
    reader.Update()
    field_range = reader.GetOutput().GetPointData().GetScalars().GetRange()

    mapper = vtkGPUVolumeRayCastMapper()
    mapper.SetInputConnection(reader.GetOutputPort())

    color_function = vtkColorTransferFunction()
    color_function.AddRGBPoint(field_range[0], 0., 0., 0.)
    color_function.AddRGBPoint(field_range[1], 1., 1., 1.)

    scalar_opacity = vtkPiecewiseFunction()
    scalar_opacity.AddPoint(field_range[0], 0.)
    scalar_opacity.AddPoint(field_range[1], 1.)

    volume_property = vtkVolumeProperty()
    #volume_property.ShadeOn()  # TODO(zachmullen) I thought it looked better off, should it be on?
    volume_property.SetInterpolationType(VTK_LINEAR_INTERPOLATION)
    volume_property.SetColor(color_function)
    volume_property.SetScalarOpacity(scalar_opacity)

    volume = vtkVolume()
    volume.SetMapper(mapper)
    volume.SetProperty(volume_property)

    window = vtkRenderWindow()
    window.SetSize(width, height)

    renderer = vtkRenderer()
    window.AddRenderer(renderer)

    renderer.AddVolume(volume)

    camera = vtkCamera()
    renderer.SetActiveCamera(camera)
    renderer.ResetCamera()
    window.Render()

    idb = ImageDataSetBuilder(out_dir, 'image/jpg', {
        'type': 'spherical',
        'phi': phi_vals,
        'theta': theta_vals
    })

    idb.start(window, renderer)
    idb.writeImages()
    idb.stop()


if __name__ == '__main__':
    process()
