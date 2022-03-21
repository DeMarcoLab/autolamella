import numpy as np
import pytest

import autolamella.data
from autolamella.conversions import (
    realspace_to_pixel_coordinate,
    pixel_to_realspace_coordinate,
    realspace_to_relative_coordinate,
    relative_to_realspace_coordinate,
    pixel_to_relative_coordinate,
    relative_to_pixel_coordinate,
)
from autolamella.data.mocktypes import MockAdornedImage


@pytest.fixture
def image():
    image_array = np.random.random((10, 10))
    return MockAdornedImage(image_array, pixelsize_x=1e-6, pixelsize_y=1e-6)


@pytest.mark.dependency(depends=["test_initialize"])
def test_conversion_types():
    pytest.importorskip("autoscript_sdb_microscope_client",
                        reason="Autoscript is not available.")
    image = autolamella.data.adorned_image()
    input_coord = [0, 0]
    assert isinstance(realspace_to_pixel_coordinate(input_coord, image), list)
    assert isinstance(pixel_to_realspace_coordinate(input_coord, image), list)
    assert isinstance(realspace_to_relative_coordinate(input_coord, image), list)
    assert isinstance(relative_to_realspace_coordinate(input_coord, image), list)
    assert isinstance(pixel_to_relative_coordinate(input_coord, image), list)
    assert isinstance(relative_to_pixel_coordinate(input_coord, image), list)


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([0, 0], [5, 5]),
        ([1e-6, 0], [6, 5]),
        ([0, 1e-6], [5, 4]),
        ([1e-6, 1e-6], [6, 4]),
        ([-1e-6, -1e-6], [4, 6]),
        ([-1e-6, 1e-6], [4, 4]),
        ([1e-6, -1e-6], [6, 6]),
    ],
)
def test_realspace_to_pixel_coordinate(coord, image, expected_output):
    result = realspace_to_pixel_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([5, 5], [0, 0]),
        ([6, 5], [1e-6, 0]),
        ([5, 4], [0, 1e-6]),
        ([6, 4], [1e-6, 1e-6]),
        ([4, 6], [-1e-6, -1e-6]),
        ([4, 4], [-1e-6, 1e-6]),
        ([6, 6], [1e-6, -1e-6]),
    ],
)
def test_pixel_to_realspace_coordinate(coord, image, expected_output):
    result = pixel_to_realspace_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([0, 0], [0.5, 0.5]),
        ([5e-6, 0], [1.0, 0.5]),
        ([0, 5e-6], [0.5, 0.0]),
        ([-5e-6, 0], [0.0, 0.5]),
        ([0, -5e-6], [0.5, 1.0]),
        ([5e-6, 5e-6], [1.0, 0.0]),
        ([-5e-6, -5e-6], [0.0, 1.0]),
    ],
)
def test_realspace_to_relative_coordinate(coord, image, expected_output):
    result = realspace_to_relative_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([0.5, 0.5], [0, 0]),
        ([1.0, 0.5], [5e-6, 0]),
        ([0.5, 0.0], [0, 5e-6]),
        ([0.0, 0.5], [-5e-6, 0]),
        ([0.5, 1.0], [0, -5e-6]),
        ([1.0, 0.0], [5e-6, 5e-6]),
        ([0.0, 1.0], [-5e-6, -5e-6]),
    ],
)
def test_relative_to_realspace_coordinate(coord, image, expected_output):
    result = relative_to_realspace_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([0, 0], [0, 0]),
        ([5, 5], [0.5, 0.5]),
        ([10, 10], [1.0, 1.0]),
        ([0, 10], [0, 1.0]),
        ([10, 0], [1.0, 0]),
    ],
)
def test_pixel_to_relative_coordinate(coord, image, expected_output):
    result = pixel_to_relative_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "coord, expected_output",
    [
        ([0, 0], [0, 0]),
        ([0.5, 0.5], [5, 5]),
        ([1.0, 1.0], [10, 10]),
        ([0, 1.0], [0, 10]),
        ([1.0, 0], [10, 0]),
    ],
)
def test_relative_to_pixel_coordinate(coord, image, expected_output):
    result = relative_to_pixel_coordinate(coord, image)
    assert np.allclose(np.array(result), np.array(expected_output))


@pytest.mark.parametrize(
    "input_value",
    [([0, 0]), ([1e-6, 1e-6]), ([-1e-6, 1e-6]), ([1e-6, -1e-6]), ([-1e-6, -1e-6])],
)
def test_roundtrip_realspace_pixels_realspace(input_value, image):
    output = pixel_to_realspace_coordinate(
        realspace_to_pixel_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)


@pytest.mark.parametrize(
    "input_value",
    [([0, 0]), ([1e-6, 1e-6]), ([-1e-6, 1e-6]), ([1e-6, -1e-6]), ([-1e-6, -1e-6])],
)
def test_roundtrip_realspace_relative_realspace(input_value, image):
    output = relative_to_realspace_coordinate(
        realspace_to_relative_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)


@pytest.mark.parametrize(
    "input_value", [([0, 0]), ([5, 5]), ([2, 8]), ([8, 2]), ([10, 10])]
)
def test_roundtrip_pixels_realspace_pixels(input_value, image):
    output = realspace_to_pixel_coordinate(
        pixel_to_realspace_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)


@pytest.mark.parametrize(
    "input_value", [([0, 0]), ([5, 5]), ([2, 8]), ([8, 2]), ([10, 10])]
)
def test_roundtrip_pixels_relative_pixels(input_value, image):
    output = relative_to_pixel_coordinate(
        pixel_to_relative_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)


@pytest.mark.parametrize(
    "input_value", [([0, 0]), ([0.5, 0.5]), ([0.2, 0.8]), ([0.8, 0.2]), ([1.0, 1.0])]
)
def test_roundtrip_relative_pixels_relative(input_value, image):
    output = pixel_to_relative_coordinate(
        relative_to_pixel_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)


@pytest.mark.parametrize(
    "input_value", [([0, 0]), ([0.5, 0.5]), ([0.2, 0.8]), ([0.8, 0.2]), ([1.0, 1.0])]
)
def test_roundtrip_relative_realspace_relative(input_value, image):
    output = realspace_to_relative_coordinate(
        relative_to_realspace_coordinate(input_value, image), image
    )
    assert np.allclose(output, input_value)
