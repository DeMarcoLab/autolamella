import os
import logging

import numpy as np

from autoscript_core.common import ApplicationServerException
from autoscript_sdb_microscope_client.structures import (
    GrabFrameSettings,
    Rectangle,
    RunAutoCbSettings,
    Point,
    StagePosition,
)

from autolamella.acquire import (
    autocontrast,
    create_camera_settings,
    grab_ion_image,
    grab_sem_image,
)
from autolamella.autoscript import reset_state
from autolamella.align import calculate_beam_shift


def upper_milling(
    microscope,
    settings,
    stage_settings,
    my_lamella,
    filename_prefix="",
    demo_mode=False,
):
    # Setup and realign to fiducial marker
    setup_milling(microscope, settings, stage_settings, my_lamella)
    tilt_in_radians = np.deg2rad(stage_settings["overtilt_degrees"])
    microscope.specimen.stage.relative_move(StagePosition(t=-tilt_in_radians))
    image_unaligned = grab_images(
        microscope,
        settings,
        my_lamella,
        prefix="IB_" + filename_prefix,
        suffix="_0-unaligned",
    )
    realign_fiducial(microscope, settings, image_unaligned, my_lamella)
    grab_images(
        microscope,
        settings,
        my_lamella,  # can remove
        prefix="IB_" + filename_prefix,
        suffix="_1-aligned",
    )
    # Create and mill patterns
    _upper_milling_coords(microscope, stage_settings, my_lamella)
    if not demo_mode:
        print("Milling pattern...")
        microscope.patterning.run()
    microscope.patterning.clear_patterns()
    grab_images(
        microscope,
        settings,
        my_lamella,  # can remove
        prefix="IB_" + filename_prefix,
        suffix="_2-after-upper-milling",
    )
    return microscope


def lower_milling(
    microscope,
    settings,
    stage_settings,
    my_lamella,
    filename_prefix="",
    demo_mode=False,
):
    # Setup and realign to fiducial marker
    setup_milling(microscope, settings, stage_settings, my_lamella)
    tilt_in_radians = np.deg2rad(stage_settings["overtilt_degrees"])
    microscope.specimen.stage.relative_move(StagePosition(t=+tilt_in_radians))
    image_unaligned = grab_images(
        microscope,
        settings,
        my_lamella,
        prefix="IB_" + filename_prefix,
        suffix="_3-unaligned",
    )
    realign_fiducial(microscope, settings, image_unaligned, my_lamella)
    grab_images(
        microscope,
        settings,
        my_lamella,  # can remove
        prefix="IB_" + filename_prefix,
        suffix="_4-aligned",
    )
    # Create and mill patterns
    _lower_milling_coords(microscope, stage_settings, my_lamella)
    if not demo_mode:
        print("Milling pattern...")
        microscope.patterning.run()
    microscope.patterning.clear_patterns()
    grab_images(
        microscope,
        settings,
        my_lamella,  # TODO can remove
        prefix="IB_" + filename_prefix,
        suffix="_5-after-lower-milling",
    )
    return microscope


def _upper_milling_coords(microscope, stage_settings, my_lamella):
    """Create cleaning cross section milling pattern above lamella position."""
    microscope.imaging.set_active_view(2)  # the ion beam view
    lamella_center_x, lamella_center_y = my_lamella.center_coord_realspace
    if my_lamella.custom_milling_depth is not None:
        milling_depth = my_lamella.custom_milling_depth
    else:
        milling_depth = stage_settings["milling_depth"]
    center_y = (
        lamella_center_y
        + (0.5 * stage_settings["lamella_height"])
        + (
            stage_settings["total_cut_height"]
            * stage_settings["percentage_from_lamella_surface"]
        )
        + (
            0.5
            * stage_settings["total_cut_height"]
            * stage_settings["percentage_roi_height"]
        )
    )
    height = float(
        stage_settings["total_cut_height"] * stage_settings["percentage_roi_height"]
    )
    if stage_settings["overtilt_degrees"] > 0:
        scaling_factor = np.cos(np.deg2rad(stage_settings["overtilt_degrees"]))
        height = scaling_factor * height  # shrink ROI height
        fiducial_y = my_lamella.fiducial_coord_realspace[1]
        hypotenuse = abs(center_y - fiducial_y)
        adjacent = hypotenuse * scaling_factor
        y_tilt_adjustment = hypotenuse - adjacent
        center_y = center_y - y_tilt_adjustment  # moving closer to lamella
    milling_roi = microscope.patterning.create_cleaning_cross_section(
        lamella_center_x,
        center_y,
        stage_settings["lamella_width"],
        height,
        milling_depth,
    )
    milling_roi.scan_direction = "TopToBottom"
    return milling_roi


