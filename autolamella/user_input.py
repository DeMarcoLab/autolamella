import numpy as np
import yaml


def _add_missing_keys(dictionary):
    """If the user leaves these keys blank, add them with these default values.

    Parameters
    ----------
    dictionary : Dictionary of user input argument settings.

    Returns
    -------
    dictionary
        [description]
    """
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
    """"Load settings for each milling stage, overwriting default values.

    Parameters
    ----------
    settings :  Dictionary of user input argument settings.

    Returns
    -------
    protocol_stages
        List containing a dictionary of settings for each protocol stage.
    """
    protocol_stages = []
    for stage_settings in settings["lamella"]["protocol_stages"]:
        tmp_settings = settings["lamella"].copy()
        tmp_settings.update(stage_settings)
        # Autoscript actually expects tilt in radians
        radians_tilt = np.deg2rad(tmp_settings["overtilt_degrees"])
        tmp_settings["overtilt_degrees"] = radians_tilt
        protocol_stages.append(tmp_settings)
    return protocol_stages
