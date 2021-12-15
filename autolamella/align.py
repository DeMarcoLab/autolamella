import logging

import numpy as np
import scipy.ndimage as ndi
import skimage.draw
import skimage.io

__all__ = ["realign"]


def realign(microscope, new_image, reference_image):
    """Realign to reference image using beam shift.

    Parameters
    ----------
    microscope : Autoscript microscope object
    new_image : The most recent image acquired.
        Must have the same dimensions and relative position as the reference.
    reference_image : The reference image to align with.
        Muast have the same dimensions and relative position as the new image
    Returns
    -------
    microscope.beams.ion_beam.beam_shift.value
        The current beam shift position (after any realignment)
    """
    from autoscript_core.common import ApplicationServerException

    shift_in_meters = _calculate_beam_shift(new_image, reference_image)
    try:
        microscope.beams.ion_beam.beam_shift.value += shift_in_meters
    except ApplicationServerException:
        logging.warning(
            "Cannot move beam shift beyond limits, "
            "will continue with no beam shift applied."
        )
    return microscope.beams.ion_beam.beam_shift.value


def _calculate_beam_shift(image_1, image_2):
    """Cross correlation to find shift between two images.

    Parameters
    ----------
    image_1 : AdornedImage
        Original image to use as reference point.
    image_2 : AdornedImage
        Possibly shifted image to align with original.

    Returns
    -------
    realspace_beam_shift
        Beam shift in x, y format (meters), list of floats.

    Raises
    ------
    ValueError
        If images are not the same dimensions, raise a ValueError.
    """
    if image_1.data.shape != image_2.data.shape:
        raise ValueError("Images must be the same shape for cross correlation.")
    mask_image_1 = _mask_circular(image_1.data.shape)
    mask_image_2 = _mask_rectangular(image_2.data.shape)
    norm_image_1 = _normalize_image(image_1.data) * mask_image_1
    norm_image_2 = _normalize_image(image_2.data) * mask_image_2
    pixel_shift = _simple_register_translation(norm_image_2, norm_image_1)
    # Autoscript y-axis has an inverted positive direction
    pixel_shift[1] = -pixel_shift[1]
    pixelsize_x = image_1.metadata.binary_result.pixel_size.x
    realspace_beam_shift = pixel_shift * pixelsize_x
    logging.info("pixel_shift calculated = {}".format(pixel_shift))
    logging.info("realspace_beam_shift calculated = {}".format(realspace_beam_shift))
    return realspace_beam_shift


def _simple_register_translation(src_image, target_image, max_shift_mask=None):
    """Calculate pixel shift between two input images.

    This function runs with numpy or cupy for GPU acceleration.

    Parameters
    ----------
    src_image : array
        Reference image.
    target_image : array
        Image to register.  Must be same dimensionality as ``src_image``.
    max_shift_mask : array
        The fourier mask restricting the maximum allowable pixel shift.

    Returns
    -------
    shifts : ndarray
        Pixel shift in x, y order between target and source image.

    References
    ----------
    scikit-image register_translation function in the skimage.feature module.
    """
    src_freq = np.fft.fftn(src_image)
    target_freq = np.fft.fftn(target_image)
    print('using bp mask')
    bp_mask = _bandpass_mask(target_image.data.shape, target_image.data.shape / 3, inner_radius=2, sigma=3)
    bp_target_freq = bp_mask * target_freq

    # Whole-pixel shift - Compute cross-correlation by an IFFT
    shape = src_freq.shape
    image_product = src_freq * bp_target_freq.conj()
    cross_correlation = np.fft.ifftn(image_product)
    # Locate maximum
    maxima = np.unravel_index(
        np.argmax(np.abs(cross_correlation)), cross_correlation.shape
    )
    midpoints = np.array([float(np.round(axis_size / 2)) for axis_size in shape])
    shifts = np.array(maxima, dtype=np.float64)
    shifts[shifts > midpoints] -= np.array(shape)[shifts > midpoints]
    shifts = np.flip(shifts, axis=0).astype(np.int)  # x, y order
    return shifts


