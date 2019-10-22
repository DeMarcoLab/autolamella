import logging
import os

from autoscript_sdb_microscope_client.structures import (
    GrabFrameSettings,
    Rectangle,
    RunAutoCbSettings,
)

__all__ = [
    "autocontrast",
    "create_camera_settings",
    "grab_ion_image",
    "grab_sem_image",
    "grab_images",
]


def autocontrast(microscope):
    """Atuomatically adjust the microscope image contrast.

    Parameters
    ----------
    microscope : Autoscript microscope object.

    Returns
    -------
    RunAutoCbSettings
        Automatic contrast brightness settings.
    """
    autocontrast_settings = RunAutoCbSettings(
        method="MaxContrast",
        resolution="768x512",  # low resolution, so as not to damage the sample
        number_of_frames=5,
    )
    logging.info("Automatically adjusting contrast...")
    microscope.auto_functions.run_auto_cb()
    return autocontrast_settings


def create_camera_settings(imaging_settings, reduced_area=Rectangle(0, 0, 1, 1)):
    """Camera settings for acquiring images on the microscope.

    Parameters
    ----------
    imaging_settings : dictionary
        User input as dictionary containing keys "resolution" and "dwell_time".
    reduced_area : Rectangle, optional
        Reduced area view for image acquisition.
        By default Rectangle(0, 0, 1, 1), which means the whole field of view.

    Returns
    -------
    GrabFrameSettings
        Camera acquisition settings
    """
    camera_settings = GrabFrameSettings(
        resolution=imaging_settings["resolution"],
        dwell_time=imaging_settings["dwell_time"],
        reduced_area=reduced_area,
    )
    return camera_settings


def grab_ion_image(microscope, camera_settings):
    """Acquire a new ion beam image.

    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.

    Returns
    -------
    AdornedImage
        Image from ion beam camera acquisition.
    """
    microscope.imaging.set_active_view(2)  # the ion beam view
    ion_image = microscope.imaging.grab_frame(camera_settings)
    return ion_image


def grab_sem_image(microscope, camera_settings):
    """Aquire a new SEM image.

    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.

    Returns
    -------
    AdornedImage
        Image from SEM camera acquisition.
    """
    microscope.imaging.set_active_view(1)  # the sem beam view
    sem_image = microscope.imaging.grab_frame(camera_settings)
    microscope.imaging.set_active_view(2)  # restore the ion beam view
    return sem_image


def grab_images(microscope, settings, my_lamella, prefix="", suffix=""):
    """Aquire and save images, with optional autocontrast."""
    # Reduced area images (must reset camera settings each time, because different samples have different reduced areas)
    camera_settings = GrabFrameSettings(
        reduced_area=my_lamella.fiducial_reduced_area,
        resolution=settings["fiducial"]["reduced_area_resolution"],
        dwell_time=settings["imaging"]["dwell_time"],
    )
    fullfield_cam_settings = GrabFrameSettings(
        reduced_area=Rectangle(0, 0, 1, 1),
        resolution=settings["fiducial"]["reduced_area_resolution"],
        dwell_time=settings["imaging"]["dwell_time"],
    )
    # Optional autocontrast
    if settings["imaging"]["autocontrast"]:
        microscope.imaging.set_active_view(2)  # the ion beam view
        autocontrast(microscope)
    # Take images before alignment
    acquire_many_images = settings["imaging"]["full_field_ib_images"]
    output_dir = settings["save_directory"]
    if acquire_many_images:
        fullfield_image = grab_ion_image(microscope, fullfield_cam_settings)
        fname_fullfield = prefix + "_FullField_" + suffix + ".tif"
        filename_fullfield = os.path.join(output_dir, fname_fullfield)
        fullfield_image.save(filename_fullfield)
    image = grab_ion_image(microscope, camera_settings)
    filename = os.path.join(output_dir, prefix + "_" + suffix + ".tif")
    image.save(filename)
    return image
