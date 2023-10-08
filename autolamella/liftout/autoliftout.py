import logging
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import os
import napari
import numpy as np
from fibsem import acquire, alignment, calibration, patterning
from fibsem import utils as fibsem_utils
from fibsem import validation
from fibsem.detection import detection
from fibsem.detection.detection import (
    ImageCentre,
    LamellaCentre,
    LamellaLeftEdge,
    LamellaRightEdge,
    LandingPost,
    NeedleTip,
    LandingPost,
    LamellaTopEdge,
    LamellaBottomEdge,
    detect_features,
    DetectedFeatures,
)
from fibsem import conversions
from fibsem.imaging import utils as image_utils
from fibsem.microscope import FibsemMicroscope
from fibsem.patterning import FibsemMillingStage, _get_milling_stages
from fibsem.structures import (
    BeamType,
    FibsemRectangle,
    FibsemStagePosition,
    FibsemImage,
    MicroscopeSettings,
    MicroscopeState,
    Point,
    ImageSettings
)
from fibsem.ui import windows as fibsem_ui_windows

from autolamella.liftout import actions
from autolamella.liftout.structures import AutoLiftoutStage, Experiment, Lamella
from autolamella.liftout.ui.AutoLiftoutUIv2 import AutoLiftoutUIv2
from fibsem import config as fcfg


from autolamella.workflows.core import log_status_message, start_of_stage_update, end_of_stage_update
from autolamella.workflows.ui import _validate_mill_ui, _update_status_ui, _set_images_ui, ask_user, _validate_det_ui_v2

# autoliftout workflow functions

def liftout_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:
    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["liftout"])
    settings.image.save_path = lamella.path

    # get ready to do liftout by moving to liftout angle (flat to eb)
    # actions.move_to_liftout_angle(microscope, settings)

    log_status_message(lamella, "ALIGN_REF_UNDERCUT")

    # detect
    log_status_message(lamella, f"ALIGN_TRENCH")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_trench_align_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    microscope.stable_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )

    # Align ion so it is coincident with the electron beam
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    
    # align vertical
    microscope.vertical_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )

    # lamella should now be centred in ion beam


    # reference images for needle location
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_needle_inserted"
    acquire.take_reference_images(microscope, settings.image)

    # land needle on lamella
    lamella = land_needle_on_milled_lamella(
        microscope, settings, lamella, validate=validate, parent_ui=parent_ui
    )

    log_status_message(lamella, "NEEDLE_JOIN_LAMELLA")
    _update_status_ui(
        parent_ui, f"{lamella.info} Joining Needle to Lamella..."
    )


    _JOINING_METHOD = settings.protocol["options"]["liftout_joining_method"].upper()
    logging.info(f"Using {_JOINING_METHOD} joining method")

    # joining options
    if  _JOINING_METHOD == "WELD":
        settings.image.beam_type = BeamType.ION

        features = [LamellaLeftEdge()]
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)


        # mill weld
        stages = _get_milling_stages(
            "weld", settings.protocol, det.features[0].feature_m
        )
        stages = _validate_mill_ui(stages, parent_ui, 
            msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
            validate=validate)
        
        lamella.protocol["join"] = deepcopy(patterning._get_protocol_from_stages(stages))
        lamella.protocol["join"]["point"] = stages[0].pattern.point.__to_dict__()

    logging.info(
        f"{lamella.state.stage.name}: lamella to needle joining complete."
    )

    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_contact"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    log_status_message(lamella, "NEEDLE_SEVER_LAMELLA")
    _update_status_ui(parent_ui, f"{lamella.info} Severing Lamella...")

    # sever lamella
    lamella = mill_lamella_edge(
        microscope=microscope,
        settings=settings,
        parent_ui=parent_ui,
        lamella=lamella,
        validate=validate,
        x_shift=1e-6,
    )

    # take reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_{lamella.state.stage.name}_sever"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    log_status_message(lamella, "NEEDLE_TRENCH_REMOVAL")
    _update_status_ui(
        parent_ui, f"{lamella.info} Removing Needle from trench..."
    )

    # Raise needle 30um from trench
    # move needle back from trench x
    dx = -1.5e-6
    microscope.move_manipulator_corrected(dx=dx, dy=0, beam_type=BeamType.ION)

    for i in range(3):
        microscope.move_manipulator_corrected(dx=0, dy=10e-6, beam_type=BeamType.ION)
        settings.image.label = f"liftout_trench_{i:02d}"
        acquire.take_reference_images(microscope, settings.image)
        time.sleep(1)

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    # move needle to park position
    microscope.retract_manipulator()  # retracted needle not supported on tescan

    return lamella


