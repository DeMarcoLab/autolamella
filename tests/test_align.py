import pytest
import numpy as np
import scipy.ndimage as ndi

from lamella.align import (
    calculate_beam_shift,
    normalize_image,
    _simple_register_translation,
)
import lamella.data
from lamella.mocktypes import MockAdornedImage


@pytest.mark.parametrize(
    "pixel_shift, pixel_size, expected_beam_shift",
    [
        (np.array([0, 20]), 1e-6, np.array([-0.0, +20e-6])),
        (np.array([10, 0]), 1e-6, np.array([-10e-6, +0.0])),
        (np.array([10, 20]), 1e-6, np.array([-10e-6, +20e-6])),
        (np.array([10, -20]), 1e-6, np.array([-10e-6, -20e-6])),
        (np.array([-10, 20]), 1e-6, np.array([+10e-6, +20e-6])),
        (np.array([-10, -20]), 1e-6, np.array([+10e-6, -20e-6])),
    ],
)
def test_calculate_beam_shift(pixel_shift, pixel_size, expected_beam_shift):
    data = np.random.random([512, 512])
    shifted_data = ndi.shift(data, np.flip(pixel_shift))
    reference_image = MockAdornedImage(
        data, pixelsize_x=pixel_size, pixelsize_y=pixel_size
    )
    shifted_image = MockAdornedImage(
        shifted_data, pixelsize_x=pixel_size, pixelsize_y=pixel_size
    )
    result = calculate_beam_shift(reference_image, shifted_image)
    assert np.allclose(result, expected_beam_shift)


@pytest.mark.parametrize(
    "shift",
    [
        (np.array([0, 20])),
        (np.array([10, 0])),
        (np.array([10, 20])),
        (np.array([10, -20])),
        (np.array([-10, 20])),
        (np.array([-10, -20])),
    ],
)
def test__simple_register_translation(shift):
    """Input shift in x, y format."""
    reference_image = np.random.random((512, 512))
    shifted_image = ndi.shift(reference_image, np.flip(shift))
    result = _simple_register_translation(reference_image, shifted_image)
    expected_shift = -1 * shift  # negative should return to original position
    assert np.allclose(result[:2], expected_shift)


@pytest.mark.parametrize(
    "image",
    [
        ((np.random.random((512, 512)) * 100) + 20),
        (lamella.data.autoscript_image()),
        (lamella.data.embryo()),
    ],
)
def test_normalize_image(image):
    output = normalize_image(image)
    assert np.isclose(np.mean(output), 0)
    assert np.isclose(np.std(output), 1)
