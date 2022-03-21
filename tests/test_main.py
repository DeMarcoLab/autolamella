from io import StringIO
import os
from unittest.mock import patch

import numpy as np
import pytest

import autolamella
from autolamella.main import main

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


def mock_fiducial(*args, **kwargs):
    coord = [-2e-6, -2e-6]
    relative_coord = [0.3, 0.73167421]
    pixel_coord = [307, 647]
    return coord, relative_coord, pixel_coord


def mock_set_lamella_center(self, image, settings):
    lamella_center_coord = [1e-6, 1e-6]
    self.center_coord_realspace = lamella_center_coord
    return lamella_center_coord


@pytest.mark.parametrize(
    "user_inputs",
    [
        # Add one regular lamella, cancel batch milling job.
        (StringIO("y\ny\ny\nn\n\n" + "n\nno\n")),
        # Add two regular lamellae, run batch milling job.
        (StringIO("y\ny\ny\nn\n\n" + "y\ny\ny\nn\n\n" + "n\nyes\n")),
        # Add two lamallae (one with custom milling depth), run batch milling.
        (StringIO("y\ny\ny\nn\n150e-6\n" + "y\ny\ny\nn\n\n" + "n\nyes\n")),
    ],
)
@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_main(user_inputs, settings, tmpdir, monkeypatch):
    settings["save_directory"] = tmpdir
    settings["demo_mode"] = True
    monkeypatch.setattr("sys.stdin", user_inputs)
    main(settings)


@pytest.mark.parametrize(
    "user_inputs",
    [
        # Add one regular lamella, cancel batch milling job.
        (StringIO("y\ny\ny\nn\n\n" + "n\nno\n")),
        # Add two regular lamellae, run batch milling job.
        (StringIO("y\ny\ny\nn\n\n" + "y\ny\ny\nn\n\n" + "n\nyes\n")),
        # Add two lamallae (one with custom milling depth), run batch milling.
        (StringIO("y\ny\ny\nn\n150e-6\n" + "y\ny\ny\nn\n\n" + "n\nyes\n")),
    ],
)
@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_main_reduced_area(user_inputs, reduced_area_settings, tmpdir, monkeypatch):
    reduced_area_settings["save_directory"] = tmpdir
    reduced_area_settings["demo_mode"] = True
    monkeypatch.setattr("sys.stdin", user_inputs)
    main(reduced_area_settings)