def land_needle_on_milled_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    validate: bool,
    parent_ui: AutoLiftoutStage,
) -> Lamella:
    # bookkeeping
    settings.image.save_path = lamella.path

    # validate needle insertion conditions
    # validate_needle_insertion(
    #     microscope, settings.system.stage.needle_stage_height_limit
    # )

    log_status_message(lamella, "INSERT_NEEDLE")
    _update_status_ui(parent_ui, f"{lamella.info} Inserting Needle...")

    # insert the needle for liftout
    actions.move_needle_to_liftout_position(microscope)

    # align needle to side of lamella
    log_status_message(lamella, "NEEDLE_EB_DETECTION")

    settings.image.beam_type = BeamType.ELECTRON

    features = [NeedleTip(), LamellaLeftEdge()]
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # offset from lamella
    logging.info(f"DISTANCE: {det.distance}")
    H_OFFSET = 2.5e-6
    det._offset = Point(-H_OFFSET, 0) 
    logging.info(f"OFFSET: {det._offset}")
    logging.info(f"DISTANCE: {det.distance}")
    
    detection.move_based_on_detection(
        microscope, settings, det, beam_type=settings.image.beam_type
    )

    log_status_message(lamella, "NEEDLE_IB_DETECTION")

    # need to do vertical movement twice, because needle isnt moving correctly in z
    # TODO: remove when needle movement is fixed.
    for i in range(2):
        settings.image.beam_type = BeamType.ION

        features = [NeedleTip(), LamellaLeftEdge()]
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type, move_x=False
        )

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_start_position"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    if validate:
        ask_user(
            parent_ui,
            msg="Confirm Needle is positioned to left of the Lamella Left Edge.",
            pos="Continue",
        )

    # charge neutralisation  to charge lamella
    settings.image.beam_type = BeamType.ION
    n_iter = int(
        settings.protocol["options"].get("liftout_charge_neutralisation_iterations", 35)
    )

    calibration.auto_charge_neutralisation(
        microscope=microscope, 
        image_settings=settings.image, 
        n_iterations=n_iter, 
        discharge_settings = ImageSettings(
            resolution=[768, 512],
            dwell_time=200e-9,
            hfw=settings.image.hfw,
            beam_type=BeamType.ION,
            save=False,
            autocontrast=False,
            gamma_enabled=False,
            label=None,
        )
    )

    X_LIFTOUT_CONTACT_OFFSET = settings.protocol["options"].get("liftout_contact_offset", 0.25e-6)
    features = [NeedleTip(), LamellaLeftEdge()]
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    det._offset = Point(x=X_LIFTOUT_CONTACT_OFFSET, y=0)
    detection.move_based_on_detection(microscope, settings, det, beam_type=settings.image.beam_type, move_y=False)

    _USE_CONTACT_DETECTION = settings.protocol["options"].get("liftout_contact_detection", False)
    if _USE_CONTACT_DETECTION:
        lamella = _liftout_contact_detection(microscope, settings, lamella, parent_ui, validate=validate)
                
    # move needle up in z to prevent bottoming out
    dz = 0.5e-6  # positive is away from sample (up)
    microscope.move_manipulator_corrected(dx=0, dy=dz, beam_type=BeamType.ION)

    # restore imaging settings
    settings.image.gamma_enabled = True
    settings.image.reduced_area = None

    acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        label=f"ref_{lamella.state.stage.name}_manipulator_landed",
    )

    return lamella

