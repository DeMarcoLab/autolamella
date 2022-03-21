import os

import matplotlib.pyplot as plt
import numpy as np
import pytest

import autolamella.data


@pytest.mark.mpl_image_compare
def test_mpl_autoscript_image():
    image = autolamella.data.autoscript_image()
    fig, ax = plt.subplots(1)
    ax.imshow(image, cmap="gray")
    return fig


def test_autoscript_image():
    result = autolamella.data.autoscript_image()
    assert result.shape == (884, 1024)


@pytest.mark.dependency(depends=["test_initialize"])
def test_adorned_image():
    pytest.importorskip(
        "autoscript_sdb_microscope_client", reason="Autoscript is not available."
    )
    adorned_image = autolamella.data.adorned_image()
    assert adorned_image.data.shape == (884, 1024)


def test_load_image():
    filename = os.path.join(autolamella.data.data_dir, "autoscript.png")
    result = autolamella.data.load_image(filename)
    assert result.shape == (884, 1024)


@pytest.mark.dependency(depends=["test_connect_microscope"])
def test_mock_adorned(microscope):
    expected = microscope.imaging.get_image()
    output = autolamella.data.mock_adorned_image()
    assert np.allclose(output.data, expected.data)
    assert np.isclose(
        output.metadata.binary_result.pixel_size.x,
        expected.metadata.binary_result.pixel_size.x,
    )
    assert np.isclose(
        output.metadata.binary_result.pixel_size.y,
        expected.metadata.binary_result.pixel_size.y,
    )
