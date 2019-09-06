import pytest

import lamella.acquire

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)

# WARNING: We cannot test the autofocus function while Autoscript is offline
# using localhost, because it causes a focus cycling error.
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
    camera_settings = lamella.acquire.create_camera_settings(
        imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)
    )
    return camera_settings


def test__run_autocontrast(microscope):
    from autoscript_sdb_microscope_client.structures import RunAutoCbSettings

    result = lamella.acquire._run_autocontrast(microscope)
    assert isinstance(result, RunAutoCbSettings)


def test_autocontrast_autofocus(microscope):
    # WARNING: We cannot test the autofocus function if Autoscript is offline
    # using localhost, because it causes a focus cycling error.
    lamella.acquire.autocontrast_autofocus(
        microscope, autocontrast=True, autofocus=False
    )  # must stay false, cannot test this :(


def test_create_camera_settings(microscope):
    from autoscript_sdb_microscope_client.structures import GrabFrameSettings

    imaging_settings = {"resolution": "1536x1024", "dwell_time": 1e-6}
    result = lamella.acquire.create_camera_settings(
        imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)
    )
    assert isinstance(result, GrabFrameSettings)


def test_grab_ion_image(microscope, camera_settings):
    from autoscript_sdb_microscope_client.structures import AdornedImage

    result = lamella.acquire.grab_ion_image(microscope, camera_settings)
    assert isinstance(result, AdornedImage)
    # It appears Autoscript does not reliably report the beam type this way
    # assert result.metadata.acquisition.beam_type == 'Ion'


def test_grab_sem_image(microscope, camera_settings):
    from autoscript_sdb_microscope_client.structures import AdornedImage

    result = lamella.acquire.grab_sem_image(microscope, camera_settings)
    assert isinstance(result, AdornedImage)
    assert result.metadata.acquisition.beam_type == "Electron"