def _liftout_contact_detection(microscope: FibsemMicroscope, settings: MicroscopeSettings, 
                                lamella: Lamella, parent_ui: AutoLiftoutUIv2, validate: bool = True) -> Lamella:
    

    # measure brightness
    BRIGHTNESS_FACTOR = 1.2
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_land_initial"
    settings.image.save = True
    settings.image.gamma_enabled = False
    reduced_area = FibsemRectangle(
        0.2, 0.2, 0.70, 0.70
    )  # TODO: improve contact detection
    settings.image.reduced_area = reduced_area
    ib_image = acquire.new_image(microscope, settings.image)
    previous_brightness = image_utils.measure_brightness(ib_image)

    brightness_history = [previous_brightness]
    mean_brightness = np.mean(brightness_history)

    iteration_count = 0
    MAX_ITERATIONS = 15

    log_status_message(lamella, "NEEDLE_CONTACT_DETECTION")

    while True:
        # move needle down
        dx = 0.5e-6
        dy = 0.0e-6

        microscope.move_manipulator_corrected(dx=dx, dy=dy, beam_type=BeamType.ION)

        # calculate brightness
        settings.image.label = f"ref_{lamella.state.stage.name}_contact_brightness_{iteration_count}"
        ib_image = acquire.new_image(microscope, settings.image)
        brightness = image_utils.measure_brightness(ib_image)
        _set_images_ui(parent_ui, None, ib_image)

        logging.info(
            f"iter: {iteration_count}: brightness: {brightness}, prevs: {previous_brightness}, MEAN BRIGHTNESS: {mean_brightness}"
        )

        above_brightness_threshold = brightness > mean_brightness * BRIGHTNESS_FACTOR

        if above_brightness_threshold and validate is False:
            break  # exit loop

        if above_brightness_threshold or validate:
            # needle has landed...
            if above_brightness_threshold:
                logging.info("BRIGHTNESS THRESHOLD REACHED STOPPPING")

            msg = f"Has the needle landed on the lamella? Above Threshold: {above_brightness_threshold} ({iteration_count+1}/{MAX_ITERATIONS})"
            response = ask_user(parent_ui, msg=msg, pos="Yes", neg="No")
            if response is True:
                break

        previous_brightness = brightness
        brightness_history.append(brightness)
        mean_brightness = np.mean(brightness_history)

        iteration_count += 1
        if iteration_count >= MAX_ITERATIONS:
            break
    return lamella


def land_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:
    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["landing"])
    settings.image.save_path = lamella.path
    settings.image.save = False

    # move to landing coordinate
    microscope.set_microscope_state(lamella.landing_state)

    # align to ref
    log_status_message(lamella, "ALIGN_REF_LANDING")
    reference_images = lamella.get_reference_images("ref_landing")
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    # align to ref
    alignment.correct_stage_drift(
        microscope,
        settings,
        reference_images=reference_images,
        alignment=(BeamType.ION, BeamType.ION),
        rotate=False,
        xcorr_limit=(512, 100),
    )

    # confirm eucentricity
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    if validate:
        ask_user(
            parent_ui,
            msg=f"Confirm {lamella.info} is centred in both Beams. Press Continue to proceed.",
            pos="Continue",
        )

    ############################## LAND_LAMELLA ##############################
    # validate_needle_insertion(
    #     microscope, settings.system.stage.needle_stage_height_limit
    # )

    # landing entry
    log_status_message(lamella, "LAND_LAMELLA_ENTRY")
    _update_status_ui(
        parent_ui, f"{lamella.info} Landing Entry Procedure..."
    )
    # TODO tescan warning to insert needle
    landing_entry_procedure(microscope, settings, lamella=lamella, 
    validate=validate,parent_ui=parent_ui)
    # land lamella on post
    log_status_message(lamella, "LAND_LAMELLA_ON_POST")
    response = False
    _repeated_landing_attempt = False
    while response is False:
        if _repeated_landing_attempt:
            mill_lamella_edge(
                microscope,
                settings,
                parent_ui=parent_ui,
                lamella=lamella,
                validate=validate,
            )
        # land the lamella on the post
        land_lamella_on_post(
            microscope=microscope,
            settings= settings,
            parent_ui=parent_ui,
            lamella=lamella,
            validate=validate)

        # confirm with user
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        _set_images_ui(parent_ui, eb_image, ib_image)
        if validate:
            response = ask_user(
                parent_ui,
                msg=f"Confirm {lamella.info} has landed on post. \nPress Continue to proceed, or Repeat to attempt landing again.",
                pos="Continue",
                neg="Repeat",
            )
        else:
            response = True

        _repeated_landing_attempt = True

    log_status_message(lamella, "LAND_LAMELLA_REMOVE_NEEDLE")
    # move needle out of trench slowly at first (QUERY: is this required?)
    for i in range(3):
        microscope.move_manipulator_corrected(dx=0, dy=10e-6, beam_type=BeamType.ION)
        time.sleep(1)

    # move needle to park position
    microscope.retract_manipulator()

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    # reset manipulator
    RESET_REQUIRED = bool(settings.protocol["options"]["liftout_joining_method"].capitalize() != "None")

    response = True
    if validate:
        response = ask_user(parent_ui, msg="Do you want to Reset the manipulator?", pos="Reset", neg="Skip")

    if response and RESET_REQUIRED:
        lamella = reset_needle(microscope, settings, lamella,  parent_ui,)


    return lamella


