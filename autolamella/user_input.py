import os

import numpy as np
from tkinter import Tk, filedialog
import yaml


def ask_user(message, default=None):
    """Ask the user a question and return True if they say yes.

    Parameters
    ----------
    message : str
        The question to ask the user.
    default : str, optional
        If the user presses Enter without typing an answer,
        the default indicates how to interpret this.
        Choices are 'yes' or 'no'. The efault is None.

    Returns
    -------
    bool
        Returns True if the user answers yes, and false if they answer no.
    """
    yes = ["yes", "y"]
    no = ["no", "n"]
    if default:
        if default.lower() == "yes":
            yes.append("")
        elif default.lower() == "no":
            no.append("")
    all_posiible_responses = yes + no
    user_response = "initial non-empty string"
    while user_response not in all_posiible_responses:
        user_response = input(message)
        if user_response.lower() in yes:
            return True
        elif user_response.lower() in no:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def choose_directory():
    """Ask the user to create or select an EMPTY directory with Tkinter.

    Returns
    -------
    str
        Path to directory for output files.
    """
    print("Create a new EMPTY directory to store your output images.")
    root = Tk()
    save_directory = filedialog.askdirectory()
    while os.listdir(save_directory):  # while loop breaks for empty directory
        contents = [i for i in os.listdir(save_directory) if not i.endswith(".log")]
        if contents == []:
            break  # if there is nothing in the directory EXCEPT for a log file
        save_directory = filedialog.askdirectory()
    root.destroy()
    return save_directory


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
        protocol_stages.append(tmp_settings)
    return protocol_stages


def validate_user_input(microscope, settings):
    application_files = [
        settings["system"]["application_file_rectangle"],
        settings["system"]["application_file_cleaning_cross_section"],
    ]
    _validate_application_files(microscope, application_files)
    scanning_resolutions = [
        settings["imaging"]["resolution"],
        settings["fiducial"]["reduced_area_resolution"],
    ]
    _validate_scanning_rotation(microscope)
    dwell_times = [settings["imaging"]["dwell_time"]]
    _validate_dwell_time(microscope, dwell_times)
    _validate_scanning_resolutions(microscope, scanning_resolutions)


def _add_missing_keys(dictionary):
    """If the user leaves these keys blank, add them with these default values.

    Parameters
    ----------
    dictionary : Dictionary of user input argument settings.

    Returns
    -------
    dictionary
        Python dictionray of user input settings.
    """
    dictionary["lamella"]["overtilt_degrees"] = dictionary["lamella"].get(
        "overtilt_degrees", 0
    )
    dictionary["demo_mode"] = dictionary.get("demo_mode", False)
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


def _validate_application_files(microscope, application_files):
    """Check that the user supplied application files exist on this system.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    application_files : list
        List of application files, eg: ['Si', 'Si_small']

    Raises
    ------
    ValueError
        Application file name not found in list of available application files.
    """
    available_files = microscope.patterning.list_all_application_files()
    for app_file in application_files:
        if app_file not in available_files:
            raise ValueError(
                "{} not found ".format(app_file)
                + "in list of available application files!\n"
                "Please choose one from the list: \n"
                "{}".format(available_files)
            )


def _validate_dwell_time(microscope, dwell_times):
    """Check that the user specified dwell times are within the limits.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    dwell_times : list
        List of dwell times, eg: [1e-7, 1e-6]

    Raises
    ------
    ValueError
        Dwell time is smaller than the minimum limit.
    ValueError
        Dwell time is larger than the maximum limit.
    """
    dwell_limits = microscope.beams.ion_beam.scanning.dwell_time.limits
    for dwell in dwell_times:
        if not isinstance(dwell, (int, float)):
            raise ValueError(
                "Dwell time {} must be a number!\n".format(dwell)
                + "Please choose a value between the limits: \n"
                "{}".format(dwell_limits)
            )
        if dwell < dwell_limits.min:
            raise ValueError(
                "{} dwell time is too small!\n".format(dwell)
                + "Please choose a value between the limits: \n"
                "{}".format(dwell_limits)
            )
        elif dwell > dwell_limits.max:
            raise ValueError(
                "{} dwell time is too large!\n".format(dwell)
                + "Please choose a value between the limits: \n"
                "{}".format(dwell_limits)
            )
        else:
            if dwell is np.nan:
                raise ValueError(
                    "{} dwell time ".format(dwell) + "is not a number!\n"
                    "Please choose a value between the limits:\n"
                    "{}".format(dwell_limits)
                )


