import os

import pytest

import autolamella.user_input


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


def test__format_dictionary():
    input_dictionary = {"value_1": "1e6", "value_2": "2e-6", "value_3": True}
    expected_output = {"value_1": 1000000.0, "value_2": 2e-06, "value_3": 1.0}
    result = autolamella.user_input._format_dictionary(input_dictionary)
    assert result == expected_output


def test_load_config(expected_user_input):
    yaml_filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "test_user_input.yml"
    )
    result = autolamella.user_input.load_config(yaml_filename)
    assert result == expected_user_input