def mill_lamella_edge(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    parent_ui: AutoLiftoutUIv2,
    lamella: Lamella = None,
    validate: bool = True,
    x_shift: float = 0,
):
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_mill_lamella_edge"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    log_status_message(
        lamella, f"{lamella.state.stage.name.upper()}_MILL_LAMELLA_EDGE"
    )
    _update_status_ui(parent_ui, f"{lamella.info} Mill Lamella Edge...")

    settings.image.beam_type = BeamType.ION

    features = [LamellaRightEdge()]
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # adjustment
    point = det.features[0].feature_m
    point.x += x_shift

    stages = _get_milling_stages("sever", settings.protocol, point=point)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the sever for {lamella._petname}. Press Continue when done.", 
        validate=validate)

    lamella.protocol[f"{lamella.state.stage.name}_sever"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol[f"{lamella.state.stage.name}_sever"]["point"] = stages[0].pattern.point.__to_dict__()

    # take reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_lamella_edge_milled"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    return lamella


def land_lamella_on_post(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    parent_ui: AutoLiftoutUIv2,
    lamella: Lamella,
    validate: bool = True,
):
    # done

    # repeat final movement until user confirms landing
    response = False
    i = 0
    while response is False:
        #### X-MOVE
        settings.image.hfw = (
            fcfg.REFERENCE_HFW_HIGH if i == 0 else fcfg.REFERENCE_HFW_SUPER
        )
        settings.image.beam_type = BeamType.ION
        settings.image.save = True
        settings.image.label = f"ref_{lamella.state.stage.name}_needle_pre_move_{i}"

        log_status_message(lamella, "LAND_LAMELLA_IB_DETECTION")

        features = [LamellaRightEdge(), LandingPost()]
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        logging.info(f"OFFSET: {det._offset}")
        logging.info(f"DISTANCE: {det.distance}")
        det._offset = Point(x=settings.protocol.get("landing_post_x_offset", 0.75e-6), y=0)
        logging.info(f"OFFSET: {det._offset}")
        logging.info(f"DISTANCE: {det.distance}")
        
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type
        )

        # final reference images
        settings.image.save = True
        settings.image.label = f"ref_{lamella.state.stage.name}_lamella_contact_{i}"
        eb_image, ib_image = acquire.take_reference_images(
            microscope=microscope, image_settings=settings.image
        )
        _set_images_ui(parent_ui, eb_image, ib_image)

        if validate:
            response =ask_user(
                parent_ui,
                msg=f"Confirm {lamella.info} has made contact with post. \nPress Continue to proceed or Repeat to repeat the landing attempt.",
                pos="Continue",
                neg="Repeat",
            )
        else:
            response = True

            # TODO: add a check where if the lamella edge and post are close enough, exit the loop

        # increment count
        i += 1

    #################################################################################################

    ############################## WELD TO LANDING POST #############################################

    log_status_message(lamella, "LAND_LAMELLA_WELD_TO_POST")

    settings.image.beam_type = BeamType.ION

    features = [LamellaRightEdge()]
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    point = det.features[0].feature_m 
    point.x += settings.protocol["weld"].get("width", 5e-6) / 2

    stages = _get_milling_stages("weld", settings.protocol, point)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["weld"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["weld"]["point"] = stages[0].pattern.point.__to_dict__()

    # final reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_lamella_final_weld_high_res"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)

    #################################################################################################

    ###################################### REMOVE NEEDLE ######################################

    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.beam_type = BeamType.ION
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_lamella_needle_removal"

    # charge neutralisation # discharge to unlock lamella
    response = False
    n_iter = int(
        settings.protocol["options"].get(
            "landing_charge_neutralisation_iterations", 100
        )
    )
    while response is False:
        settings.image.beam_type = BeamType.ELECTRON
        calibration.auto_charge_neutralisation(
            microscope, settings.image, n_iterations=n_iter
        )

        if validate:
            response = ask_user(
                parent_ui,
                msg=f"Repeat charge procedure? iter: {n_iter}. \nPress Continue to proceed or Repeat to repeat the dis-charge attempt.",
                pos="Continue",
                neg="Repeat",
            )
        else:
            response = True

    # optional? makes it not repeatable
    log_status_message(lamella, "LAND_LAMELLA_REMOVE_NEEDLE")

    logging.info(f"{lamella.state.stage.name}: removing needle from lamella")

    # back out needle from lamella , no cut required?
    for i in range(10):
        # move needle back
        microscope.move_manipulator_corrected(dx=-0.5e-6, dy=0, beam_type=BeamType.ION)

    # reference images
    acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        label=f"ref_{lamella.state.stage.name}_lamella_needle_removal",
    )

    return


