#!/usr/bin/env python

import click
import itk
import itkTemplate
import json
import math
import os


__version__ = '0.1.0'
DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512
DEFAULT_NB_SLICES = 10
INPUT_IMAGE_DIMENSION = 3
SLICING_DIMENSION = 2
OUTPUT_IMAGE_DIMENSION = 2


def smooth_and_resample(image, width, height):
    # Set input image origin to 0,0 as we do not want to worry about it.
    image.SetOrigin([0, 0])

    original_size = itk.size(image)
    original_spacing = image.GetSpacing()

    # We need to create a new Python variable to compute
    # the new size as `size_im` that was returned above is
    # actually a reference that points to the value that is
    # contained in the image.
    new_size = itk.Size[OUTPUT_IMAGE_DIMENSION]()
    new_size[0] = width
    new_size[1] = height
    SpacingType = itk.Vector[itk.D, OUTPUT_IMAGE_DIMENSION]
    scale = SpacingType()
    new_spacing = SpacingType()
    for ii in range(OUTPUT_IMAGE_DIMENSION):
        scale[ii] = float(original_size[ii])/float(new_size[ii])
        new_spacing[ii] = scale[ii]*original_spacing[ii]

    # Make output image isotropic since jpeg does not have spacing information.
    # We keep the largest spacing, to avoid cutting the image along one
    # direction.
    if new_spacing[0] > new_spacing[1]:
        new_spacing[1] = new_spacing[0]
    else:
        new_spacing[0] = new_spacing[1]

    sigma = SpacingType()
    for ii in [0, 1]:
        sigma[ii] = 2*new_spacing[ii]/math.pi
    variance = sigma*sigma

    gaussian_image = itk.DiscreteGaussianImageFilter(
        image, UseImageSpacing=True, Variance=variance)
    resampled_image = itk.ResampleImageFilter(
        gaussian_image, Size=new_size, OutputSpacing=new_spacing)
    return resampled_image

# The functions `SeriesImageFileReader` has been integrated inside
# `ImageFileReader` in recent versions (>=5.0.0 beta 2) of ITK
# to support image series but this has not been backported to ITK 4.13 which
# is the current stable release.
def ImageSeriesReader(*args, **kwargs):
    primaryInputMethods = ('FileNames',)
    inputFileName = ''
    if len(args) != 0:
        # try to find a type suitable for the primary input provided
        inputFileName = args[0]
    elif set(primaryInputMethods).intersection(kwargs.keys()):
        for method in primaryInputMethods:
            if method in kwargs:
                inputFileName = kwargs[method]
                break
    if not inputFileName:
        raise RuntimeError("No FileName specified.")
    import itk
    if "ImageIO" in kwargs:
        imageIO = kwargs["ImageIO"]
    else:
        imageIO = itk.ImageIOFactory.CreateImageIO(
            inputFileName[0], itk.ImageIOFactory.ReadMode)
    if not imageIO:
        raise RuntimeError(
            "No ImageIO is registered to handle the given file.")
    componentTypeDic = {"float": itk.F, "double": itk.D,
                        "unsigned_char": itk.UC, "unsigned_short": itk.US,
                        "unsigned_int": itk.UI, "unsigned_long": itk.UL,
                        "unsigned_long_long": itk.ULL, "char": itk.SC,
                        "short": itk.SS, "int": itk.SI, "long": itk.SL,
                        "long_long": itk.SLL
                        }
    # Read the metadata from the image file.
    imageIO.SetFileName(inputFileName[0])
    imageIO.ReadImageInformation()
    dimension = imageIO.GetNumberOfDimensions()
    componentAsString = imageIO.GetComponentTypeAsString(
        imageIO.GetComponentType())
    component = componentTypeDic[componentAsString]
    pixel = imageIO.GetPixelTypeAsString(imageIO.GetPixelType())
    numberOfComponents = imageIO.GetNumberOfComponents()
    PixelType = itkTemplate.itkTemplate._pixelTypeFromIO(
        pixel, component, numberOfComponents)
    ImageType = itk.Image[PixelType, dimension]
    ReaderType = itk.ImageSeriesReader[ImageType]
    return ReaderType.New(*args, **kwargs)


