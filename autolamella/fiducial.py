from autolamella.conversions import (
    realspace_to_pixel_coordinate,
    realspace_to_relative_coordinate,
)
from autolamella.display import quick_plot, InteractiveRectangle


def select_fiducial_point(image, fiducial_fov_x, fiducial_fov_y):
    fig, ax = quick_plot(image)
    pixelsize_x = image.metadata.binary_result.pixel_size.x
    field_of_view_x = [
        -(image.width * pixelsize_x) / 2,
        +(image.width * pixelsize_x) / 2,
    ]
    field_of_view_y = [
        -(image.height * pixelsize_x) / 2,
        +(image.height * pixelsize_x) / 2,
    ]
    myfig = InteractiveRectangle(
        fig,
        ax,
        roi_size_x=fiducial_fov_x,
        roi_size_y=fiducial_fov_y,
        fov_x=field_of_view_x,
        fov_y=field_of_view_y,
    )
    myfig.show()
    return myfig.coords


def fiducial(
    microscope,
    image,
    fiducial_length,
    fiducial_width,
    fiducial_fov_x,
    fiducial_fov_y,
    fiducial_milling_depth=300e-9,
):
    """Create cross to mill for drift correction fiducial.

    By default, the rectangle milling patterns that make up the cross have
    * length of 12% of the image field of view, and a
    * width of 3% of the image field of view.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    image : AdornedImage
        Current ion bream image.
    fiducial_length : float,
        Real space size, length of fiducial marker.
    fiducial_width : float
       Real space size, width of fiducial rectangle bars.
    fiducial_fov_x :
        Real space width of the fiducial reduced area field of view.
    fiducial_fov_y :
        Real space height of the fiducial reduced area field of view.
    fiducial_milling_depth : float, optional
        Depth of milling pattern in metres, by default 1e-6 (1 micron)

    Returns
    -------
    realspace_coord, relative_coord, pixel_coord
    """
    if (fiducial_fov_x < fiducial_length) or (fiducial_fov_y < fiducial_length):
        raise ValueError(
            "'fiducial_image_size_x' and 'fiducial_image_size_y' "
            "must be equal or greater than 'fiducial_length'. "
            "Please check your input user settings and try again."
        )
    coord = select_fiducial_point(image, fiducial_fov_x, fiducial_fov_y)
    if coord == []:  # user did not select a fiducial location
        return
    rectangle_1 = microscope.patterning.create_rectangle(
        coord[0], coord[1], fiducial_width, fiducial_length, fiducial_milling_depth
    )
    rectangle_2 = microscope.patterning.create_rectangle(
        coord[0], coord[1], fiducial_length, fiducial_width, fiducial_milling_depth
    )
    relative_coord = realspace_to_relative_coordinate(coord, image)
    pixel_coord = realspace_to_pixel_coordinate(coord, image)
    return coord, relative_coord, pixel_coord


def fiducial_image(image, relative_center, relative_size=[0.15, 0.15]):
    """Crop an image to return just the fiducial marker area.

    Parameters
    ----------
    image : AdornedImage
        Input image.
    relative_center : list of floats
        Center coordinate x, y format; relative coordinates (between 0 and 1)
    relative_size : list of floats, optional
        Relative size of cropped image, by default [0.15, 0.15]

    Returns
    -------
    AdornedImage
        Cropped image
    """
    import autoscript_toolkit.vision as vision_toolkit

    cropped_image = vision_toolkit.cut_image(
        image, relative_center=relative_center, relative_size=relative_size
    )
    return cropped_image


def fiducial_reduced_area_rect(fiducial_relative_center, fiducial_relative_size):
    """Return autoscript Rectangle object describing the fiducial reduced area

    Returns
    -------
    Autoscript Rectangle
        Fiducial reduced area rectangle, in relative units.
    """
    from autoscript_sdb_microscope_client.structures import Rectangle

    width, height = fiducial_relative_size
    top_left_x = fiducial_relative_center[0] - (width / 2)
    top_left_y = fiducial_relative_center[1] - (height / 2)
    if top_left_x < 0:
        top_left_x = 0
    if top_left_x > 1:
        raise ValueError("top_left_x relative coordinate cannot be larger than 1")
    if top_left_y < 0:
        top_left_y = 0
    if top_left_y > 1:
        raise ValueError("top_left_y relative coordinate cannot be larger than 1")
    # create the relative rectangle
    fiducial_reduced_area = Rectangle(top_left_x, top_left_y, width, height)
    print("fiducial_reduced_area", fiducial_reduced_area)
    return fiducial_reduced_area