def _lower_milling_coords(microscope, stage_settings, my_lamella):
    """Create cleaning cross section milling pattern below lamella position."""
    microscope.imaging.set_active_view(2)  # the ion beam view
    lamella_center_x, lamella_center_y = my_lamella.center_coord_realspace
    if my_lamella.custom_milling_depth is not None:
        milling_depth = my_lamella.custom_milling_depth
    else:
        milling_depth = stage_settings["milling_depth"]
    center_y = (
        lamella_center_y
        - (0.5 * stage_settings["lamella_height"])
        - (
            stage_settings["total_cut_height"]
            * stage_settings["percentage_from_lamella_surface"]
        )
        - (
            0.5
            * stage_settings["total_cut_height"]
            * stage_settings["percentage_roi_height"]
        )
    )
    height = float(
        stage_settings["total_cut_height"] * stage_settings["percentage_roi_height"]
    )
    if stage_settings["overtilt_degrees"] > 0:
        scaling_factor = np.cos(np.deg2rad(stage_settings["overtilt_degrees"]))
        height = (1.0 / scaling_factor) * height  # expand / stretch ROI height
        fiducial_y = my_lamella.fiducial_coord_realspace[1]
        hypotenuse = abs(center_y - fiducial_y)
        adjacent = hypotenuse * scaling_factor
        y_tilt_adjustment = hypotenuse - adjacent
        center_y = center_y - y_tilt_adjustment  # negative, moving further away
    milling_roi = microscope.patterning.create_cleaning_cross_section(
        lamella_center_x,
        center_y,
        stage_settings["lamella_width"],
        height,
        milling_depth,
    )
    milling_roi.scan_direction = "BottomToTop"
    return milling_roi


def save_final_images(microscope, settings, lamella_number):
    """Aquire and save ion beam & SEM images after complete milling stage."""
    output_dir = settings["save_directory"]
    fullfield_cam_settings = GrabFrameSettings(
        reduced_area=Rectangle(0, 0, 1, 1),
        resolution=settings["fiducial"]["reduced_area_resolution"],
        dwell_time=settings["imaging"]["dwell_time"],
    )
    if settings["imaging"]["autocontrast"]:
        microscope.imaging.set_active_view(2)  # the ion beam view
        microscope.auto_functions.run_auto_cb()
    if settings["imaging"]["full_field_ib_images"]:
        image = grab_ion_image(microscope, fullfield_cam_settings)
        filename = os.path.join(
            output_dir, "IB_lamella{}-milling-complete.tif".format(lamella_number + 1)
        )
        image.save(filename)
    sem_adorned_image = grab_sem_image(microscope, fullfield_cam_settings)
    sem_fname = "SEM_lamella{}-milling-complete.tif".format(lamella_number + 1)
    sem_filename = os.path.join(output_dir, sem_fname)
    sem_adorned_image.save(sem_filename)


def save_reference_images(settings, my_lamella, n_lamella=None):
    output_dir = settings["save_directory"]
    if n_lamella:
        n_lamella + 1  # 1 based indexing for user output
    else:
        n_lamella = ""
    # save overlay image
    filename_overlay = os.path.join(
        output_dir, "IB_lamella{}_overlay.png".format(n_lamella)
    )
    my_lamella.save_matplotlib_figure_with_overlays(settings, filename_overlay)
    # save original image
    filename_original_image = os.path.join(
        output_dir, "IB_lamella{}_original.tif".format(n_lamella)
    )
    my_lamella.original_image.save(filename_original_image)
    # save reference image (full field with fiducial marker)
    filename_reference_image = os.path.join(
        output_dir, "IB_lamella{}_fiducial_fullfield.tif".format(n_lamella)
    )
    my_lamella.reference_image.save(filename_reference_image)
    # save fiducial marker image (reduced area image)
    filename_fiducial_image = os.path.join(
        output_dir, "IB_lamella{}_fiducial.tif".format(n_lamella)
    )
    my_lamella.fiducial_image.save(filename_fiducial_image)
    # save SEM image
    filename_sem_original_image = os.path.join(
        output_dir, "SEM_lamella{}_original.tif".format(n_lamella)
    )
    if my_lamella.sem_image:
        my_lamella.sem_image.save(filename_sem_original_image)