def landing_entry_procedure(
    microscope: FibsemMicroscope, settings: MicroscopeSettings, lamella: Lamella, validate: bool = True,parent_ui=AutoLiftoutUIv2
):
    # entry procedure, align vertically to post
    actions.move_needle_to_landing_position(microscope)

    hfws = [
        fcfg.REFERENCE_HFW_LOW,
        fcfg.REFERENCE_HFW_MEDIUM,
        fcfg.REFERENCE_HFW_HIGH,
        fcfg.REFERENCE_HFW_HIGH,
    ]
    beam_types = [BeamType.ION, BeamType.ELECTRON, BeamType.ION, BeamType.ION]

    for i, (hfw, beam_type) in enumerate(zip(hfws, beam_types)):
        # needle starting position
        settings.image.hfw = hfw
        settings.image.beam_type = beam_type
        settings.image.save = True
        settings.image.label = f"ref_{lamella.state.stage.name}_needle_start_position_{i}"
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        _set_images_ui(parent_ui, eb_image, ib_image)
        
        features = [LamellaRightEdge(), LandingPost()]
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)
       
        det._offset = Point(-30e-6, 0)
        logging.info(f"DISTANCE: {det.distance}, OFFSET: {det._offset}")
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type
        )

    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_{lamella.state.stage.name}_needle_ready_position"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

def reset_needle(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:
    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["reset"])

    settings.image.save_path = lamella.path

    # move sample stage out
    actions.move_sample_stage_out(microscope, settings)

    ###################################### SHARPEN_NEEDLE ######################################

    validation.validate_stage_height_for_needle_insertion(
        microscope, settings.system.stage.needle_stage_height_limit
    )

    # move needle in
    actions.move_needle_to_reset_position(microscope)



    # needle imagesV
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_needle_start_position"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
    settings.image.beam_type = BeamType.ION

    # TODO: move needle to the centre, because it has been cut off...
    calibration.align_needle_to_eucentric_position(microscope, settings, validate=False)

    # TODO: validate this movement

    # # create sharpening patterns
    ask_user(
        parent_ui,
        msg="Please move the needle to the centre of the view and press OK",
        pos="OK",
    )

    stages = _get_milling_stages("sharpen", settings.protocol)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the sharpen for {lamella._petname}. Press Continue when done.", 
        validate=validate)

    lamella.protocol["reset"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["reset"]["point"] = stages[0].pattern.point.__to_dict__()

    #################################################################################################

    # reset the "eucentric position" for the needle, centre needle in both views
    calibration.align_needle_to_eucentric_position(microscope, settings, validate=True)

    # take reference images
    settings.image.label = f"ref_{lamella.state.stage.name}_final"
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.save = True
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)

    # retract needle
    microscope.retract_manipulator()

    # # reset stage position
    # move_settings = MoveSettings(rotate_compucentric=True)
    # stage.absolute_move(StagePosition(t=np.deg2rad(0)), move_settings)
    # stage.absolute_move(StagePosition(x=0.0, y=0.0), move_settings)
    microscope.move_stage_absolute(x=0.0, y=0.0, t=0.0)

    # TODO: test this
    if lamella.landing_selected:
        calibration.set_microscope_state(microscope, lamella.landing_state)

    return lamella
