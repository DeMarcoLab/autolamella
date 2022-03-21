import pytest


@pytest.mark.dependency()
def test_initialize():
    """Test connecting to the microscope offline with localhost."""
    import autolamella.autoscript

    microscope = autolamella.autoscript.initialize("localhost")  # noqa: F841


@pytest.mark.dependency(depends=["test_initialize"])
def test_reset_beam_shift(microscope):
    from autoscript_sdb_microscope_client.structures import Point
    import autolamella.autoscript

    microscope.beams.ion_beam.beam_shift.value = Point(x=5e-6, y=-2e-6)
    microscope.beams.electron_beam.beam_shift.value = Point(x=5e-6, y=-2e-6)
    microscope = autolamella.autoscript.reset_beam_shift(microscope)
    assert microscope.beams.ion_beam.beam_shift.value.x == 0
    assert microscope.beams.ion_beam.beam_shift.value.y == 0
    assert microscope.beams.electron_beam.beam_shift.value.x == 0
    assert microscope.beams.electron_beam.beam_shift.value.y == 0
