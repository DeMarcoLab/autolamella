import pytest

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)


def test_initialize():
    """Test connecting to the microscope offline with localhost."""
    import lamella.autoscript

    microscope = lamella.autoscript.initialize("localhost")


@pytest.fixture
def microscope():
    from autoscript_sdb_microscope_client import SdbMicroscopeClient

    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
    return microscope


def test_reset_beam_shift(microscope):
    from autoscript_sdb_microscope_client.structures import Point
    import lamella.autoscript

    microscope.beams.ion_beam.beam_shift.value = Point(x=5e-6, y=-2e-6)
    microscope.beams.electron_beam.beam_shift.value = Point(x=5e-6, y=-2e-6)
    microscope = lamella.autoscript.reset_beam_shift(microscope)
    assert microscope.beams.ion_beam.beam_shift.value.x == 0
    assert microscope.beams.ion_beam.beam_shift.value.y == 0
    assert microscope.beams.electron_beam.beam_shift.value.x == 0
    assert microscope.beams.electron_beam.beam_shift.value.y == 0
