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

# Copied from Slicer:
# https://github.com/Slicer/Slicer/blob/master/Modules/Loadable/VolumeRendering/Resources/presets.xml
MEDICAL_XFER_PRESETS = {
    'CT-AAA': {
        'rgba': (
            (-3024, 0, 0, 0, 0),
            (143.556, 0.615686, 0.356863, 0.184314, 0),
            (166.222, 0.882353, 0.603922, 0.290196, 0.686275),
            (214.389, 1, 1, 1, 0.696078),
            (419.736, 1, 0.937033, 0.954531, 0.833333),
            (3071, 0.827451, 0.658824, 1, 0.803922)
        ),
        'shade': True,
        'ambient': 0.1,
        'diffuse': 0.9,
        'specular': 0.2,
        'specularPower': 10
    },
    'CT-Bones': {
        'rgb': (
            (-1000, 0.3, 0.3, 1),
            (-488, 0.3, 1, 0.3),
            (463.28, 1, 0, 0),
            (659.15, 1, 0.912535, 0.0374849),
            (953, 1, 0.3, 0.3)
        ),
        'opacity': (
            (-1000, 0),
            (152.19, 0),
            (278.93, 0.190476),
            (952, 0.2)
        ),
        'shade': True,
        'ambient': 0.2,
        'diffuse': 1,
        'specular': 0,
        'specularPower': 1
    },
    'CT-Soft-Tissue': {
        'rgba': (
            (-2048, 0, 0, 0, 0),
            (-167.01, 0, 0, 0, 0),
            (-160, 0.0556356, 0.0556356, 0.0556356, 1),
            (240, 1, 1, 1, 1),
            (3661, 1, 1, 1, 1)
        ),
        'shade': False,
        'ambient': 0.2,
        'diffuse': 1,
        'specular': 0,
        'specularPower': 1
    }
}

def arc_samples(n_samples, sample_range=360., start=0.):
    step = sample_range / n_samples
    return [start + step * i for i in range(n_samples)]


def build_xfer_fns(color_fn, opacity_fn, volume_property, data):
    if 'rgba' in data:
        for pt in data['rgba']:
            color_fn.AddRGBPoint(*pt[:4])
            opacity_fn.AddPoint(pt[0], pt[4])
    else:
        for pt in data['rgb']:
            color_fn.AddRGBPoint(*pt)
        for pt in data['opacity']:
            opacity_fn.AddPoint(*pt)

    volume_property.SetAmbient(data['ambient'])
    volume_property.SetDiffuse(data['diffuse'])
    volume_property.SetSpecular(data['specular'])
    if data['shade']:
        volume_property.ShadeOn()


@click.command()
@click.argument('in_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('out_dir', type=click.Path(file_okay=False))
@click.option('--width', default=DEFAULT_WIDTH, help='output image width (px)')
@click.option('--height', default=DEFAULT_HEIGHT, help='output image height (px)')
@click.option('--phi-samples', default=12, help='number of samples in phi dimension')
@click.option('--theta-samples', default=3, help='number of samples in theta dimension')
@click.option('--xfer-preset', default=None, help='transfer function preset to use')
@click.version_option(version=__version__, prog_name='Process a volume image into a 3d thumbnail')
def process(in_file, out_dir, width, height, phi_samples, theta_samples, xfer_preset):
    # Importing vtk package can be quite slow, only do it if CLI validation passes
    from vtk import (
        vtkMetaImageReader, vtkGPUVolumeRayCastMapper, vtkColorTransferFunction,
        vtkPiecewiseFunction, vtkNrrdReader, vtkVolumeProperty, vtkVolume, vtkRenderWindow,
        vtkRenderer, vtkCamera, VTK_LINEAR_INTERPOLATION)

    from vtk.web.dataset_builder import ImageDataSetBuilder

    phi_vals = arc_samples(phi_samples)

    if theta_samples > 1:
        theta_vals = arc_samples(theta_samples, 180., -90.)
    else:
        theta_vals = [0.]

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
    scalar_opacity = vtkPiecewiseFunction()
    volume_property = vtkVolumeProperty()

    if xfer_preset is None:  # some sensible naive default
        color_function.AddRGBPoint(field_range[0], 0., 0., 0.)
        color_function.AddRGBPoint(field_range[1], 1., 1., 1.)
        scalar_opacity.AddPoint(field_range[0], 0.)
        scalar_opacity.AddPoint(field_range[1], 1.)
    elif xfer_preset in MEDICAL_XFER_PRESETS:
        build_xfer_fns(
            color_function, scalar_opacity, volume_property, MEDICAL_XFER_PRESETS[xfer_preset])
    else:
        raise Exception('Unknown transfer function preset: %s' % xfer_preset)


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
