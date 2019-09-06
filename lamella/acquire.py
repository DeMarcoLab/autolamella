import logging

from autoscript_sdb_microscope_client.structures import (
    GrabFrameSettings,
    Rectangle,
    RunAutoCbSettings,
    RunAutoFocusSettings,
)


def _run_autofocus(microscope, reduced_area=Rectangle(0, 0, 1, 1)):
    """Run autofocus function."""
    focus_settings = RunAutoFocusSettings(
        method="Volumescope",
        resolution="1536x1024",
        reduced_area=reduced_area,
        number_of_frames=5,
        working_distance_step=1e-6,
    )
    logging.info("Automatically focusing...")
    microscope.auto_functions.run_auto_focus(focus_settings)
    return focus_settings


def _run_autocontrast(microscope):
    """Run autocontrast function."""
    autocontrast_settings = RunAutoCbSettings(
        method="MaxContrast",
        resolution="768x512",  # low resolution, so as not to damage the sample
        number_of_frames=5,
    )
    logging.info("Automatically adjusting conttrast...")
    microscope.auto_functions.run_auto_cb()
    return autocontrast_settings


def autocontrast_autofocus(
    microscope,
    autocontrast=False,
    autofocus=False,
    reduced_area_focus=Rectangle(0, 0, 1, 1),
):
    """Optionally run autocontrast and autofocus functions."""
    if autocontrast:
        _run_autocontrast(microscope)
    if autofocus:
        _run_autofocus(microscope, reduced_area_focus)


def create_camera_settings(imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)):
    camera_settings = GrabFrameSettings(
        resolution=imaging_settings["resolution"],
        dwell_time=imaging_settings["dwell_time"],
        reduced_area=reduced_area,
    )
    return camera_settings


def grab_ion_image(microscope, camera_settings):
    """Acquire a new ion beam image."""
    microscope.imaging.set_active_view(2)  # the ion beam view
    ion_image = microscope.imaging.grab_frame(camera_settings)
    return ion_image


def grab_sem_image(microscope, camera_settings):
    """Aquire a new SEM image."""
    microscope.imaging.set_active_view(1)  # the sem beam view
    sem_image = microscope.imaging.grab_frame(camera_settings)
    microscope.imaging.set_active_view(2)  # restore the ion beam view
    return sem_image
