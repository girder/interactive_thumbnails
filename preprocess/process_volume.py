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


def get_phi_vals(n_samples):
    step = 360. / n_samples
    return [step * i for i in range(n_samples)]


def get_theta_vals(n_samples):
    if n_samples == 1:
        return [0.]

    step = 160. / (n_samples - 1)
    return [step * i - 80. for i in range(n_samples)]


def setup_vr(color_fn, opacity_fn, volume_property, data):
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
@click.option('--theta-samples', default=6, help='number of samples in theta dimension')
@click.option('--preset', default=None, help='transfer function preset to use')
@click.version_option(version=__version__, prog_name='Process a volume image into a 3d thumbnail')
def process(in_file, out_dir, width, height, phi_samples, theta_samples, preset):
    # Importing vtk package can be quite slow, only do it if CLI validation passes
    from vtk import (
        vtkMetaImageReader, vtkGPUVolumeRayCastMapper, vtkColorTransferFunction,
        vtkPiecewiseFunction, vtkNrrdReader, vtkVolumeProperty, vtkVolume, vtkRenderWindow,
        vtkRenderer, vtkCamera, vtkXMLImageDataReader, VTK_LINEAR_INTERPOLATION)

    from vtk.web.dataset_builder import ImageDataSetBuilder

    phi_vals = get_phi_vals(phi_samples)
    theta_vals = get_theta_vals(theta_samples)

    ext = os.path.splitext(in_file)[1].lower()
    if ext == '.mha':
        reader = vtkMetaImageReader()
    elif ext == '.nrrd':
        reader = vtkNrrdReader()
    elif ext == '.vti':
        reader = vtkXMLImageDataReader()
    elif ext == '.tre':
        # TODO refactor this to reduce duplication of visualization code
        return process_tre(in_file, out_dir, phi_vals, theta_vals, width, height)
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

    if preset is None or preset == 'default':  # some sensible naive default
        color_function.AddRGBPoint(field_range[0], 0., 0., 0.)
        color_function.AddRGBPoint(field_range[1], 1., 1., 1.)
        scalar_opacity.AddPoint(field_range[0], 0.)
        scalar_opacity.AddPoint(field_range[1], 1.)
    elif preset in MEDICAL_XFER_PRESETS:
        setup_vr(color_function, scalar_opacity, volume_property, MEDICAL_XFER_PRESETS[preset])
    else:
        raise Exception('Unknown transfer function preset: %s' % preset)


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


def process_tre(in_file, out_dir, phi_vals, theta_vals, width, height):
    import itk, vtk
    from vtk.web.dataset_builder import ImageDataSetBuilder

    reader = itk.SpatialObjectReader[3].New()
    reader.SetFileName(in_file)
    reader.Update()
    blocks = vtk.vtkMultiBlockDataSet()
    tubeGroup = reader.GetGroup()
    for tube in _iter_tubes(tubeGroup):
        polydata = _tube_to_polydata(tube)
        index = blocks.GetNumberOfBlocks()
        blocks.SetBlock(index, polydata)

    prod = vtk.vtkTrivialProducer()
    prod.SetOutput(blocks)

    mapper = vtk.vtkCompositePolyDataMapper2()
    mapper.SetInputConnection(prod.GetOutputPort())

    cdsa = vtk.vtkCompositeDataDisplayAttributes()
    cdsa.SetBlockColor(1, (1, 1, 0))
    cdsa.SetBlockColor(2, (0, 1, 1))

    mapper.SetCompositeDataDisplayAttributes(cdsa)

    window = vtk.vtkRenderWindow()
    window.SetSize(width, height)

    renderer = vtk.vtkRenderer()
    window.AddRenderer(renderer)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    renderer.AddActor(actor)
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


def _iter_tubes(tubeGroup):
    import itk, itkExtras

    obj = itkExtras.down_cast(tubeGroup)
    if isinstance(obj, itk.VesselTubeSpatialObject[3]):
        yield obj

    # otherwise, `obj` is a GroupSpatialObject
    children = obj.GetChildren()
    for i in range(obj.GetNumberOfChildren()):
        for tube in _iter_tubes(children[i]):
            yield tube


