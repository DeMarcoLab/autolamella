"""Module for validating user input values."""
import numpy as np


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
    # TODO
    # ion_beam_currents = [
    #     settings["fiducial"]["fiducial_milling_current"],
    #     settings["lamella"]["milling_current"],
    # ]
    # _validate_ion_beam_currents(microscope, ion_beam_currents)


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
        if not app_file in available_files:
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
                "Dwell time must be a number!\n".format(dwell)
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
        if not beam_current in available_ion_beam_currents:
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
        if not resolution in available_resolutions:
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
    allowed_values = [np.deg2rad(0.0), np.deg2rad(180.0)]
    matching_criterion = any([np.isclose(rotation, i) for i in allowed_values])
    if not matching_criterion:
        raise ValueError(
            "Ion beam scanning rotation must be either 0 or 180 degrees!"
            "\nPlease change your system settings and try again."
            "\nCurrent rotation value is {}".format(rotation)
        )
