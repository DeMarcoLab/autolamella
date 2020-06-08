from io import StringIO
import os
from unittest.mock import patch

import pytest

import autolamella.add_samples
import autolamella.data
import autolamella.sample

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


def mock_select_fiducial(*args, **kwargs):
    realspace_center_coordinate = [-2e-6, -2e-6]
    return realspace_center_coordinate


def mock_no_fiducial(*args, **kwargs):
    return []


def mock_fiducial(*args, **kwargs):
    coord = [-2e-6, -2e-6]
    relative_coord = [0.3, 0.73167421]
    pixel_coord = [307, 647]
    return coord, relative_coord, pixel_coord


def mock_set_lamella_center(self, image, settings):
    lamella_center_coord = [1e-6, 1e-6]
    self.center_coord_realspace = lamella_center_coord
    return lamella_center_coord


def mock_no_lamella_center(*args, **kwargs):
    return []


@patch("autolamella.fiducial.select_fiducial_point", new=mock_select_fiducial)
def test_add_fiducial(microscope, settings):
    image = autolamella.data.adorned_image()
    result = autolamella.fiducial.fiducial(
        microscope, image, 1e-6, 1e-6, 1.5e-6, 1.5e-6, 300e-9
    )
    expected_result_0 = [-2e-6, -2e-6]
    expected_result_1 = [0.30000000000000004, 0.7316742081447963]
    expected_result_2 = [307, 647]
    assert result[0] == expected_result_0
    assert result[1] == expected_result_1
    assert result[2] == expected_result_2


@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_set_center(settings):
    expected_lamella_center = [1e-6, 1e-6]
    image = autolamella.data.adorned_image()
    my_lamella = autolamella.sample.Lamella()
    result = my_lamella.set_center(image, settings)
    assert my_lamella.center_coord_realspace == expected_lamella_center
    assert result == expected_lamella_center


@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_add_single_sample(microscope, settings, monkeypatch):
    expected_lamella_center = [1e-6, 1e-6]
    user_inputs = StringIO("y\nn\n\n")
    monkeypatch.setattr("sys.stdin", user_inputs)
    my_lamella = autolamella.add_samples.add_single_sample(microscope, settings)
    assert my_lamella.center_coord_realspace == expected_lamella_center


@pytest.mark.parametrize(
    "user_inputs, expected",
    [
        (StringIO("n"), 0),  # No, do not select a new location for milling
        (StringIO("y\ny\ny\nn\n\n" + "n\n"), 1),  # regular fiducial marker
        (StringIO("y\ny\ny\ny\n\n" + "n\n"), 1),  # re-mill fiducial marker
        (StringIO("y\ny\ny\ny\n150e-6\n" + "n\n"), 1),  # custom milling depth
        (StringIO("y\ny\ny\nn\n\n" + "y\ny\ny\nn\n\n" + "n\n"), 2),  # 2 samples
    ],
)
@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_add_samples(user_inputs, expected, microscope, settings, monkeypatch):
    monkeypatch.setattr("sys.stdin", user_inputs)
    lamella_list = autolamella.add_samples.add_samples(microscope, settings)
    assert len(lamella_list) == expected
    assert all(isinstance(i, autolamella.sample.Lamella) for i in lamella_list)


@pytest.mark.parametrize(
    "user_inputs, expected",
    [
        (StringIO("n"), 0),  # No, do not select a new location for milling
        (StringIO("y\ny\ny\nn\n\n" + "n\n"), 1),  # regular fiducial marker
        (StringIO("y\ny\ny\ny\n\n" + "n\n"), 1),  # re-mill fiducial marker
        (StringIO("y\ny\ny\ny\n150e-6\n" + "n\n"), 1),  # custom milling depth
        (StringIO("y\ny\ny\nn\n\n" + "y\ny\ny\nn\n\n" + "n\n"), 2),  # 2 samples
    ],
)
@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_set_lamella_center)
def test_add_samples_reduced_area(user_inputs, expected, microscope, reduced_area_settings, monkeypatch):
    monkeypatch.setattr("sys.stdin", user_inputs)
    lamella_list = autolamella.add_samples.add_samples(microscope, reduced_area_settings)
    assert len(lamella_list) == expected
    assert all(isinstance(i, autolamella.sample.Lamella) for i in lamella_list)


@pytest.mark.parametrize(
    "user_inputs",
    [
        (StringIO("y\ny\n" + "n\n")),
        (StringIO("y\ny\n" + "y\ny\n" + "n\n"))],
)
@patch("autolamella.fiducial.select_fiducial_point", new=mock_no_fiducial)
def test_cancel_fiducial(user_inputs, microscope, settings, monkeypatch):
    monkeypatch.setattr("sys.stdin", user_inputs)
    lamella_list = autolamella.add_samples.add_samples(microscope, settings)
    assert lamella_list == []


@pytest.mark.parametrize(
    "user_inputs",
    [
        (StringIO("y\ny\nn\n\n" + "n\n")),
        (StringIO("y\ny\nn\n\n" + "y\ny\nn\n\n" + "n\n")),
    ],
)
@patch("autolamella.fiducial.fiducial", new=mock_fiducial)
@patch("autolamella.sample.Lamella.set_center", new=mock_no_lamella_center)
def test_cancel_lamella(user_inputs, microscope, settings, monkeypatch):
    monkeypatch.setattr("sys.stdin", user_inputs)
    lamella_list = autolamella.add_samples.add_samples(microscope, settings)
    assert lamella_list == []
