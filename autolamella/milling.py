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
    grab_images,
    save_reference_images,
    save_final_images,
)
from autolamella.autoscript import reset_state
from autolamella.align import realign


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
    realign(microscope, image_unaligned, my_lamella.fiducial_image)
    my_lamella.fiducial_image = grab_images(microscope, settings, my_lamella)
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
        microscope.imaging.set_active_view(2)  # the ion beam view
        try:
            microscope.patterning.run()
        except ApplicationServerException:
            logging.error("ApplicationServerException: could not mill!")
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
    realign(microscope, image_unaligned, my_lamella.fiducial_image)
    my_lamella.fiducial_image = grab_images(microscope, settings, my_lamella)
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
        microscope.imaging.set_active_view(2)  # the ion beam view
        try:
            microscope.patterning.run()
        except ApplicationServerException:
            logging.error("ApplicationServerException: could not mill!")
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
        stage_settings["total_cut_height"] *
        stage_settings["percentage_roi_height"]
    )
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
        stage_settings["total_cut_height"] *
        stage_settings["percentage_roi_height"]
    )
    milling_roi = microscope.patterning.create_cleaning_cross_section(
        lamella_center_x,
        center_y,
        stage_settings["lamella_width"],
        height,
        milling_depth,
    )
    milling_roi.scan_direction = "BottomToTop"
    return milling_roi


def setup_milling(microscope, settings, stage_settings, my_lamella):
    """Setup the ion beam system ready for milling."""
    system_settings = settings["system"]
    ccs_file = system_settings["application_file_cleaning_cross_section"]
    microscope = reset_state(microscope, settings, application_file=ccs_file)
    my_lamella.fibsem_position.restore_state(microscope)
    microscope.beams.ion_beam.beam_current.value = stage_settings["milling_current"]
    return microscope


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


def mill_single_stage(
    microscope, settings, stage_settings, stage_number, my_lamella, lamella_number
):
    """Run ion beam milling for a single milling stage in the protocol."""
    filename_prefix = "lamella{}_stage{}".format(
        lamella_number + 1, stage_number + 1)
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
    """Run all milling stages in the protocol."""
    if lamella_list == []:
        logging.info("Lamella sample list is empty, nothing to mill here.")
        return
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    for stage_number, stage_settings in enumerate(protocol_stages):
        logging.info(
            "Protocol stage {} of {}".format(
                stage_number + 1, len(protocol_stages))
        )
        for lamella_number, my_lamella in enumerate(lamella_list):
            logging.info(
                "Lamella number {} of {}".format(
                    lamella_number + 1, len(lamella_list))
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
