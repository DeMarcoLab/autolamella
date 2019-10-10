from autoscript_sdb_microscope_client.structures import GrabFrameSettings, Rectangle

from autolamella.acquire import grab_ion_image
import autolamella.autoscript
from autolamella.interactive import ask_user
from autolamella.sample import Lamella


def add_single_sample(microscope, settings):
    """Create a single lamella object.

    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.

    Returns
    -------
    my_lamella
        A single Lamella() object.
    """
    demo_mode = settings["demo_mode"]
    acquire_many_images = settings["imaging"]["full_field_ib_images"]
    # Reset microscope state
    autolamella.autoscript.reset_state(microscope, settings)
    microscope.beams.ion_beam.beam_current.value = settings["lamella"][
        "milling_current"
    ]
    # Optional autocontrast
    if settings["imaging"]["autocontrast"]:
        autolamella.acquire.autocontrast(microscope)
    # Take full field image
    full_field_camera_settings = autolamella.acquire.create_camera_settings(
        settings["imaging"], reduced_area=Rectangle(0, 0, 1, 1)
    )
    original_image = grab_ion_image(microscope, full_field_camera_settings)
    # Select fiducial posiion
    print("Please select where to put a fiducial marker.")
    my_fiducial = autolamella.fiducial.fiducial(
        microscope,
        original_image,
        settings["fiducial"]["fiducial_length"],
        settings["fiducial"]["fiducial_width"],
        settings["fiducial"]["fiducial_milling_depth"],
    )
    if my_fiducial is None:
        print("No fiducial location selected, cancelling.")
        microscope.patterning.clear_patterns()
        return
    #
    fiducial_coord_realspace, fiducial_coord_relative, fiducial_coord_pixels = (
        my_fiducial
    )
    pixelsize_x = original_image.metadata.binary_result.pixel_size.x
    fiducial_image_relative_size = [
        settings["fiducial"]["fiducial_image_size_x"]
        / (original_image.width * pixelsize_x),
        settings["fiducial"]["fiducial_image_size_y"]
        / (original_image.height * pixelsize_x),
    ]
    reduced_area_fiducial = autolamella.fiducial.fiducial_reduced_area_rect(
        fiducial_coord_relative, fiducial_image_relative_size
    )
    camera_settings = autolamella.acquire.create_camera_settings(
        settings["imaging"], reduced_area=reduced_area_fiducial
    )
    cropped_original_image = grab_ion_image(microscope, camera_settings)
    my_lamella = Lamella(microscope)
    my_lamella.fiducial_image_relative_size = fiducial_image_relative_size
    my_fiducial = my_lamella.set_fiducial(
        cropped_original_image,
        fiducial_coord_realspace,
        fiducial_coord_relative,
        fiducial_coord_pixels,
        reduced_area_fiducial,
    )
    # Select the lamella position
    print("Please select the center point of your lamella.")
    my_lamella.original_image = original_image
    lamella_center = my_lamella.set_center(original_image, settings)
    if lamella_center == []:
        print("No lamella position selected, cancelling.")
        microscope.patterning.clear_patterns()
        return
    # Ask user for decision
    message = "Do you want to mill a fiducial marker here? [y]/n\n"
    if ask_user(message, default="yes") == True:
        print("Milling fiducial marker...")
        if not demo_mode:
            microscope.beams.ion_beam.beam_current.value = settings["fiducial"][
                "fiducial_milling_current"
            ]
            microscope.patterning.run()
        if acquire_many_images:
            full_field_camera_settings = GrabFrameSettings(
                reduced_area=Rectangle(0, 0, 1, 1),
                resolution=settings["imaging"]["resolution"],
                dwell_time=settings["imaging"]["dwell_time"],
            )
            microscope.auto_functions.run_auto_cb()
            reference_image = grab_ion_image(microscope, full_field_camera_settings)
        camera_settings = GrabFrameSettings(
            reduced_area=reduced_area_fiducial,
            resolution=settings["fiducial"]["reduced_area_resolution"],
            dwell_time=settings["imaging"]["dwell_time"],
        )
        cropped_reference_image = grab_ion_image(microscope, camera_settings)
        message = "Do you want to re-mill the fiducial marker? y/[n]\n"
        if ask_user(message, default="no") == True:
            print("Milling fiducial marker again...")
            if not demo_mode:
                microscope.patterning.run()
        reference_image = grab_ion_image(microscope, camera_settings)
        microscope.patterning.clear_patterns()
    else:
        print("Ok, deleting those milling patterns.")
        return  # returns None, which gets stripped from sample list later
        microscope.patterning.clear_patterns()
    # Continue on
    camera_settings = GrabFrameSettings(
        reduced_area=reduced_area_fiducial,
        resolution=settings["fiducial"]["reduced_area_resolution"],
        dwell_time=settings["imaging"]["dwell_time"],
    )
    cropped_reference_image = grab_ion_image(microscope, camera_settings)
    my_lamella.set_fiducial(
        cropped_reference_image,
        fiducial_coord_realspace,
        fiducial_coord_relative,
        fiducial_coord_pixels,
        reduced_area_fiducial,
    )
    my_lamella.reference_image = reference_image
    my_lamella.set_sem_image(microscope, settings)
    my_lamella.set_custom_milling_depth()
    return my_lamella


def add_samples(microscope, settings):
    """Interactive function to add samples to list.

    Parameters
    ----------
    microscope : Autoscript microscope object.
    settings :  Dictionary of user input argument settings.

    Returns
    -------
    samples
        List of FIB-SEM sample objects.
    """
    default_response_yes = ["", "yes", "y"]
    response_no = ["no", "n"]

    samples = []
    user_response = ""
    while user_response.lower() not in response_no:
        message = (
            " \n FIRST MOVE TO THE DESIRED POSITION \n "
            "Do you want to select a new location for milling? [y]/n\n"
        )
        user_response = input(message)
        if user_response.lower() in default_response_yes:
            my_sample = add_single_sample(microscope, settings)
            samples.append(my_sample)
    samples = [s for s in samples if s is not None]
    return samples
