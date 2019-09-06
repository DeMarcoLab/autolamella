from dataclasses import dataclass
import numpy as np
import yaml


def _add_missing_keys(dictionary):
    try:
        dictionary["lamella"]["overtilt_degrees"]
    except KeyError:
        dictionary["lamella"]["overtilt_degrees"] = 0
    try:
        dictionary["demo_mode"]
    except KeyError:
        dictionary["demo_mode"] = False
    return dictionary


def _format_dictionary(dictionary):
    """Recursively traverse dictionary and covert all numeric values to flaot.

    Parameters
    ----------
    dictionary : dict
        Any arbitrarily structured python dictionary.

    Returns
    -------
    dictionary
        The input dictionary, with all numeric values converted to float type.
    """
    for key, item in dictionary.items():
        if isinstance(item, dict):
            _format_dictionary(item)
        elif isinstance(item, list):
            dictionary[key] = [_format_dictionary(i) for i in item]
        else:
            if item is not None:
                try:
                    dictionary[key] = float(dictionary[key])
                except ValueError:
                    pass
    return dictionary


def load_config(yaml_filename):
    """Load user input from yaml settings file.

    Parameters
    ----------
    yaml_filename : str
        Filename path of user configuration file.

    Returns
    -------
    dict
        Dictionary containing user input settings.
    """
    with open(yaml_filename, "r") as f:
        settings_dict = yaml.safe_load(f)
    settings_dict = _add_missing_keys(settings_dict)
    settings_dict = _format_dictionary(settings_dict)
    # settings = Settings(**settings_dict)  # convert to python dataclass
    return settings_dict


def protocol_stage_settings(settings):
    """Load settings for each milling stage, overwriting default values."""
    protocol_stages = []
    for stage_settings in settings["lamella"]["protocol_stages"]:
        tmp_settings = settings["lamella"].copy()
        tmp_settings.update(stage_settings)
        # Autoscript actually expects tilt in radians
        tmp_settings["overtilt_degrees"] = np.deg2rad(tmp_settings["overtilt_degrees"])
        protocol_stages.append(tmp_settings)
    return protocol_stages


# @dataclass(frozen = True)  # can make instance values immutable
@dataclass
class Settings:
    """Convert nested dictionray to python dataclass."""

    def __init__(self, **response):
        for k, v in response.items():
            if isinstance(v, dict):
                self.__dict__[k] = Settings(**v)
            else:
                self.__dict__[k]: type(v) = v


def dict_from_class(cls):
    """Conversion from python class to nested dictionary."""
    my_dict = {}
    for (key, value) in cls.__dict__.items():
        try:
            value.__dict__
        except AttributeError:
            my_dict[key] = value
        else:
            my_dict[key] = dict_from_class(value)
    return my_dict
