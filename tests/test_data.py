import os

import numpy as np
import pytest

import lamella.data


def test_adorned_image():
    autoscript = pytest.importorskip('autoscript_sdb_microscope_client',
                                     reason="Autoscript is not available.")
    adorned_image = lamella.data.adorned_image()
    assert adorned_image.data.shape == (884, 1024)


def test_embryo_image():
    img = lamella.data.embryo()
    assert img.shape == (2188, 3072)


def test_embryo_mask_image():
    img = lamella.data.embryo_mask()
    assert img.shape == (2188, 3072)


def test_load_image():
    filename = os.path.join(lamella.data.data_dir, 'embryo.png')
    img = lamella.data.load_image(filename)
    assert img.shape == (2188, 3072)


def test_mock_adorned_image():
    autoscript = pytest.importorskip('autoscript_sdb_microscope_client',
                                     reason="Autoscript is not available.")
    import fibsem.autoscript
    from autoscript_sdb_microscope_client import SdbMicroscopeClient
    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    expected = microscope.imaging.get_image()
    output = fibsem.data.mock_adorned_image()
    assert np.allclose(output.data, expected.data)
    assert np.isclose(output.metadata.binary_result.pixel_size.x,
                      expected.metadata.binary_result.pixel_size.x)
    assert np.isclose(output.metadata.binary_result.pixel_size.y,
                      expected.metadata.binary_result.pixel_size.y)