def run_setup_autoliftout(
    microscope: FibsemMicroscope,	
    settings: MicroscopeSettings,	
    experiment: Experiment,	
    parent_ui: AutoLiftoutUIv2,	
) -> Experiment:
    logging.info(f"INIT | {AutoLiftoutStage.Setup.name} | STARTED")

    # select the lamella and landing positions
    experiment = select_lamella_positions(microscope, settings, experiment, parent_ui)

    return experiment

from autolamella.workflows.core import mill_trench, mill_undercut, mill_lamella, setup_lamella
# autoliftout_workflow
WORKFLOW_STAGES = {
    AutoLiftoutStage.Setup: run_setup_autoliftout, # TODO: split this further
    AutoLiftoutStage.MillTrench: mill_trench,
    AutoLiftoutStage.MillUndercut: mill_undercut,
    AutoLiftoutStage.Liftout: liftout_lamella,
    AutoLiftoutStage.Landing: land_lamella,
    AutoLiftoutStage.SetupLamella: setup_lamella,
    AutoLiftoutStage.MillRoughCut: mill_lamella,
    AutoLiftoutStage.MillPolishingCut: mill_lamella,
}

def run_autoliftout_workflow(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> Experiment:

    CONFIRM_WORKFLOW_ADVANCE = bool(settings.protocol["options"]["confirm_advance"])

    _update_status_ui(parent_ui, "Starting AutoLiftout Workflow...")
    logging.info(
        f"AutoLiftout Workflow started for {len(experiment.positions)} lamellae."
    )
    settings.image.save = False
    settings.image.save_path = experiment.path
    settings.image.label = f"{fibsem_utils.current_timestamp()}"

    
    # batch mode workflow
    if True:
        for terminal_stage in [
            AutoLiftoutStage.MillTrench,
            AutoLiftoutStage.MillUndercut, # TODO: maybe add this to config?
        ]:
            lamella: Lamella
            for lamella in experiment.positions:
                if lamella.is_failure:
                    continue  # skip failures

                while lamella.state.stage.value < terminal_stage.value:
                    next_stage = AutoLiftoutStage(lamella.state.stage.value + 1)

                    # update image settings (save in correct directory)
                    settings.image.save_path = lamella.path

                    # reset to the previous state
                    lamella = start_of_stage_update(
                        microscope, lamella, next_stage=next_stage, parent_ui=parent_ui
                    )

                    # run the next workflow stage
                    lamella = WORKFLOW_STAGES[next_stage](
                        microscope=microscope,
                        settings=settings,
                        lamella=lamella,
                        parent_ui=parent_ui,
                    )
                    # advance workflow
                    experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

                    # update ui
                    parent_ui.update_experiment_signal.emit(experiment)

    # standard workflow
    lamella: Lamella
    for lamella in experiment.positions:
        if lamella.is_failure:
            continue  # skip failures

        while lamella.state.stage.value < AutoLiftoutStage.Landing.value:

            next_stage = AutoLiftoutStage(lamella.state.stage.value + 1)
            if CONFIRM_WORKFLOW_ADVANCE:
                msg = (
                    f"""Continue Lamella {(lamella._petname)} from {next_stage.name}?"""
                )
                response = ask_user(parent_ui, msg=msg, pos="Continue", neg="Skip")

            else:
                response = True

            # update image settings (save in correct directory)
            settings.image.save_path = lamella.path

            if response:
                # reset to the previous state
                lamella = start_of_stage_update(
                    microscope, lamella, next_stage=next_stage, parent_ui=parent_ui
                )

                # run the next workflow stage
                lamella = WORKFLOW_STAGES[next_stage](
                    microscope=microscope,
                    settings=settings,
                    lamella=lamella,
                    parent_ui=parent_ui,
                )

                # advance workflow
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)
                
                # update ui
                parent_ui.update_experiment_signal.emit(experiment)
            else:
                break  # go to the next lamella

    return experiment

