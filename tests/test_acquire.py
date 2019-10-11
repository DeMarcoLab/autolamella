import pytest

import autolamella.acquire

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)

from autoscript_sdb_microscope_client.structures import Rectangle


@pytest.fixture
def microscope():
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    return microscope


@pytest.fixture
def camera_settings():
    imaging_settings = {"resolution": "3072x2048", "dwell_time": 1e-6}
    camera_settings = autolamella.acquire.create_camera_settings(
        imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)
    )
    return camera_settings


def test_autocontrast(microscope):
    from autoscript_sdb_microscope_client.structures import RunAutoCbSettings

    result = autolamella.acquire.autocontrast(microscope)
    assert isinstance(result, RunAutoCbSettings)


def test_create_camera_settings(microscope):
    from autoscript_sdb_microscope_client.structures import GrabFrameSettings

    imaging_settings = {"resolution": "1536x1024", "dwell_time": 1e-6}
    result = autolamella.acquire.create_camera_settings(
        imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)
    )
    assert isinstance(result, GrabFrameSettings)


def test_grab_ion_image(microscope, camera_settings):
    from autoscript_sdb_microscope_client.structures import AdornedImage

    result = autolamella.acquire.grab_ion_image(microscope, camera_settings)
    assert isinstance(result, AdornedImage)
    # It appears Autoscript does not reliably report the beam type this way
    # assert result.metadata.acquisition.beam_type == 'Ion'


def test_grab_sem_image(microscope, camera_settings):
    from autoscript_sdb_microscope_client.structures import AdornedImage

    result = autolamella.acquire.grab_sem_image(microscope, camera_settings)
    assert isinstance(result, AdornedImage)
    assert result.metadata.acquisition.beam_type == "Electron"
