import os

import numpy as np
import pytest

import lamella

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)


@pytest.fixture
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
    settings = lamella.user_input.load_config(yaml_filename)
    settings["demo_mode"] = True
    settings["imaging"]["autofocus"] = False  # cannot test this offline
    settings["imaging"]["autocontrast"] = True
    settings["imaging"]["full_field_ib_images"] = True
    return settings


def test_mill_all_stages_empty_list(microscope):
    result = lamella.milling.mill_all_stages(microscope, {}, [], {})
    assert result is None


def test_save_final_images(microscope, settings, tmpdir):
    settings["save_directory"] = tmpdir
    lamella.milling.save_final_images(microscope, settings, 1)
