from io import StringIO
from unittest.mock import patch

import pytest

from autolamella.main import main


def mock_fiducial(*args, **kwargs):
    coord = [-2e-6, -2e-6]
    relative_coord = [0.3, 0.73167421]
    pixel_coord = [307, 647]
    return coord, relative_coord, pixel_coord


def mock_set_lamella_center(self, image, settings):
    lamella_center_coord = [1e-6, 1e-6]
    self.center_coord_realspace = lamella_center_coord
    return lamella_center_coord


@pytest.mark.dependency(depends=["test_initialize"])
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


@pytest.mark.dependency(depends=["test_initialize"])
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
