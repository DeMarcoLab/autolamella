import os
import yaml

from tkinter import Tk, filedialog


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
        save_directory = filedialog.askdirectory()
    root.destroy()
    return save_directory


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
        settings = yaml.safe_load(f)
    settings = _format_dictionary(settings)
    return settings