def _get_tube_points(tube):
    points = []
    for j in range(tube.GetNumberOfPoints()):
        point = _convert_to_vessel_tube(tube.GetPoint(j))

        radius = point.GetRadius()
        pos = point.GetPosition()

        # I think I need to extract the values otherwise corruption occurs
        # on the itkPointD3 objects.
        points.append(((pos[0], pos[1], pos[2]), radius))
    return points


def _convert_to_vessel_tube(soPoint):
    import itk
    props = str(soPoint).split('\n')
    dim = len(soPoint.GetPosition())
    vesselTubePoint = itk.VesselTubeSpatialObjectPoint[dim]()

    vesselTubePoint.SetID(soPoint.GetID())
    vesselTubePoint.SetPosition(*soPoint.GetPosition())
    vesselTubePoint.SetBlue(soPoint.GetBlue())
    vesselTubePoint.SetGreen(soPoint.GetGreen())
    vesselTubePoint.SetRed(soPoint.GetRed())
    vesselTubePoint.SetAlpha(soPoint.GetAlpha())

    radius = float(props[3].strip()[len("R: "):])
    vesselTubePoint.SetRadius(radius)

    tangent = list(map(float, props[5].strip()[len("T: ["):-1].split(",")))
    vesselTubePoint.SetTangent(*tangent)

    normal1 = list(map(float, props[6].strip()[len("Normal1: ["):-1].split(",")))
    normal2 = list(map(float, props[7].strip()[len("Normal2: ["):-1].split(",")))
    vesselTubePoint.SetNormal1(*normal1)
    vesselTubePoint.SetNormal2(*normal2)

    medialness = float(props[8].strip()[len("Medialness: "):])
    vesselTubePoint.SetMedialness(medialness)

    ridgeness = float(props[9].strip()[len("Ridgeness: "):])
    vesselTubePoint.SetRidgeness(ridgeness)

    alpha1 = float(props[10].strip()[len("Alpha1: "):])
    alpha2 = float(props[11].strip()[len("Alpha2: "):])
    alpha3 = float(props[12].strip()[len("Alpha3: "):])
    vesselTubePoint.SetAlpha1(alpha1)
    vesselTubePoint.SetAlpha2(alpha2)
    vesselTubePoint.SetAlpha3(alpha3)

    mark = float(props[13].strip()[len("Mark: "):])
    vesselTubePoint.SetMark(bool(mark))

    return vesselTubePoint


def _tube_to_polydata(tube):
    import vtk
    points = _get_tube_points(tube)

    # Convert points to world space.
    tube.ComputeObjectToWorldTransform()
    transform = tube.GetIndexToWorldTransform()
    # Get scaling vector from transform matrix diagonal.
    scaling = [transform.GetMatrix()(i,i) for i in range(3)]
    # Use average of scaling vector for scale since TubeFilter
    # doesn't seem to support ellipsoid.
    scale = sum(scaling)/len(scaling)
    for i in range(len(points)):
        pt, radius = points[i]
        pt = transform.TransformPoint(pt)
        points[i] = (pt, radius*scale)

    vpoints = vtk.vtkPoints()
    vpoints.SetNumberOfPoints(len(points))
    scalars = vtk.vtkFloatArray()
    scalars.SetNumberOfValues(len(points))
    scalars.SetName('Radii')

    minRadius = float('inf')
    maxRadius = float('-inf')
    for i, (pt, r) in enumerate(points):
        vpoints.SetPoint(i, pt)
        scalars.SetValue(i, r)
        minRadius = min(r, minRadius)
        maxRadius = max(r, maxRadius)

    pl = vtk.vtkPolyLine()
    pl.Initialize(len(points), range(len(points)), vpoints)

    ca = vtk.vtkCellArray()
    ca.InsertNextCell(pl)

    pd = vtk.vtkPolyData()
    pd.SetLines(ca)
    pd.SetPoints(vpoints)
    pd.GetPointData().SetScalars(scalars)
    pd.GetPointData().SetActiveScalars('Radii')

    tf = vtk.vtkTubeFilter()
    tf.SetInputData(pd)
    tf.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
    tf.SetRadius(minRadius)
    tf.SetRadiusFactor(maxRadius/minRadius)
    tf.SetNumberOfSides(20)
    tf.Update()

    return tf.GetOutput()


if __name__ == '__main__':
    process()
