import os

import numpy as np
import pytest

import autolamella
from autolamella.milling import _milling_coords, _microexpansion_coords

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


def test__milling_coords(microscope, settings):
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
    # Upper pattern
    result = _milling_coords(microscope, stage_settings, my_lamella, pattern="upper")
    assert result.scan_direction == "TopToBottom"
    assert np.isclose(result.width, stage_settings["lamella_width"])
    assert np.isclose(result.depth, stage_settings["milling_depth"])
    assert np.isclose(result.center_x, my_lamella.center_coord_realspace[0])
    assert np.isclose(result.height, 1)
    assert np.isclose(result.center_y, 1.5)
    # Lower pattern
    result = _milling_coords(microscope, stage_settings, my_lamella, pattern="lower")
    assert result.scan_direction == "BottomToTop"
    assert np.isclose(result.width, stage_settings["lamella_width"])
    assert np.isclose(result.depth, stage_settings["milling_depth"])
    assert np.isclose(result.center_x, my_lamella.center_coord_realspace[0])
    assert np.isclose(result.height, 1)
    assert np.isclose(result.center_y, -1.5)


def test__microexpansion_coords(microscope, settings):
    stage_settings = {
        "milling_depth": 300e-6,
        "lamella_width": 5,
        "lamella_height": 2,
        "total_cut_height": 10,
        "percentage_from_lamella_surface": 0,
        "percentage_roi_height": 0.1,
        "overtilt_degrees": 20,
        "microexpansion_width": 1.0e-6,
        "microexpansion_distance_from_lamella": 3e-6,
        "microexpansion_percentage_height": 0.6,
    }
    my_lamella = autolamella.sample.Lamella()
    my_lamella.center_coord_realspace = [0, 0]
    my_lamella.fiducial_coord_realspace = [-5, -5]
    # Upper pattern
    results = _microexpansion_coords(microscope, stage_settings, my_lamella)
    assert len(results) == 2

    for result in results:
        assert np.isclose(result.width, stage_settings["microexpansion_width"])
        assert np.isclose(result.depth, stage_settings["milling_depth"])

    if results[0].scan_direction == "LeftToRight" and results[1].scan_direction == "RightToLeft":
        result_l = results[0]
        result_r = results[1]
    elif results[0].scan_direction == "RightToLeft" and results[1].scan_direction == "LeftToRight":
        result_l = results[1]
        result_r = results[0]
    else:
        return pytest.fail("Patterns don't have correct scan direction!")

    assert np.isclose(result_l.center_y, result_r.center_y)
    assert np.isclose(-(result_l.center_x - my_lamella.center_coord_realspace[0]),
                      +(result_r.center_x - my_lamella.center_coord_realspace[0]))
