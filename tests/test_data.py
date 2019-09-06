import os

import matplotlib.pyplot as plt
import numpy as np
import pytest

import lamella.data


@pytest.mark.mpl_image_compare
def test_mpl_autoscript_image():
    image = lamella.data.autoscript_image()
    fig, ax = plt.subplots(1)
    ax.imshow(image, cmap="gray")
    return fig


@pytest.mark.mpl_image_compare
def test_mpl_embryo():
    image = lamella.data.embryo()
    fig, ax = plt.subplots(1)
    ax.imshow(image, cmap="gray")
    return fig


@pytest.mark.mpl_image_compare
def test_mpl_embryo_mask():
    image = lamella.data.embryo_mask()
    fig, ax = plt.subplots(1)
    ax.imshow(image, cmap="gray")
    return fig


def test_autoscript_image():
    result = lamella.data.autoscript_image()
    assert result.shape == (884, 1024)


def test_adorned_image():
    autoscript = pytest.importorskip(
        "autoscript_sdb_microscope_client", reason="Autoscript is not available."
    )
    adorned_image = lamella.data.adorned_image()
    assert adorned_image.data.shape == (884, 1024)


def test_embryo():
    result = lamella.data.embryo()
    assert result.shape == (2188, 3072)


def test_embryo_adorned():
    result = lamella.data.embryo_adorned()
    assert result.data.shape == (2188, 3072)
    assert result.metadata.binary_result.pixel_size.x == 1e-6
    assert result.metadata.binary_result.pixel_size.y == 1e-6


def test_embryo_mask():
    result = lamella.data.embryo_mask()
    assert result.shape == (2188, 3072)


def test_embryo_mask_adorned():
    result = lamella.data.embryo_mask_adorned()
    assert result.data.shape == (2188, 3072)
    assert result.metadata.binary_result.pixel_size.x == 1e-6
    assert result.metadata.binary_result.pixel_size.y == 1e-6


def test_load_image():
    filename = os.path.join(lamella.data.data_dir, "embryo.png")
    result = lamella.data.load_image(filename)
    assert result.shape == (2188, 3072)


def test_mock_adorned():
    autoscript = pytest.importorskip(
        "autoscript_sdb_microscope_client", reason="Autoscript is not available."
    )
    import lamella.autoscript
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    expected = microscope.imaging.get_image()
    output = lamella.data.mock_adorned_image()
    assert np.allclose(output.data, expected.data)
    assert np.isclose(
        output.metadata.binary_result.pixel_size.x,
        expected.metadata.binary_result.pixel_size.x,
    )
    assert np.isclose(
        output.metadata.binary_result.pixel_size.y,
        expected.metadata.binary_result.pixel_size.y,
    )
