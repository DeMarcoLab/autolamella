import os

import numpy as np
import pytest

from autolamella.validate import (
    validate_user_input,
    _validate_application_files,
    _validate_dwell_time,
    _validate_ion_beam_currents,
    _validate_horizontal_field_width,
    _validate_scanning_resolutions,
    _validate_scanning_rotation,
)
from autolamella.user_input import _format_dictionary

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


@pytest.mark.parametrize("rotation", [(np.deg2rad(0.0)), (np.deg2rad(180.0))])
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
