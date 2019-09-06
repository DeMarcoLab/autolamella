from dataclasses import dataclass
import PySimpleGUI as sg
import yaml

from autoscript_sdb_microscope_client import SdbMicroscopeClient

from lamella.user_input import Settings, load_config


def app(microscope, settings):
    title = "My GUI"
    layout = create_layout(settings, [])
    layout.append(
        [
            [sg.Text(title)],
            [
                sg.Text("save_directory", size=(15, 1)),
                sg.InputText(key="save_directory"),
                sg.FolderBrowse(),
            ],
            [sg.Submit(), sg.Cancel()],
        ]
    )
    window = sg.Window("Simple data entry window", layout)
    event, values = window.Read()
    window.Close()
    return event, values


def create_layout(obj, layout):
    for attr, value in obj.__dict__.items():
        if isinstance(value, type(obj)):
            print(attr)
            layout.append([sg.Text(str(attr))])
            create_layout(value, layout)
        else:
            print(attr, value)
            row = input_element(attr, value)
            layout.append(row)
    return layout


def input_element(name, value):
    size = (15, 1)
    _boolean_inputs = {
        "demo_mode": False,
        "acquire_many_images": False,
        "autofocus": False,
        "autocontrast": False,
        "save_sem_images": False,
    }
    if name in list(_boolean_inputs):
        input_element = sg.Checkbox(
            name, default=_boolean_inputs[name], size=size, key=name
        )
        return [input_element]
    elif "application_file" in name:
        _avail_application_files = microscope.patterning.list_all_application_files()
        input_element = sg.DropDown(_avail_application_files, size=size, key=name)
    elif "resolution" in name:
        _avail_resolutions = (
            microscope.beams.ion_beam.scanning.resolution.available_values
        )
        input_element = sg.DropDown(_avail_resolutions, size=size, key=name)
    elif "current" in name:
        _avail_milling_currents = (
            microscope.beams.ion_beam.beam_current.available_values
        )
        input_element = sg.DropDown(_avail_milling_currents, size=size, key=name)
    else:
        input_element = sg.InputText(value, size=size, key=name)
    row = [sg.Text(name, size=size), input_element]
    return row


if __name__ == "__main__":
    filename = "protocol.yml"
    settings_dict = load_config(filename)
    settings = Settings(**settings_dict)
    microscope = SdbMicroscopeClient()
    microscope.connect(settings.system.ip_address)
    event, values = app(microscope, settings)
    print(event, values)
