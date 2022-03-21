import logging
import os
import time

import numpy as np

from autolamella.acquire import (
    grab_images,
    save_reference_images,
    save_final_images,
)
from autolamella.align import realign
from autolamella.autoscript import reset_state


def milling(
        microscope,
        settings,
        stage_settings,
        my_lamella,
        pattern,  # "upper", "lower", "both"
        filename_prefix="",
        demo_mode=False,
):
    from autoscript_core.common import ApplicationServerException
    from autoscript_sdb_microscope_client.structures import StagePosition

    # Sanity-check pattern parameter
    if pattern not in ("upper", "lower", "both"):
        raise ValueError("Invalid pattern type: should be \"upper\", \"lower\" or \"both\", not " + pattern)

    # Setup and realign to fiducial marker
    setup_milling(microscope, settings, stage_settings, my_lamella)
    tilt_in_radians = np.deg2rad(stage_settings["overtilt_degrees"])
    if pattern == "upper":
        microscope.specimen.stage.relative_move(StagePosition(t=-tilt_in_radians))
    elif pattern == "lower":
        microscope.specimen.stage.relative_move(StagePosition(t=+tilt_in_radians))

    # Realign three times
    for abc in "abc":
        image_unaligned = grab_images(
            microscope,
            settings,
            my_lamella,
            prefix="IB_" + filename_prefix,
            suffix="_0{}-unaligned".format(abc),
        )
        realign(microscope, image_unaligned, my_lamella.fiducial_image)

    # Save the newly aligned image for the next alignment stage
    my_lamella.fiducial_image = grab_images(
        microscope,
        settings,
        my_lamella,  # can remove
        prefix="IB_" + filename_prefix,
        suffix="_1-aligned",
    )
    # Create and mill patterns
    if pattern == "upper" or pattern == "both":
        _milling_coords(microscope, stage_settings, my_lamella, "upper")
    if pattern == "lower" or pattern == "both":
        _milling_coords(microscope, stage_settings, my_lamella, "lower")
    # Create microexpansion joints (if applicable)
    _microexpansion_coords(microscope, stage_settings, my_lamella)
    if 'patterning_mode' in stage_settings:
        microscope.patterning.mode = stage_settings['patterning_mode']
    if not demo_mode:
        microscope.imaging.set_active_view(2)  # the ion beam view
        print("Milling pattern...")
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
        suffix="_2-after-{}-milling".format(pattern),
    )
    return microscope


def _milling_coords(microscope, stage_settings, my_lamella, pattern):
    """Create milling pattern for lamella position."""
    # Sanity-check pattern parameter
    if pattern not in ("upper", "lower"):
        raise ValueError("Invalid pattern type for milling coords generation: should be \"upper\" or \"lower\", not "
                         + pattern)
    microscope.imaging.set_active_view(2)  # the ion beam view
    lamella_center_x, lamella_center_y = my_lamella.center_coord_realspace
    if my_lamella.custom_milling_depth is not None:
        milling_depth = my_lamella.custom_milling_depth
    else:
        milling_depth = stage_settings["milling_depth"]

    height = float(
        stage_settings["total_cut_height"] * stage_settings.get(f"percentage_roi_height_{pattern}",
                                                                stage_settings["percentage_roi_height"])
    )
    center_offset = (
            (0.5 * stage_settings["lamella_height"])
            + (stage_settings["total_cut_height"] * stage_settings["percentage_from_lamella_surface"])
            + (0.5 * height)
    )
    center_y = lamella_center_y + center_offset \
        if pattern == "upper" \
        else lamella_center_y - center_offset

    # milling_roi = microscope.patterning.create_cleaning_cross_section(
    milling_roi = microscope.patterning.create_rectangle(
        lamella_center_x,
        center_y,
        stage_settings.get(f'lamella_width_{pattern}', stage_settings["lamella_width"]),
        height,
        milling_depth,
    )
    if pattern == "upper":
        milling_roi.scan_direction = "TopToBottom"
    elif pattern == "lower":
        milling_roi.scan_direction = "BottomToTop"
    return milling_roi


def _microexpansion_coords(microscope, stage_settings, my_lamella):
    """Mill microexpansion joints (TODO: add reference)"""

    if not ("microexpansion_width" in stage_settings
            and "microexpansion_distance_from_lamella" in stage_settings
            and "microexpansion_percentage_height" in stage_settings):
        return None

    microscope.imaging.set_active_view(2)  # the ion beam view
    lamella_center_x, lamella_center_y = my_lamella.center_coord_realspace
    if my_lamella.custom_milling_depth is not None:
        milling_depth = my_lamella.custom_milling_depth
    else:
        milling_depth = stage_settings["milling_depth"]

    height = float(
        (
                2 * stage_settings["total_cut_height"]
                * (stage_settings["percentage_roi_height"] + stage_settings["percentage_from_lamella_surface"])
                + stage_settings["lamella_height"]
        ) * stage_settings["microexpansion_percentage_height"]
    )
    offset_x = (stage_settings["lamella_width"] + stage_settings["microexpansion_width"]) / 2 \
               + stage_settings["microexpansion_distance_from_lamella"]
    milling_rois = []
    for scan_direction, offset_x in (("LeftToRight", -offset_x), ("RightToLeft", offset_x)):
        milling_roi = microscope.patterning.create_rectangle(
            lamella_center_x + offset_x,
            lamella_center_y,
            stage_settings["microexpansion_width"],
            height,
            milling_depth,
        )
        milling_roi.scan_direction = scan_direction
        milling_rois.append(milling_roi)
    return milling_rois


def setup_milling(microscope, settings, stage_settings, my_lamella):
    """Setup the ion beam system ready for milling."""
    system_settings = settings["system"]
    ccs_file = system_settings["application_file_cleaning_cross_section"]
    microscope = reset_state(microscope, settings, application_file=ccs_file)
    my_lamella.fibsem_position.restore_state(microscope)
    microscope.beams.ion_beam.beam_current.value = stage_settings["milling_current"]
    return microscope


def run_drift_corrected_milling(microscope, correction_interval,
                                reduced_area=None):
    """
    Parameters
    ----------
    microscope : Autoscript microscope object
    correction_interval : Time in seconds between drift correction realignment
    reduced_area : Autoscript Rectangle() object
        Describes the reduced area view in relative coordinates, with the
        origin in the top left corner.
        Default value is None, which will create a Rectangle(0, 0, 1, 1),
        which means the imaging will use the whole field of view.
    """
    from autoscript_core.common import ApplicationServerException
    from autoscript_sdb_microscope_client.structures import (GrabFrameSettings,
                                                             Rectangle)

    if reduced_area is None:
        reduced_area = Rectangle(0, 0, 1, 1)
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
    milling(
        microscope,
        settings,
        stage_settings,
        my_lamella,
        pattern="both",
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
    # Return ion beam current to imaging current (20 pico-Amps)
    microscope.beams.ion_beam.beam_current.value = 20e-12