def get_filenames(in_dir):
    nameGenerator = itk.GDCMSeriesFileNames.New()
    # In case multiple series. Probably not necessary
    nameGenerator.SetUseSeriesDetails(True)
    # Limit series by date
    nameGenerator.AddSeriesRestriction("0008|0021")

    nameGenerator.SetDirectory(in_dir)
    # TODO: See if it is better to keep only the first series or throw
    # an error message if multiple series are found.
    seriesIdentifier = nameGenerator.GetSeriesUIDs()
    fileNames = nameGenerator.GetFileNames(seriesIdentifier[0])
    return fileNames


def rescale_dicom_image_intensity(image, meta_dict):
    try:
        # '0028|1050' is the DICOM window Center for display (string). It is
        # used to apply an intensity windowing filter.
        center = int(float(meta_dict['0028|1050']))
        # '0028|1050' is the DICOM window Width for display (string). It is
        # used to apply an intensity windowing filter.
        width = int(float(meta_dict['0028|1051']))
        intensity_winwdow_filter = itk.IntensityWindowingImageFilter.New(image)
        # ITK versions prior to ITK 5.0.0 beta 2 do not support passing tuples
        # directly as an argument of the `New()` function. Instead, we need to
        # explicitely call the correct `Set` function.
        intensity_winwdow_filter.SetWindowLevel(width, center)
        # Image is rescaled between 0 and 255 to be saved as a JPEG later.
        intensity_winwdow_filter.SetOutputMinimum(0)
        intensity_winwdow_filter.SetOutputMaximum(255)
        intensity_winwdow_filter.Update()
        return intensity_winwdow_filter.GetOutput()
    except KeyError:
        # If either or both of the required tags are missing in the DICOM,
        # we simply rely on the image minimum and maximum to rescale it.
        # Image is rescaled between 0 and 255 to be saved as a JPEG later.
        return itk.RescaleIntensityImageFilter(image, OutputMinimum=0,
                                               OutputMaximum=255)


def save_as_jpeg(image, out_dir, current_slice):
    # To save as a jpeg, rescale between 0 and 255 (unsigned char)
    OutputImageType = itk.Image[itk.UC, OUTPUT_IMAGE_DIMENSION]
    cast_filter = itk.CastImageFilter[image, OutputImageType].New(image)
    cast_filter.Update()
    output_image_filename = os.path.join(out_dir, '%d.jpg' % current_slice)
    itk.imwrite(cast_filter.GetOutput(),
                output_image_filename)


def generate_json(out_dir, list_indices):
    json_dict = {
        "arguments_order": [
            "slice"
        ],
        "type": [
            "tonic-query-data-model"
        ],
        "arguments": {
            "slice": {
                "name": "slice",
                "values": [
                    "0",
                ],
                "ui": "slider",
                "loop": "modulo",
                "bind": {
                    "mouse": {
                        "drag": {
                            "modifier": 0,
                            "coordinate": 0,
                            "step": 30,
                            "orientation": 1
                        }
                    }
                }
            }
        },
        "metadata": {
            "backgroundColor": "rgb(0, 0, 0)"
        },
        "data": [
            {
                "metadata": {},
                "name": "image",
                "type": "blob",
                "mimeType": "image/jpg",
                "pattern": "{slice}.jpg"
            }
        ]
    }
    json_dict["arguments"]["slice"]["values"] = list_indices
    output_json_filename = os.path.join(out_dir, "index.json")
    with open(output_json_filename, 'w') as outfile:
        json.dump(json_dict, outfile)