def _validate_ion_beam_currents(microscope, ion_beam_currents):
    """Check that the user supplied ion beam current values are valid.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    ion_beam_currents : list
        List of ion beam currents, eg: [ 3e-10, 1e-09]

    Raises
    ------
    ValueError
        Beam current not found in list of available ion beam currents.
    """
    available_ion_beam_currents = (
        microscope.beams.ion_beam.beam_current.available_values
    )
    for beam_current in ion_beam_currents:
        if beam_current not in available_ion_beam_currents:
            raise ValueError(
                "{} not found ".format(beam_current)
                + "in list of available ion beam currents!\n"
                "Please choose one from the list: \n"
                "{}".format(available_ion_beam_currents)
            )


def _validate_horizontal_field_width(microscope, horizontal_field_widths):
    """Check that the ion beam horizontal field width is within the limits.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    horizontal_field_widths : list
        List of ion beam horizontal field widths, eg: [50e-6, 100e-6]

    Raises
    ------
    ValueError
        Ion beam horizontal field width is smaller than the minimum limit.
    ValueError
        Ion beam horizontal field width is larger than the maximum limit.
    """
    hfw_limits = microscope.beams.ion_beam.horizontal_field_width.limits
    for hfw in horizontal_field_widths:
        if not isinstance(hfw, (int, float)):
            raise ValueError(
                "Horizontal field width must be a number!\n"
                "Please choose a value between the limits: \n"
                "{}".format(hfw_limits)
            )
        if hfw < hfw_limits.min:
            raise ValueError(
                "{} ".format(hfw) + "horizontal field width is too small!\n"
                "Please choose a value between the limits: \n"
                "{}".format(hfw_limits)
            )
        elif hfw > hfw_limits.max:
            raise ValueError(
                "{} ".format(hfw) + "horizontal field width is too large!\n"
                "Please choose a value between the limits: \n"
                "{}".format(hfw_limits)
            )
        else:
            if hfw is np.nan:
                raise ValueError(
                    "{} dwell time ".format(hfw) + "is not a number!\n"
                    "Please choose a value between the limits: \n"
                    "{}".format(hfw_limits)
                )


def _validate_scanning_resolutions(microscope, scanning_resolutions):
    """Check that the user supplied scanning resolution values are valid.

    Parameters
    ----------
    microscope : Connected Autoscrpt microscope instance.
    scanning_resolutions : list
        List of scanning resolutions, eg: ['1536x1024', '3072x2048']

    Raises
    ------
    ValueError
        Resolution not found in list of available scanning resolutions.
    """
    available_resolutions = (
        microscope.beams.ion_beam.scanning.resolution.available_values
    )
    microscope.beams.ion_beam.beam_current.available_values
    for resolution in scanning_resolutions:
        if resolution not in available_resolutions:
            raise ValueError(
                "{} not found ".format(resolution)
                + "in list of available scanning resolutions!\n"
                "Please choose one from the list: \n"
                "{}".format(available_resolutions)
            )


def _validate_scanning_rotation(microscope):
    rotation = microscope.beams.ion_beam.scanning.rotation.value
    if rotation is None:
        microscope.beams.ion_beam.scanning.rotation.value = 0
        rotation = microscope.beams.ion_beam.scanning.rotation.value
    if not np.isclose(rotation, 0.0):
        raise ValueError(
            "Ion beam scanning rotation must be 0 degrees."
            "\nPlease change your system settings and try again."
            "\nCurrent rotation value is {}".format(rotation)
        )
