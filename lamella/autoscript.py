from autoscript_sdb_microscope_client import SdbMicroscopeClient
from autoscript_sdb_microscope_client.structures import Point


def initialize(ip_address='localhost'):
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
    microscope = SdbMicroscopeClient()
    microscope.connect(ip_address)
    microscope = reset_beam_shift(microscope)
    microscope.imaging.set_active_view(2)  # the ion beam view
    return microscope


def reset_beam_shift(microscope):
    microscope.beams.electron_beam.beam_shift.value = Point(x=0, y=0)
    microscope.beams.ion_beam.beam_shift.value = Point(x=0, y=0)
    return microscope


class BeamSettings():
    def __init__(self, microscope, beam_type):
        if 'ELECTRON_BEAM' == beam_type.upper():
            self.beam = microscope.beams.electron_beam
        elif 'ION_BEAM' == beam_type.upper():
            self.beam = microscope.beams.ion_beam
        else:
            raise ValueError('beam_type argument must be either'
                             '"ELECTRON_BEAM" or "ION_BEAM".')
        # Save all the important beam settings
        self.beam_shift = self.beam.beam_shift.value
        self.horizontal_field_width = self.beam.horizontal_field_width.value  # mag
        self.scan_resolution = self.beam.scanning.resolution.value
        self.scan_rotation = self.beam.scanning.rotation.value
        self.dwell_time = self.beam.scanning.dwell_time.value
        self.stigmator = self.beam.stigmator.value
        self.working_distance = self.beam.working_distance.value  # sets the focus

    def restore_state(self, microscope):
        # Restore all the important beam settings
        self.beam.beam_shift.value = self.beam_shift
        self.beam.horizontal_field_width.value = self.horizontal_field_width
        self.beam.scanning.resolution.value = self.scan_resolution
        self.beam.scanning.rotation.value = self.scan_rotation
        self.beam.scanning.dwell_time.value = self.dwell_time
        self.beam.stigmator.value = self.stigmator
        self.beam.working_distance.value = self.working_distance


class FibsemPosition():
    def __init__(self, microscope):
        self.stage_position = microscope.specimen.stage.current_position
        # self.electron_beam = BeamSettings(microscope, 'ELECTRON_BEAM')
        self.ion_beam = BeamSettings(microscope, 'ION_BEAM')

    def restore_state(self, microscope):
        microscope.specimen.stage.absolute_move(self.stage_position)
        # self.electron_beam.restore_state(microscope)
        self.ion_beam.restore_state(microscope)