def compute_real_width_and_height(image, width, height):
    image_size = itk.size(image)
    if width is None and height is None:
        width = DEFAULT_WIDTH
        height = DEFAULT_HEIGHT
    elif width is None:
        width = int(math.ceil(image_size[0]/image_size[1]*height))
    elif height is None:
        height = int(math.ceil(image_size[1]/image_size[0]*width))
    if not height >= 1 or not width >= 1:
        raise Exception(
            "`height` and `width` must be greater than or equal to 1")
    return width, height


@click.command()
@click.argument('in_dir', type=click.Path(exists=True, file_okay=False))
@click.argument('out_dir', type=click.Path(file_okay=False))
@click.option('--width', type=click.INT, default=None, help='output image width (px)')  # noqa
@click.option('--height', type=click.INT, default=None, help='output image height (px)')  # noqa
@click.option('--slices', type=click.INT, default=DEFAULT_NB_SLICES, help='number of slicer step for sampling (degrees)')  # noqa
@click.version_option(version=__version__, prog_name='Create 2D thumbnails from 3D image.')  # noqa
def process(in_dir, out_dir, width, height, slices):

    if not slices >= 2:
        raise Exception("`slices` must me greater or equal to 1.")
    # Create output directory if necessary.
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    file_names = get_filenames(in_dir)
    dicom_reader = ImageSeriesReader(FileNames=file_names)
    dicom_reader.MetaDataDictionaryArrayUpdateOn()
    dicom_reader.Update()
    meta_dict = dicom_reader.GetMetaDataDictionaryArray()[0]

    image = dicom_reader.GetOutput()

    # Rescaling is performed on the entire input image instead of on a
    # per-slice basis to allow rescaling the image based on its global
    # minimum and maximum if `width` and `center` tags are not defined
    # in the DICOM. The output of this function is scaled between 0 and 255.
    rescaled_image = rescale_dicom_image_intensity(image, meta_dict)

    width, height = compute_real_width_and_height(rescaled_image, width,
                                                  height)

    image_dimension = rescaled_image.GetImageDimension()
    # Verifies that input image is 3D. This allows to simplify the logic after.
    if image_dimension != INPUT_IMAGE_DIMENSION:
        raise Exception("Input must be a %dD image. %d dimensions found." % (
            INPUT_IMAGE_DIMENSION, image_dimension))

    # Process each slice independently. This allows to only resample and
    # rescale the slices that will be saved at the end. NOTE: One could have
    # created a pipeline with `itk.pipeline()` which would only be run in the
    # end and only process requested regions, e.g. slice by slice. This method
    # would be useful if one wanted to resample the image in 3D instead of
    # processing each slice independently but is not necessary for now.
    image_size = itk.size(rescaled_image)

    size_sampling_dim = image_size[SLICING_DIMENSION]

    region = itk.ImageRegion[INPUT_IMAGE_DIMENSION]()
    new_size = itk.Size[INPUT_IMAGE_DIMENSION]()
    image_index = itk.Index[INPUT_IMAGE_DIMENSION]()

    for ii in range(INPUT_IMAGE_DIMENSION-1):
        new_size[ii] = image_size[ii]
    new_size[INPUT_IMAGE_DIMENSION-1] = 0

    region.SetSize(new_size)
    CollapsedImageType = itk.Image[itk.template(
        rescaled_image)[1][0], OUTPUT_IMAGE_DIMENSION]

    list_indices = []
    for ii in range(slices):
        slice_index = int((size_sampling_dim-1)*ii/(slices-1))
        image_index[SLICING_DIMENSION] = slice_index
        list_indices.append(slice_index)

        region.SetIndex(image_index)
        slice_image_filter = itk.ExtractImageFilter[
            rescaled_image, CollapsedImageType].New(
            rescaled_image, ExtractionRegion=region)
        slice_image_filter.SetDirectionCollapseToIdentity()
        slice_image_filter.Update()

        resampled_image = smooth_and_resample(slice_image_filter.GetOutput(),
                                              width, height)
        save_as_jpeg(resampled_image, out_dir, slice_index)
    # Generate JSON file
    generate_json(out_dir, list_indices)


if __name__ == '__main__':
    process()
