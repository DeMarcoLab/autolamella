import numpy as np


def realspace_to_pixel_coordinate(coord, image):
    """Covert real space to pixel image coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    Parameters
    ----------
    coord : listlike, float
        In x, y format & real space units. Origin is at the image center.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    pixel_coord
        xy coordinate in pixels. Origin is at the top left.
    """
    coord = np.array(coord).astype(np.float64)
    y_shape, x_shape = image.data.shape
    pixelsize_x = image.metadata.binary_result.pixel_size.x
    # deliberately don't use the y pixel size, any tilt will throw this off
    coord /= pixelsize_x  # to pixels
    coord += np.array([x_shape / 2, y_shape / 2])  # reset origin to top left
    coord[1] = y_shape - coord[1]  # flip y-axis for relative coordinate system
    pixel_coord = [int(round(i)) for i in coord]
    return pixel_coord


def pixel_to_realspace_coordinate(coord, image):
    """Covert pixel image coordinate to real space coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    coord : listlike, float
        In x, y format & pixel units. Origin is at the top left.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    realspace_coord
        xy coordinate in real space. Origin is at the image center.
    """
    coord = np.array(coord).astype(np.float64)
    y_shape, x_shape = image.data.shape
    pixelsize_x = image.metadata.binary_result.pixel_size.x
    # deliberately don't use the y pixel size, any tilt will throw this off
    coord[1] = y_shape - coord[1]  # flip y-axis for relative coordinate system
    # reset origin to center
    coord -= np.array([x_shape / 2, y_shape / 2]).astype(np.int32)
    realspace_coord = list(np.array(coord) * pixelsize_x)  # to real space
    return realspace_coord


def realspace_to_relative_coordinate(coord, image):
    """Covert real space to relative image coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    Parameters
    ----------
    coord : Listlike, float
        In x, y format & real space units. Origin is at the image center.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    relative_coord
        xy relative coordinate. Origin is at the top left.
    """
    coord = np.array(coord).astype(np.float64)
    y_shape, x_shape = image.data.shape
    pixelsize_x = image.metadata.binary_result.pixel_size.x
    coord /= pixelsize_x  # to pixels
    coord += np.array([x_shape / 2, y_shape / 2])  # reset origin to top left
    coord[1] = y_shape - coord[1]  # flip y-axis for relative coordinate system
    relative_coord = list(coord / np.array([x_shape, y_shape]))
    return relative_coord


def relative_to_realspace_coordinate(coord, image):
    """Covert relative image coordinate to real space image coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    Parameters
    ----------
    coord : Listlike, float
        In x, y format & relative units. Origin is at the top left.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    realspace_coord
        xy coordinate in real space. Origin is at the center of the image.
    """
    coord = np.array(coord).astype(np.float64)
    if any(coord > 1) or any(coord < 0):
        raise ValueError(
            "Coordinate is out of bounds: "
            "relative coordinates must range between 0 and 1."
        )
    coord -= np.array([0.5, 0.5])  # reset origin to center
    y_shape, x_shape = image.data.shape
    pixelsize_x = image.metadata.binary_result.pixel_size.x
    coord *= np.array([x_shape, y_shape])  # to pixels
    coord[1] = -coord[1]  # flip y-axis
    realspace_coord = list(coord * pixelsize_x)  # to realspace
    return realspace_coord


def pixel_to_relative_coordinate(coord, image):
    """Covert pixel coordinate value to relative image coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    Parameters
    ----------
    coord : Listlike, float
        In x, y format & pixel units. Origin is at the top left.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    relative_coord
        xy relative coordinate. Origin is at the top left.
    """
    coord = np.array(coord).astype(np.float64)
    coord = pixel_to_realspace_coordinate(coord, image)
    relative_coord = realspace_to_relative_coordinate(coord, image)
    return relative_coord


def relative_to_pixel_coordinate(coord, image):
    """Covert relative image coordinate to real space coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuraccies if the sample is not flat in y.

    Parameters
    ----------
    coord : Listlike, float
        In x, y format & relative units. Origin is at the top left.
    image : AdorrnedImage
        Image the coordinate came from.

    Returns
    -------
    pixel_coord
        xy coordinate in pixels. Origin is at the top left.
    """
    coord = np.array(coord).astype(np.float64)
    coord = relative_to_realspace_coordinate(coord, image)
    pixel_coord = realspace_to_pixel_coordinate(coord, image)
    return pixel_coord