def run_thinning_workflow(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> Experiment:

    _update_status_ui(parent_ui, "Starting MillRoughCut Workflow...")
    lamella: Lamella
    for next_stage in [
        AutoLiftoutStage.SetupLamella,
        AutoLiftoutStage.MillRoughCut,
        AutoLiftoutStage.MillPolishingCut,
    ]:
        for lamella in experiment.positions:
            if lamella.is_failure:
                continue

            if lamella.state.stage.value == next_stage.value - 1:
                lamella = start_of_stage_update(
                    microscope, lamella, next_stage=next_stage, parent_ui=parent_ui
                )
                WORKFLOW_STAGES[next_stage](microscope, settings, lamella,parent_ui)
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

    # finish the experiment
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLiftoutStage.MillPolishingCut:
            lamella = start_of_stage_update(microscope, lamella, next_stage=AutoLiftoutStage.Finished, parent_ui=parent_ui, _restore_state=False)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)


    return experiment

def get_current_lamella(
    experiment: Experiment, parent_ui: AutoLiftoutUIv2
) -> bool:
    select_another_lamella = (
        ask_user(
            parent_ui,
            msg=f"Do you want to select another lamella? {len(experiment.positions)} currentlly selected.",
            pos="Yes",
            neg="No",
        )
        if experiment.positions
        else True
    )
    return select_another_lamella


def select_initial_lamella_positions(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2 = None,
) -> Lamella:
    """Select the initial experiment positions for liftout"""

    # create lamella
    lamella_no = max(len(experiment.positions) + 1, 1)
    lamella = Lamella(experiment.path, lamella_no)
    log_status_message(lamella, "STARTED")

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.save = False
    eb_image,ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    log_status_message(lamella, "SELECT_LAMELLA_POSITION")
    stages = patterning._get_milling_stages("trench", settings.protocol)
    stages = _validate_mill_ui(stages, parent_ui,
        msg=f"Select a position and milling pattern for {lamella._petname}. Press Continue when done.",
        validate=True,
        milling_enabled=False
    )
    
    # log the protocol
    lamella.protocol["trench"] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol["trench"]["point"] = stages[0].pattern.point.__to_dict__()
    
    # need to set the imaging settings too?
    lamella.lamella_state = microscope.get_current_microscope_state()
    
    # save microscope state   

    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    lamella.state.microscope_state = lamella.lamella_state

    log_status_message(lamella, "LAMELLA_REFERENCE_IMAGES")

    settings.image.hfw = fcfg.REFERENCE_HFW_LOW
    settings.image.save = True
    settings.image.save_path = lamella.path

    acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_start",
    )

    return lamella


def select_landing_positions(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
):
    """Select landing positions for autoliftout"""

    ####################################
    # # move to landing grid
    landing_start_position = fibsem_utils._get_position(settings.protocol["options"]["landing_start_position"])
    microscope._safe_absolute_stage_movement(landing_start_position)

    settings.image.save = False
    ####################################

    # select corresponding experiment landing positions
    lamella: Lamella
    for lamella in experiment.positions:
        # check if landing position already selected? so it doesnt overwrite
        if lamella.landing_selected is False:
            settings.image.hfw = fcfg.REFERENCE_HFW_LOW
            lamella = select_landing_sample_positions(
                microscope, settings, lamella, parent_ui
            )

            experiment.save()

    return experiment


def select_landing_sample_positions(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:
    """Select the landing coordinates for a lamella."""
    logging.info(f"Selecting Landing Position: {lamella._petname}")

    # update image path
    settings.image.save_path = lamella.path
    settings.image.hfw = fcfg.REFERENCE_HFW_LOW

    # eb_image, ib_image = acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
    # _set_images_ui(parent_ui, eb_image, ib_image)

    # # select landing coordinates
    # ask_user(
    #     parent_ui,
    #     msg=f"Select the landing coordinate for {lamella._petname}.",
    #     pos="Continue",
    # )  # enable movement, imaging
    # lamella.landing_state = microscope.get_current_microscope_state()

    # mill the landing edge flat
    log_status_message(lamella, "SELECT_LANDING_POSITION")
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.beam_type = BeamType.ION
    settings.image.save = False

    eb_image, ib_image = acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    
    # log the protocol
    stages = _get_milling_stages("flatten", settings.protocol)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Select the landing position and prepare (mill) the area for {lamella._petname}. Press Continue when done.", 
        validate=True)
    
    lamella.protocol["flatten"] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol["flatten"]["point"] = stages[0].pattern.point.__to_dict__()
    lamella.landing_state = microscope.get_current_microscope_state()

    # take reference images
    log_status_message(lamella, "LANDING_REFERENCE_IMAGES")
    acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label="ref_landing",
    )

    lamella.landing_selected = True

    return lamella


