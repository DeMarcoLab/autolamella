from io import StringIO
import os

import numpy as np
import pytest

from autolamella.user_input import (
    ask_user,
    choose_directory,
    load_config,
    protocol_stage_settings,
    validate_user_input,
    _add_missing_keys,
    _format_dictionary,
    _validate_application_files,
    _validate_dwell_time,
    _validate_ion_beam_currents,
    _validate_horizontal_field_width,
    _validate_scanning_resolutions,
    _validate_scanning_rotation,
)

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)


@pytest.fixture
def microscope():
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    microscope.beams.ion_beam.scanning.rotation.value = 0.0
    return microscope


@pytest.fixture
def expected_user_input():
    user_input_dictionary = {
        "demo_mode": False,
        "imaging": {"autocontrast": 1.0},
        "fiducial": {"fiducial_length": 0.1, "fiducial_width": 0.02},
        "lamella": {
            "lamella_width": 5e-06,
            "lamella_height": 1e-06,
            "protocol_stages": [
                {
                    "percentage_roi_height": 0.5,
                    "percentage_from_lamella_surface": 0.5,
                    "milling_current": 3e-10,
                    "milling_depth": 5e-07,
                },
                {
                    "percentage_roi_height": 0.3,
                    "percentage_from_lamella_surface": 0.2,
                    "milling_current": 3e-10,
                },
                {
                    "percentage_roi_height": 0.2,
                    "percentage_from_lamella_surface": 0.0,
                    "milling_current": 3e-10,
                    "overtilt_degrees": 2.0,
                },
            ],
            "overtilt_degrees": 0.0,
        },
    }
    return user_input_dictionary


@pytest.mark.parametrize(
    "test_input, default, expected",
    [
        (StringIO("\n"), "yes", True),
        (StringIO("\n"), "no", False),
        (StringIO("y\n"), None, True),
        (StringIO("Y\n"), None, True),
        (StringIO("yes\n"), None, True),
        (StringIO("Yes\n"), None, True),
        (StringIO("YES\n"), None, True),
        (StringIO("n\n"), None, False),
        (StringIO("N\n"), None, False),
        (StringIO("no\n"), None, False),
        (StringIO("No\n"), None, False),
        (StringIO("NO\n"), None, False),
    ],
)
def test_ask_user(monkeypatch, test_input, default, expected):
    monkeypatch.setattr("sys.stdin", test_input)
    result = ask_user("message", default=default)
    assert result == expected


def test_load_config(expected_user_input):
    yaml_filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "test_user_input.yml"
    )
    result = load_config(yaml_filename)
    assert result == expected_user_input


def test_validate_user_input(microscope):
    settings = {
        "system": {
            "ip_address": "localhost",
            "application_file_rectangle": "Si",
            "application_file_cleaning_cross_section": "Si",
        },
        "imaging": {"resolution": "1536x1024", "dwell_time": 1e-7},
        "fiducial": {
            "fiducial_milling_current": 3.64e-10,
            "reduced_area_resolution": "3072x2048",
        },
        "lamella": {"milling_depth": 1e-6, "milling_current": 3.64e-10},
    }
    settings = _format_dictionary(settings)
    validate_user_input(microscope, settings)


def test__validate_application_files(microscope):
    application_files = ["Si"]
    _validate_application_files(microscope, application_files)


def test__validate_application_files_invalid(microscope):
    application_files = ["involid", "invalid"]
    with pytest.raises(ValueError):
        _validate_application_files(microscope, application_files)


@pytest.mark.parametrize(
    "dwell",
    [
        (1e-12),  # minimum dwell time limit
        (1e-11),
        (1e-10),
        (1e-9),
        (1e-8),
        (1e-7),
        (1e-6),
        (1e-5),
        (1e-4),
        (0.001),  # maximum dwell time limit
    ],
)
def test__validate_dwell_time(microscope, dwell):
    dwell_times = [dwell]
    _validate_dwell_time(microscope, dwell_times)


@pytest.mark.parametrize(
    "dwell",
    [
        (1e-13),  # too small
        (0.01),  # too large
        (np.nan),  # NaN
        (np.inf),  # Inf
        ("string"),  # string
    ],
)
def test__validate_dwell_time_invalid(microscope, dwell):
    dwell_times = [dwell]
    with pytest.raises(ValueError):
        _validate_dwell_time(microscope, dwell_times)


def test__validate_ion_beam_currents(microscope):
    milling_currents = microscope.beams.ion_beam.beam_current.available_values
    _validate_ion_beam_currents(microscope, milling_currents)


def test__validate_ion_beam_currents_invalid(microscope):
    milling_currents = ["invalid", "invalid"]
    with pytest.raises(ValueError):
        _validate_ion_beam_currents(microscope, milling_currents)


@pytest.mark.parametrize(
    "hfw",
    [
        (1e-12),  # minimum limit for ion beam horizontal field width
        (1e-11),
        (1e-10),
        (1e-9),
        (1e-8),
        (1e-7),
        (1e-6),
        (1e-5),
        (1e-4),
        (0.001),  # maximum limit for ion beam horizontal field width
    ],
)
def test__validate_horizontal_field_width(microscope, hfw):
    horizontal_field_widths = [hfw]
    _validate_horizontal_field_width(microscope, horizontal_field_widths)


@pytest.mark.parametrize(
    "hfw",
    [
        (1e-13),  # too small
        (0.01),  # too large
        (np.nan),  # NaN
        (np.inf),  # Inf
        ("string"),  # string
    ],
)
def test__validate_horizontal_field_width_invalid(microscope, hfw):
    horizontal_field_widths = [hfw]
    with pytest.raises(ValueError):
        _validate_horizontal_field_width(microscope, horizontal_field_widths)


def test__validate_scanning_resolutions(microscope):
    resolutions = ["1536x1024", "3072x2048"]
    _validate_scanning_resolutions(microscope, resolutions)


def test__validate_scanning_resolutions_invalid(microscope):
    resolutions = ["invalid", "invalid"]
    with pytest.raises(ValueError):
        _validate_scanning_resolutions(microscope, resolutions)


@pytest.mark.parametrize("rotation", [(np.deg2rad(0.0))])
def test__validate_scanning_rotation(rotation):
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    microscope.beams.ion_beam.scanning.rotation.value = rotation
    _validate_scanning_rotation(microscope)
    microscope.beams.ion_beam.scanning.rotation.value = 0.0


@pytest.mark.parametrize("invalid_rotation", [(123), (-123)])
def test__validate_scanning_rotation_invalid(invalid_rotation):
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    microscope.beams.ion_beam.scanning.rotation.value = invalid_rotation
    with pytest.raises(ValueError):
        _validate_scanning_rotation(microscope)
    microscope.beams.ion_beam.scanning.rotation.value = 0.0