def setup_milling(microscope, settings, stage_settings, my_lamella):
    # Move into position
    system_settings = settings["system"]
    ccs_file = system_settings["application_file_cleaning_cross_section"]
    microscope = reset_state(microscope, settings, application_file=ccs_file)
    my_lamella.fibsem_position.restore_state(microscope)
    microscope.beams.ion_beam.beam_current.value = stage_settings["milling_current"]
    return microscope


def realign_fiducial(microscope, settings, image, my_lamella):
    realign(microscope, image, my_lamella.fiducial_image)
    updated_fiducial_image = grab_images(microscope, settings, my_lamella)
    my_lamella.fiducial_image = updated_fiducial_image  # update fiducial image


def realign(microscope, new_image, reference_image):
    """Realign to reference image using beam shift.

    Parameters
    ----------
    microscope : Autoscript microscope object
    new_image : The most recent image acquired.
        Must have the same dimensions and relative position as the reference.
    reference_image : The reference image to align with.
        Muast have the same dimensions and relative position as the new image
    Returns
    -------
    microscope.beams.ion_beam.beam_shift.value
        The current beam shift position (after any realignment)
    """
    shift_in_meters = calculate_beam_shift(new_image, reference_image)
    try:
        microscope.beams.ion_beam.beam_shift.value += shift_in_meters
    except ApplicationServerException:
        logging.warning(
            "Cannot move beam shift beyond limits, "
            "will continue with no beam shift applied."
        )
    return microscope.beams.ion_beam.beam_shift.value


def run_drift_corrected_milling(
    microscope, correction_interval, reduced_area=Rectangle(0, 0, 1, 1)
):
    """
    Parameters
    ----------
    microscope : Autoscript microscope object
    correction_interval : Time in seconds between drift correction realignment
    reduced_area : Autoscript Rectangle() object
        Describes the reduced area view in relative coordinates, with the
        origin in the top left corner.
        Default value Rectangle(0, 0, 1, 1) uses the whole field of view.
    """
    s = GrabFrameSettings(reduced_area=reduced_area)
    reference_image = microscope.imaging.grab_frame(s)
    # start drift corrected patterning (is a blocking function, not asynchronous)
    microscope.patterning.start()
    while microscope.patterning.state == "Running":
        time.sleep(correction_interval)
        try:
            microscope.patterning.pause()
        except ApplicationServerException:
            continue
        else:
            new_image = microscope.imaging.grab_frame(s)
            realign(microscope, new_image, reference_image)
            microscope.patterning.resume()


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


def mill_single_stage(
    microscope, settings, stage_settings, stage_number, my_lamella, lamella_number
):
    filename_prefix = "lamella{}_stage{}".format(lamella_number + 1, stage_number + 1)
    demo_mode = settings["demo_mode"]
    upper_milling(
        microscope,
        settings,
        stage_settings,
        my_lamella,
        filename_prefix=filename_prefix,
        demo_mode=demo_mode,
    )
    lower_milling(
        microscope,
        settings,
        stage_settings,
        my_lamella,
        filename_prefix=filename_prefix,
        demo_mode=demo_mode,
    )


def mill_all_stages(
    microscope, protocol_stages, lamella_list, settings, output_dir="output_images"
):
    if lamella_list == []:
        logging.info("Lamella sample list is empty, nothing to mill here.")
        return
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    for stage_number, stage_settings in enumerate(protocol_stages):
        logging.info(
            "Protocol stage {} of {}".format(stage_number + 1, len(protocol_stages))
        )
        for lamella_number, my_lamella in enumerate(lamella_list):
            logging.info(
                "Lamella number {} of {}".format(lamella_number + 1, len(lamella_list))
            )
            # save all the reference images you took creating the fiducial
            if stage_number == 0:
                save_reference_images(settings, my_lamella, lamella_number)
            mill_single_stage(
                microscope,
                settings,
                stage_settings,
                stage_number,
                my_lamella,
                lamella_number,
            )
            # If this is the very last stage, take an image
            if stage_number + 1 == len(protocol_stages):
                save_final_images(microscope, settings, lamella_number)
            reset_state(microscope, settings)
