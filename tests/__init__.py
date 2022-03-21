import os

import pytest
from autoscript_sdb_microscope_client.structures import Rectangle

import autolamella


@pytest.fixture(scope="session")
def microscope():
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    return microscope


@pytest.fixture
def settings():
    yaml_filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "protocol_offline.yml"
    )
    settings = autolamella.user_input.load_config(yaml_filename)
    settings["demo_mode"] = True
    settings["imaging"]["autocontrast"] = True
    settings["imaging"]["full_field_ib_images"] = True
    return settings


@pytest.fixture
def reduced_area_settings():
    yaml_filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "protocol_offline.yml"
    )
    reduced_area_settings = autolamella.user_input.load_config(yaml_filename)
    reduced_area_settings["demo_mode"] = True
    reduced_area_settings["imaging"]["autocontrast"] = True
    reduced_area_settings["imaging"]["full_field_ib_images"] = False
    return reduced_area_settings


@pytest.fixture
def camera_settings():
    imaging_settings = {"resolution": "3072x2048", "dwell_time": 1e-6}
    camera_settings = autolamella.acquire.create_camera_settings(
        imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)
    )
    return camera_settings
