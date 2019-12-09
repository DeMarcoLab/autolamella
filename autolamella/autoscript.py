def initialize(ip_address="localhost"):
    """Initialize autoscript for the FIBSEM microscope.

    Parameters
    ----------
    ip_address : str, optional
        The ip address of the microscope, by default 'localhost'.
        Use 'localhost' to connect to Autoscript offline.

    Returns
    -------
    Autoscript microscope instance
    """
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect(ip_address)
    microscope = reset_beam_shift(microscope)
    microscope.imaging.set_active_view(2)  # the ion beam view
    return microscope


def reset_beam_shift(microscope):
    """Set the beam shift to zero for the electron and ion beams.

    Parameters
    ----------
    microscope : Autoscript microscope object.

    Returns
    -------
    Autoscript microscope object.
    """
    from autoscript_sdb_microscope_client.structures import Point

    microscope.beams.electron_beam.beam_shift.value = Point(x=0, y=0)
    microscope.beams.ion_beam.beam_shift.value = Point(x=0, y=0)
    return microscope


def reset_state(microscope, settings, application_file=None):
    """Reset the microscope state.

    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.
    application_file : str, optional
        Name of the application file for milling, by default None

    Returns
    -------
    Autoscript microscope object.
    """
    microscope.patterning.clear_patterns()
    if application_file:  # optionally specified
        microscope.patterning.set_default_application_file(application_file)
    reset_beam_shift(microscope)
    resolution = settings["imaging"]["resolution"]
    dwell_time = settings["imaging"]["dwell_time"]
    hfw = settings["imaging"]["horizontal_field_width"]
    microscope.beams.ion_beam.scanning.resolution.value = resolution
    microscope.beams.ion_beam.scanning.dwell_time.value = dwell_time
    microscope.beams.ion_beam.horizontal_field_width.value = hfw
    microscope.imaging.set_active_view(2)  # the ion beam view
    return microscope


class BeamSettings:
    def __init__(self, microscope, beam_type):
        if "ELECTRON_BEAM" == beam_type.upper():
            self.beam = microscope.beams.electron_beam
        elif "ION_BEAM" == beam_type.upper():
            self.beam = microscope.beams.ion_beam
        else:
            raise ValueError(
                "beam_type argument must be either" '"ELECTRON_BEAM" or "ION_BEAM".'
            )
        # Save all the important beam settings
        self.beam_shift = self.beam.beam_shift.value
        self.horizontal_field_width = self.beam.horizontal_field_width.value  # mag
        self.scan_resolution = self.beam.scanning.resolution.value
        self.scan_rotation = self.beam.scanning.rotation.value
        self.dwell_time = self.beam.scanning.dwell_time.value
        self.stigmator = self.beam.stigmator.value
        self.working_distance = self.beam.working_distance.value  # sets the focus

    def restore_state(self, microscope):
        """Restore all the important beam settings.

        Parameters
        ----------
        microscope : Autoscript microscope object.
        """
        self.beam.beam_shift.value = self.beam_shift
        self.beam.horizontal_field_width.value = self.horizontal_field_width
        self.beam.scanning.resolution.value = self.scan_resolution
        self.beam.scanning.rotation.value = self.scan_rotation
        self.beam.scanning.dwell_time.value = self.dwell_time
        self.beam.stigmator.value = self.stigmator
        self.beam.working_distance.value = self.working_distance


class FibsemPosition:
    def __init__(self, microscope):
        self.stage_position = microscope.specimen.stage.current_position
        # self.electron_beam = BeamSettings(microscope, 'ELECTRON_BEAM')
        self.ion_beam = BeamSettings(microscope, "ION_BEAM")

    def restore_state(self, microscope):
        microscope.specimen.stage.absolute_move(self.stage_position)
        # self.electron_beam.restore_state(microscope)
        self.ion_beam.restore_state(microscope)