def _normalize_image(image, mask=None):
    """Ensure the image mean is zero and the standard deviation is one.

    Parameters
    ----------
    image : ndarray
        The input image array.
    mask : ndarray, optional
        A mask image containing values between zero and one.
        Dimensions must match the input image.

    Returns
    -------
    ndarray
        The normalized image.
        The mean intensity is equal to zero and standard deviation equals one.
    """
    image = image - np.mean(image)
    image = image / np.std(image)
    if mask:
        image = image * mask
    return image


def _mask_circular(image_shape, sigma=5.0, *, radius=None):
    """Make a circular mask with soft edges for image normalization.

    Parameters
    ----------
    image_shape : tuple
        Shape of the original image array
    sigma : float, optional
        Sigma value (in pixels) for gaussian blur function, by default 5.
    radius : int, optional
        Radius of circle, by default None which will create a circle that fills
        90% of the smallest image dimension.

    Returns
    -------
    ndarray
        Circular mask with soft edges in array matching the input image_shape
    """
    if radius is None:
        # leave at least a 5% gap on each edge
        radius = 0.45 * min(image_shape)
    r, c = np.array(np.array(image_shape) / 2).astype(int)  # center point
    rr, cc = skimage.draw.circle(r, c, radius=radius, shape=image_shape)
    mask = np.zeros(image_shape)
    mask[rr, cc] = 1.0
    mask = ndi.gaussian_filter(mask, sigma=sigma)
    return mask


def _mask_rectangular(image_shape, sigma=5.0, *, start=None, extent=None):
    """Make a rectangular mask with soft edges for image normalization.

    Parameters
    ----------
    image_shape : tuple
        Shape of the original image array
    sigma : float, optional
        Sigma value (in pixels) for gaussian blur function, by default 5.
    start : tuple, optional
        Origin point of the rectangle, e.g., ([plane,] row, column).
        Default start is 5% of the total image width and height.
    extent : int, optional
        The extent (size) of the drawn rectangle.
        E.g., ([num_planes,] num_rows, num_cols).
        Default is for the rectangle to cover 95% of the image width & height.

    Returns
    -------
    ndarray
        Rectangular mask with soft edges in array matching input image_shape.
    """
    if extent is None:
        # leave at least a 5% gap on each edge
        start = np.round(np.array(image_shape) * 0.05)
        extent = np.round(np.array(image_shape) * 0.90)
    rr, cc = skimage.draw.rectangle(start, extent=extent, shape=image_shape)
    mask = np.zeros(image_shape)
    mask[rr.astype(int), cc.astype(int)] = 1.0
    mask = ndi.gaussian_filter(mask, sigma=sigma)
    return mask


def _bandpass_mask(image_shape, outer_radius, inner_radius=0, sigma=5):
    """Create a fourier bandpass mask.

    Parameters
    ----------
    image_shape : tuple
        Shape of the original image array
    outer_radius : int
        Outer radius for bandpass filter array.
    inner_radius : int, optional
        Inner radius for bandpass filter array, by default 0
    sigma : int, optional
        Sigma value for edge blending, by default 5 pixels.

    Returns
    -------
    _bandpass_mask : ndarray
        The bandpass image mask.
    """
    _bandpass_mask = np.zeros(image_shape)
    r, c = np.array(image_shape) / 2
    inner_circle_rr, inner_circle_cc = skimage.draw.circle(
        r, c, inner_radius, shape=image_shape
    )
    outer_circle_rr, outer_circle_cc = skimage.draw.circle(
        r, c, outer_radius, shape=image_shape
    )
    _bandpass_mask[outer_circle_rr, outer_circle_cc] = 1.0
    _bandpass_mask[inner_circle_rr, inner_circle_cc] = 0.0
    _bandpass_mask = ndi.gaussian_filter(_bandpass_mask, sigma)
    _bandpass_mask = np.array(_bandpass_mask)
    # fourier space origin should be in the corner
    _bandpass_mask = np.roll(
        _bandpass_mask, (np.array(image_shape) / 2).astype(int), axis=(0, 1)
    )
    return _bandpass_mask
