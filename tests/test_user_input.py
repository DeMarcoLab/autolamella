from io import StringIO
import os

import pytest

import lamella.user_input


@pytest.mark.parametrize("test_input, default, expected", [
    (StringIO('\n'), 'yes', True),
    (StringIO('\n'), 'no', False),
    (StringIO('y\n'), None, True),
    (StringIO('Y\n'), None, True),
    (StringIO('yes\n'), None, True),
    (StringIO('Yes\n'), None, True),
    (StringIO('YES\n'), None, True),
    (StringIO('n\n'), None, False),
    (StringIO('N\n'), None, False),
    (StringIO('no\n'), None, False),
    (StringIO('No\n'), None, False),
    (StringIO('NO\n'), None, False),
])
def test_ask_user(monkeypatch, test_input, default, expected):
    monkeypatch.setattr('sys.stdin', test_input)
    result = lamella.user_input.ask_user('message', default=default)
    assert result == expected


@pytest.fixture
def expected_user_input():
    user_input_dictionary = {
        'fiducial_properties':
            {
                'fiducial_length': 0.1,
                'fiducial_width': 0.02
            },
        'lamella_properties':
            {
                'lamella_width': 5e-06,
                'lamella_height': 1e-06,
                'tilt_degrees': 0.0,
                'autofocus': 1.0,
                'save_sem_images': 1.0,
                'protocol_stages': [
                    {
                        'percentage_roi_height': 0.5,
                        'percentage_from_lamella_surface': 0.5,
                        'milling_current': 3e-10,
                        'milling_depth': 5e-07
                    },
                    {
                        'percentage_roi_height': 0.3,
                        'percentage_from_lamella_surface': 0.2,
                        'milling_current': 3e-10
                    },
                    {
                        'percentage_roi_height': 0.2,
                        'percentage_from_lamella_surface': 0.0,
                        'milling_current': 3e-10,
                        'tilt_degrees': 2.0
                    }
                ]
            }
    }
    return user_input_dictionary


def test__format_dictionary():
    input_dictionary = {'value_1': '1e6', 'value_2': '2e-6', 'value_3': True}
    expected_output = {'value_1': 1000000.0, 'value_2': 2e-06, 'value_3': 1.0}
    result = lamella.user_input._format_dictionary(input_dictionary)
    assert result == expected_output


def test_load_config(expected_user_input):
    yaml_filename = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'test_user_input.yml')
    result = lamella.user_input.load_config(yaml_filename)
    assert result == expected_user_input