def select_lamella_positions(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
):

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_LOW
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.save = True
    settings.image.save_path = experiment.path
    settings.image.label = f"initial_setup_grid_{fibsem_utils.current_timestamp_v2()}"
    eb_image,ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    select_another = get_current_lamella(experiment, parent_ui)

    if select_another:
        lamella_start_position = fibsem_utils._get_position(settings.protocol["options"]["lamella_start_position"])
        microscope._safe_absolute_stage_movement(lamella_start_position)

    # allow the user to select additional lamella positions
    while select_another:
        logging.info(f"Selecting Lamella Position: {select_another}")
        lamella = select_initial_lamella_positions(
            microscope, settings, experiment, parent_ui
        )

        # save lamella data
        experiment.positions.append(deepcopy(lamella))
        experiment.save()

        # select another?
        select_another = get_current_lamella(experiment, parent_ui)

    # select landing positions
    select_landing_positions(microscope, settings, experiment, parent_ui)

    # finish setup
    finish_setup_autoliftout(microscope, experiment, parent_ui)

    return experiment


def finish_setup_autoliftout(
    microscope: FibsemMicroscope,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
):
    """Finish the setup stage for autolifout/autolamella"""

    parent_ui._set_instructions(msg="Ready for AutoLiftout", pos=None, neg=None)

    for lamella in experiment.positions:
        if lamella.state.stage == AutoLiftoutStage.Setup:
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)

    logging.info(f"Selected {len(experiment.positions)} lamella for autoliftout.")
    logging.info(f"INIT | {AutoLiftoutStage.Setup.name} | FINISHED")




def validate_needle_insertion(
    microscope: FibsemMicroscope, needle_stage_height_limit: float = 3.7e-3
) -> None:
    while validation.validate_stage_height_for_needle_insertion(
        microscope, needle_stage_height_limit
    ):
        fibsem_ui_windows.ask_user_interaction(
            msg=f"""The system has identified the distance between the sample and the pole piece is less than {needle_stage_height_limit * 1000}mm. "
            "The needle will contact the sample, and it is unsafe to insert the needle. "
            "\nPlease manually refocus and link the stage, then press OK to continue. """,
        )





# TODO: MOVE TO FIBSEM
def _calculate_fiducial_area_v2(image: FibsemImage, fiducial_centre: Point, fiducial_length:float)->tuple[FibsemRectangle, bool]:
    pixelsize = image.metadata.pixel_size.x
    
    fiducial_centre.y = -fiducial_centre.y
    fiducial_centre_px = conversions.convert_point_from_metres_to_pixel(
        fiducial_centre, pixelsize
    )

    rcx = fiducial_centre_px.x / image.metadata.image_settings.resolution[0] + 0.5
    rcy = fiducial_centre_px.y / image.metadata.image_settings.resolution[1] + 0.5

    fiducial_length_px = (
        conversions.convert_metres_to_pixels(fiducial_length, pixelsize) * 1.5 # SCALE_FACTOR
    )
    h_offset = fiducial_length_px / image.metadata.image_settings.resolution[0] / 2
    v_offset = fiducial_length_px / image.metadata.image_settings.resolution[1] / 2

    left = rcx - h_offset
    top = rcy - v_offset
    width = 2 * h_offset
    height = 2 * v_offset

    if left < 0 or (left + width) > 1 or top < 0 or (top + height) > 1:
        flag = True
    else:
        flag = False

    fiducial_area = FibsemRectangle(left, top, width, height)

    return fiducial_area, flag