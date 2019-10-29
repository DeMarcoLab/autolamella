import os

import numpy as np
import pytest

import autolamella
from autolamella.milling import _upper_milling_coords, _lower_milling_coords

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
    settings = autolamella.user_input.load_config(yaml_filename)
    settings["demo_mode"] = True
    settings["imaging"]["autocontrast"] = True
    settings["imaging"]["full_field_ib_images"] = True
    return settings


def test_mill_all_stages_empty_list(microscope):
    result = autolamella.milling.mill_all_stages(microscope, {}, [], {})
    assert result is None


def test_save_final_images(microscope, settings, tmpdir):
    settings["save_directory"] = tmpdir
    autolamella.milling.save_final_images(microscope, settings, 1)


def test__upper_milling_coords(microscope, settings):
    stage_settings = {
        "milling_depth": 300e-6,
        "lamella_width": 5,
        "lamella_height": 2,
        "total_cut_height": 10,
        "percentage_from_lamella_surface": 0,
        "percentage_roi_height": 0.1,
        "overtilt_degrees": 20,
    }
    my_lamella = autolamella.sample.Lamella()
    my_lamella.center_coord_realspace = [0, 0]
    my_lamella.fiducial_coord_realspace = [-5, -5]
    result = _upper_milling_coords(microscope, stage_settings, my_lamella)
    assert result.scan_direction == "TopToBottom"
    assert np.isclose(result.width, stage_settings["lamella_width"])
    assert np.isclose(result.depth, stage_settings["milling_depth"])
    assert np.isclose(result.center_x, my_lamella.center_coord_realspace[0])
    assert np.isclose(result.height, 1)
    assert np.isclose(result.center_y, 1.5)


def test__lower_milling_coords(microscope, settings):
    stage_settings = {
        "milling_depth": 300e-6,
        "lamella_width": 5,
        "lamella_height": 2,
        "total_cut_height": 10,
        "percentage_from_lamella_surface": 0,
        "percentage_roi_height": 0.1,
        "overtilt_degrees": 20,
    }
    my_lamella = autolamella.sample.Lamella()
    my_lamella.center_coord_realspace = [0, 0]
    my_lamella.fiducial_coord_realspace = [-5, -5]
    result = _lower_milling_coords(microscope, stage_settings, my_lamella)
    assert result.scan_direction == "BottomToTop"
    assert np.isclose(result.width, stage_settings["lamella_width"])
    assert np.isclose(result.depth, stage_settings["milling_depth"])
    assert np.isclose(result.center_x, my_lamella.center_coord_realspace[0])
    assert np.isclose(result.height, 1)
    assert np.isclose(result.center_y, -1.5)
