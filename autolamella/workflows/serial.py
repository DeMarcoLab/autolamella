import logging
import time
from copy import deepcopy

from fibsem import acquire, alignment, calibration, patterning
from fibsem import utils as fibsem_utils
from fibsem.detection import detection
from fibsem.detection.detection import (
    ImageCentre,
    LamellaCentre,
    LamellaLeftEdge,
    LamellaRightEdge,
    NeedleTip,
    LandingPost,
    LandingGridCentre,
    LamellaTopEdge,
    LamellaBottomEdge,
    CopperAdapterBottomEdge,
    CopperAdapterTopEdge,
    VolumeBlockCentre,
    VolumeBlockTopEdge,
    VolumeBlockBottomEdge,
    VolumeBlockTopLeftCorner,
    VolumeBlockTopRightCorner,
    VolumeBlockBottomLeftCorner,
    VolumeBlockBottomRightCorner,
)

from fibsem.microscope import FibsemMicroscope
from fibsem.patterning import FibsemMillingStage, get_milling_stages
from fibsem.structures import (
    BeamType,
    FibsemRectangle,
    FibsemStagePosition,
    FibsemImage,
    MicroscopeSettings,
    MicroscopeState,
    Point,
)
import numpy as np
from autolamella.workflows import actions
from autolamella.structures import AutoLamellaWaffleStage, Experiment, Lamella
from autolamella.ui.AutoLiftoutUIv2 import AutoLiftoutUIv2
from fibsem import config as fcfg

from collections import Counter
from autolamella.structures import Lamella, Experiment, LamellaState, AutoLamellaWaffleStage
from autolamella.workflows.autoliftout import log_status_message, start_of_stage_update, end_of_stage_update, setup_lamella, mill_lamella
from autolamella.workflows.ui import ask_user, update_status_ui, update_detection_ui, set_images_ui,  update_milling_ui
from autolamella.workflows.core import align_feature_coincident, mill_trench, mill_undercut
from pprint import pprint

# serial workflow functions

def liftout_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:

    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["liftout"])
    settings.image.path = lamella.path

    # move to liftout angle...
    log_status_message(lamella, "MOVE_TO_LIFTOUT_POSITION")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Liftout Position...")

    # move the stage flat to ion beam
    microscope.move_flat_to_beam(
        beam_type=BeamType.ION,
    )    
    
    # get alignment feature
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
    print(f"SCAN ROTATION: {scan_rotation}")
    feature = VolumeBlockBottomEdge() if np.isclose(scan_rotation, 0) else VolumeBlockTopEdge()

    # align feature so beams are coincident
    lamella = align_feature_coincident(microscope=microscope, 
                             settings=settings, 
                              lamella=lamella, 
                              parent_ui=parent_ui, 
                              validate=validate, 
                              hfw=fcfg.REFERENCE_HFW_MEDIUM,
                              feature=feature)

    # insert the manipulator for liftout
    log_status_message(lamella, "INSERT_MANIPULATOR")
    update_status_ui(parent_ui, f"{lamella.info} Inserting Manipulator...")
    microscope.insert_manipulator("PARK")

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.filename = f"ref_{lamella.state.stage.name}_manipualtor_inserted"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # align manipulator to top of lamella in electron

    log_status_message(lamella, f"NEEDLE_EB_DETECTION_0")
    update_status_ui(parent_ui, f"{lamella.info} Moving Manipulator to Lamella...")

    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    # DETECT COPPER ADAPTER, VOLUME TOP
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
    features = [CopperAdapterTopEdge(), VolumeBlockBottomEdge()] if np.isclose(scan_rotation, 0) else [CopperAdapterBottomEdge(), VolumeBlockTopEdge()]
    
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # MOVE TO VOLUME BLOCK TOP
    detection.move_based_on_detection(
        microscope, settings, det, beam_type=settings.image.beam_type, move_x=True,
         _move_system="manipulator"
    )

    # align manipulator to top of lamella in ion x3
    HFWS = [fcfg.REFERENCE_HFW_LOW, fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER]

    for i, hfw in enumerate(HFWS):

        log_status_message(lamella, f"NEEDLE_IB_DETECTION_{i:02d}")
        update_status_ui(parent_ui, f"{lamella.info} Moving Manipulator to Lamella...")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = hfw

        # DETECT COPPER ADAPTER, LAMELLA TOP
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [CopperAdapterTopEdge(), VolumeBlockBottomEdge()] if np.isclose(scan_rotation, 0) else [CopperAdapterBottomEdge(), VolumeBlockTopEdge()]
        
        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # MOVE TO VOLUME BLOCK TOP
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type, move_x=True, 
            _move_system="manipulator"
        )

    # reference images
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.save = True
    settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_landed"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # WELD
    log_status_message(lamella, "WELD_VOLUME_TO_COPPER")
    update_status_ui(parent_ui, f"{lamella.info} Welding Volume to Copper...")

    features = [VolumeBlockBottomEdge() if np.isclose(scan_rotation, 0) else VolumeBlockTopEdge()] 
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # move the pattern to the top of the volume (i.e up by half the height of the pattern)
    _V_OFFSET = settings.protocol["milling"]["liftout-weld"].get("height", 5e-6) / 2
    if np.isclose(scan_rotation, 0):
        _V_OFFSET *= -1
    point = det.features[0].feature_m 
    point.y += _V_OFFSET

    stages = get_milling_stages("liftout-weld", settings.protocol["milling"], point)
    stages = update_milling_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["liftout-weld"] = deepcopy(patterning.get_protocol_from_stages(stages[0]))
    lamella.protocol["liftout-weld"]["point"] = stages[0].pattern.point.to_dict()

    # reference images
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_weld"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # SEVER
    log_status_message(lamella, "SEVER_VOLUME_BLOCK")
    update_status_ui(parent_ui, f"{lamella.info} Sever Manipulator...")

    # repeat severing until the volume is free
    while True:
        settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

        features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge()] 
        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        point = det.features[0].feature_m 
        set_images_ui(parent_ui, None, det.fibsem_image)

        stages = get_milling_stages("liftout-sever", settings.protocol["milling"], point)
        stages = update_milling_ui(stages, parent_ui, 
            msg=f"Press Run Milling to sever for {lamella._petname}. Press Continue when done.", 
            validate=validate)
        
        lamella.protocol["liftout-sever"] = deepcopy(patterning.get_protocol_from_stages(stages[0]))
        lamella.protocol["liftout-sever"]["point"] = stages[0].pattern.point.to_dict()

        # reference images
        settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
        settings.image.save = True
        settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_sever"
        acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
        set_images_ui(parent_ui, eb_image, ib_image)

        # RETRACT MANIPULATOR
        log_status_message(lamella, "RETRACT_MANIPULATOR")
        update_status_ui(parent_ui, f"{lamella.info} Retracting Manipulator...")

        # retract small and validate
        microscope.move_manipulator_corrected(dx=0, dy=0.5e-6, beam_type=BeamType.ION)
        settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_removal_initial"
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        set_images_ui(parent_ui, eb_image, ib_image)

        # TODO: implemented automated detection for separation of volume from trench
        if validate:
            response = ask_user(parent_ui, msg=f"Press Continue to confirm to separation of volume for {lamella._petname}.", pos="Continue", neg="Repeat")

        if response:
            logging.info(f"Volume Severed for {lamella._petname}, response: {response}")
            break

    # retract slowly at first
    for i in range(10):
        microscope.move_manipulator_corrected(dx=0, dy=1e-6, beam_type=BeamType.ION)
        if i % 3 == 0:
            settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_removal_slow_{i:02d}"
            eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
            set_images_ui(parent_ui, eb_image, ib_image)
        time.sleep(1)

    # then retract quickly
    for i in range(3):
        microscope.move_manipulator_corrected(dx=0, dy=20e-6, beam_type=BeamType.ION)
        settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_removal_{i:02d}"
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        set_images_ui(parent_ui, eb_image, ib_image)
        time.sleep(1)

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.state.stage.name}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    # move needle to park position
    microscope.retract_manipulator()  # retracted needle not supported on tescan


    return lamella

def land_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:

    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["landing"])
    settings.image.path = lamella.path

    # # MOVE TO LANDING POSITION
    log_status_message(lamella, "MOVE_TO_LANDING_POSITION")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Landing Position...")

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.filename = f"ref_{lamella.state.stage.name}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)


    if validate:
        response = ask_user(parent_ui, msg=f"Press Continue to confirm to landing position for {lamella._petname}.", pos="Continue")

    # INSER MANIPUALTOR TO PARK
    log_status_message(lamella, "INSERT_MANIPULATOR")
    update_status_ui(parent_ui, f"{lamella.info} Inserting Manipulator...")

    # insert the needle for landing
    actions.move_needle_to_park_position(microscope)

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_LOW
    settings.image.filename = f"ref_{lamella.state.stage.name}_manipualtor_inserted"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)


    # align in electron beam
    log_status_message(lamella, f"NEEDLE_EB_DETECTION_INITIAL")
    update_status_ui(parent_ui, f"{lamella.info} Moving Volume to Landing Grid...")

    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    # DETECT COPPER ADAPTER, LAMELLA TOP
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ELECTRON)
    features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge(), LandingGridCentre()]  # TODO: SCAN_ROTATION FOR LANDING_POST
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    set_images_ui(parent_ui, det.fibsem_image, None)

    # MOVE TO LANDING GRID
    detection.move_based_on_detection(
        microscope, settings, det, 
        beam_type=settings.image.beam_type, 
        _move_system="manipulator"
    )

    # DETECT LAMELLA BOTTOM EDGE, LandingGridCentre_TOP
    # align manipulator to top of lamella
    log_status_message(lamella, "NEEDLE_IB_DETECTION")
    update_status_ui(parent_ui, f"{lamella.info} Moving Volume to Landing Grid...")

    HFWS = [fcfg.REFERENCE_HFW_LOW, fcfg.REFERENCE_HFW_MEDIUM]#, fcfg.REFERENCE_HFW_HIGH]
    for i, hfw in enumerate(HFWS):

        log_status_message(lamella, f"NEEDLE_IB_DETECTION_{i:02d}")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = hfw

        # DETECT COPPER ADAPTER, LAMELLA TOP
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge(), LandingGridCentre()]  # TODO: SCAN_ROTATION FOR LANDING_POST
        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
        set_images_ui(parent_ui, None, det.fibsem_image)

        # offset above the grid
        det._offset = Point(0, -20e-6) 

        # MOVE TO LANDING POST
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type, move_x=True, 
            _move_system="manipulator"
        )

        log_status_message(lamella, "NEEDLE_IB_DETECTION")




    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    # DETECT COPPER ADAPTER, LAMELLA TOP
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
    features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge(), LandingGridCentre()]  # TODO: SCAN_ROTATION FOR LANDING_POST
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    set_images_ui(parent_ui, None, det.fibsem_image)
    
    # MOVE TO LANDING GRID
    detection.move_based_on_detection(
        microscope, settings, det, 
        beam_type=settings.image.beam_type, 
        move_x=True,
        move_y=False,
        _move_system="manipulator"
    )

    # TODO: check if the volume is wider than the landing grid
    # mill away excess width

    # align in ion beam
    log_status_message(lamella, f"NEEDLE_IB_DETECTION_FINAL")
    update_status_ui(parent_ui, f"{lamella.info} Moving Volume to Landing Grid...")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    # DETECT COPPER ADAPTER, LAMELLA TOP
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
    features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge(), LandingGridCentre()]  # TODO: SCAN_ROTATION FOR LANDING_POST
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    set_images_ui(parent_ui, None, det.fibsem_image)
    
    # MOVE TO LANDING GRID
    detection.move_based_on_detection(
        microscope, settings, det, 
        beam_type=settings.image.beam_type, 
        move_x=False,
        _move_system="manipulator"
    )

    # WELD BOTH SIDES
    log_status_message(lamella, "WELD_LAMELLA_TO_POST")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [VolumeBlockTopLeftCorner(), VolumeBlockTopRightCorner()] if np.isclose(scan_rotation, 0) else [VolumeBlockBottomLeftCorner(), VolumeBlockBottomRightCorner()]
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    set_images_ui(parent_ui, None, det.fibsem_image)

    # get the points
    left_corner = det.features[0].feature_m 
    right_corner = det.features[1].feature_m

    # add some offset in y
    v_offset = 2e-6  # half of recommended 4um height
    left_corner.y  +=  v_offset
    right_corner.y +=  v_offset

    # mill welds
    stages = get_milling_stages("landing-weld", settings.protocol["milling"], [left_corner, right_corner])
    stages = update_milling_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["landing-weld"] = deepcopy(patterning.get_protocol_from_stages(stages[0]))
    lamella.protocol["landing-weld"]["point"] = stages[0].pattern.point.to_dict()

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.filename = f"ref_{lamella.state.stage.name}_weld_volume_to_post"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    ########################
    # move manipulator up 50-100 nm to create strain
    dy = 100e-9
    microscope.move_manipulator_corrected(dx=0, dy=dy, beam_type=BeamType.ION)

    ######################### 

    # SEVER
    lamella = sever_lamella_block(microscope, settings, lamella, parent_ui, validate)

    # RETRACT MANIPULATOR
    log_status_message(lamella, "RETRACT_MANIPULATOR")
    update_status_ui(parent_ui, f"{lamella.info} Retracting Manipulator...")

    # move up slowly at first
    for i in range(10):
        microscope.move_manipulator_corrected(dx=0, dy=1e-6, beam_type=BeamType.ION)
        if i % 5 == 0:
            settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_removal_slow{i:02d}"
            eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
            set_images_ui(parent_ui, eb_image, ib_image)
        time.sleep(1)
    
    # move manipulator up
    microscope.move_manipulator_corrected(dx=0, dy=100e-6, beam_type=BeamType.ION)

    # move needle to park position
    microscope.retract_manipulator()  # retracted needle not supported on tescan

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.state.stage.name}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella

def sever_lamella_block(microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
    validate: bool = True) -> Lamella:

    # bookkeeping
    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)

    # SEVER
    confirm_severed = False
    i = 0
    while confirm_severed is False:
        log_status_message(lamella, f"SEVER_LAMELLA_BLOCK_{i:02d}")
        update_status_ui(parent_ui, f"{lamella.info} Severing Lamella Block...")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

        features = [VolumeBlockTopEdge() if np.isclose(scan_rotation, 0) else VolumeBlockBottomEdge()]  
        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
        set_images_ui(parent_ui, None, det.fibsem_image)
                
        point = det.features[0].feature_m

        stages = get_milling_stages("landing-sever", settings.protocol["milling"], point)
        stages = update_milling_ui(stages, parent_ui, 
            msg=f"Press Run Milling to sever for {lamella._petname}. Press Continue when done.", 
            validate=validate)
        
        lamella.protocol["landing-sever"] = deepcopy(patterning.get_protocol_from_stages(stages[0]))
        lamella.protocol["landing-sever"]["point"] = stages[0].pattern.point.to_dict()

        # reference images
        settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
        settings.image.save = True
        settings.image.filename = f"ref_{lamella.state.stage.name}_sever_volume_block_{i:02d}"
        eb_image, ib_image = acquire.take_reference_images(microscope=microscope, image_settings=settings.image)
        set_images_ui(parent_ui, eb_image, ib_image)

        # move up slowly at first
        for j in range(3):
            microscope.move_manipulator_corrected(dx=0, dy=50e-9, beam_type=BeamType.ION)
            settings.image.filename = f"ref_{lamella.state.stage.name}_manipulator_removal_check{j:02d}"
            acquire.take_reference_images(microscope, settings.image)
            time.sleep(1)

        # confirm that the lamella is free     
        log_status_message(lamella, f"CONFIRM_LAMELLA_SEVER_{i:02d}")
        update_status_ui(parent_ui, f"{lamella.info} Confirming Lamella has been Severed...")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

        features = [VolumeBlockTopEdge(), LamellaBottomEdge()] if np.isclose(scan_rotation, 0) else [VolumeBlockBottomEdge(), LamellaTopEdge()]  
        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # if the distance is less than the threshold, then the lamella is not severed
        threshold = settings.protocol["options"].get("landing-sever-threshold", 0.5e-6)
        if abs(det.distance.y) < threshold:
            logging.info(f"Lamella Not Severed: {det.distance.y} < {threshold}")
            logging.debug({"msg": "check_volume_sever",  "detected_features": det.to_dict(), "threshold": threshold})   
            confirm_severed = False
        
        # check with the user
        if validate:
            response = ask_user(parent_ui, msg=f"Confirm Lamella has been severed for {lamella._petname}. Distance measured was {det.distance.y*1e6} um. (Threshold = {threshold*1e6}) um", 
                                pos="Confirm", neg="Retry")
            confirm_severed = response

        i += 1

    return lamella




# serial workflow functions
SERIAL_WORKFLOW_STAGES = {
    AutoLamellaWaffleStage.MillTrench: mill_trench,
    AutoLamellaWaffleStage.MillUndercut: mill_undercut,
    AutoLamellaWaffleStage.LiftoutLamella: liftout_lamella,
    AutoLamellaWaffleStage.LandLamella: land_lamella,
    AutoLamellaWaffleStage.SetupLamella: setup_lamella,
    AutoLamellaWaffleStage.MillRoughCut: mill_lamella,
    AutoLamellaWaffleStage.MillPolishingCut: mill_lamella,
}

def run_serial_liftout_workflow(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> Experiment:
    """Run the serial AutoLiftout workflow for a given experiment. """
    BATCH_MODE = bool(settings.protocol["options"]["batch_mode"])
    CONFIRM_WORKFLOW_ADVANCE = bool(settings.protocol["options"]["confirm_next_stage"])

    update_status_ui(parent_ui, "Starting AutoLiftout Workflow...")
    logging.info(
        f"Serial Workflow started for {len(experiment.positions)} lamellae."
    )
    settings.image.save = False
    settings.image.path = experiment.path
    settings.image.filename = f"{fibsem_utils.current_timestamp()}"

    # standard workflow
    lamella: Lamella
    for lamella in experiment.positions:
        if lamella._is_failure:
            logging.info(f"Skipping {lamella._petname} due to failure.")
            continue  # skip failures

        while lamella.state.stage.value < AutoLamellaWaffleStage.LiftoutLamella.value:
            next_stage = AutoLamellaWaffleStage(lamella.state.stage.value + 1)
            if CONFIRM_WORKFLOW_ADVANCE:
                msg = (
                    f"""Continue Lamella {(lamella._petname)} from {next_stage.name}?"""
                )
                response = ask_user(parent_ui, msg=msg, pos="Continue", neg="Skip")

            else:
                response = True

            # update image settings (save in correct directory)
            settings.image.path = lamella.path

            if response:
                # reset to the previous state
                lamella = start_of_stage_update(
                    microscope, lamella, next_stage=next_stage, parent_ui=parent_ui
                )

                # run the next workflow stage
                lamella = SERIAL_WORKFLOW_STAGES[next_stage](
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


def run_serial_liftout_landing(    
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> Experiment:
    """Run the serial AutoLiftout workflow for landing a given experiment. """
    BATCH_MODE = bool(settings.protocol["options"]["batch_mode"])
    CONFIRM_WORKFLOW_ADVANCE = bool(settings.protocol["options"]["confirm_next_stage"])

    update_status_ui(parent_ui, "Starting Serial Liftout (Landing) Workflow...")
    logging.info(
        f"Serial Landing Workflow started for {len(experiment.positions)} lamellae."
    )

    lamella = experiment.positions[0]
    settings.image.save = False
    settings.image.path = lamella.path
    settings.image.filename = f"{fibsem_utils.current_timestamp()}"

    # move to landing position
    log_status_message(lamella, "MOVING_TO_LANDING_POSITION")
    update_status_ui(parent_ui, "Moving to Landing Position...")   
    microscope.set_microscope_state(lamella.landing_state)

    # take images, 
    log_status_message(lamella, "REFERENCE_IMAGES")
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.filename = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # calculate landing positions
    log_status_message(lamella, "CALCULATE_LANDING_POSITIONS")
    update_status_ui(parent_ui, "Generating Landing Positions...")   
    positions = _calculate_landing_positions(microscope, settings)

    # see where we are in the workflow
    _counter = Counter([p.state.stage.name for p in experiment.positions])
    land_idx = _counter[AutoLamellaWaffleStage.LandLamella.name]
    # count how many at finished
    finished_idx = _counter[AutoLamellaWaffleStage.Finished.name]

    # start of workflow
    response = ask_user(parent_ui, msg=f"Land Another Lamella? ({land_idx} Lamella Landed, {finished_idx} Lamella Finished)", pos="Continue", neg="Finish")

    while response:

        # create another lamella
        experiment.positions.append(deepcopy(_create_lamella(microscope, experiment, positions)))
        experiment.save()
        lamella = experiment.positions[-1]

        # advance workflow
        lamella = start_of_stage_update(microscope, lamella, 
            next_stage=AutoLamellaWaffleStage.LandLamella, parent_ui=parent_ui)

        # run the next workflow stage
        lamella = SERIAL_WORKFLOW_STAGES[AutoLamellaWaffleStage.LandLamella](
            microscope=microscope,
            settings=settings,
            lamella=lamella,
            parent_ui=parent_ui,
        )

        # advance workflow
        experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui=parent_ui)
                
        # update ui
        parent_ui.update_experiment_signal.emit(experiment)

        # land another lamella?
        _counter = Counter([p.state.stage.name for p in experiment.positions])
        land_idx = _counter[AutoLamellaWaffleStage.LandLamella.name]
        response = ask_user(parent_ui, msg=f"Land Another Lamella? ({land_idx} Lamella Landed), {finished_idx} Lamella Finished)", 
            pos="Continue", neg="Finish")

    return experiment



def _create_lamella(microscope: FibsemMicroscope, experiment: Experiment, positions: list[FibsemStagePosition]) -> Lamella:

    # create a new lamella for landing
    _counter = Counter([p.state.stage.name for p in experiment.positions])
    land_idx = _counter[AutoLamellaWaffleStage.LandLamella.name]

    print("COUNTER: ", _counter, land_idx)

    num = max(len(experiment.positions) + 1, 1)
    lamella = Lamella(path=experiment.path, _number=num)
    log_status_message(lamella, "CREATION")

    # set state
    lamella.state.stage = AutoLamellaWaffleStage.LiftoutLamella
    lamella.state.microscope_state = microscope.get_microscope_state()
    lamella.state.microscope_state.stage_position = deepcopy(positions[land_idx])
    lamella.landing_state = deepcopy(lamella.state.microscope_state)

    print("LANDING POSITION")
    pprint(lamella.state.microscope_state.stage_position)
    print("---------")

    return lamella



# WORKFLOW

# SETUP
# MILL_TRENCH
# MILL_UNDERCUT
# LIFTOUT
# LOOP UNTIL NO MORE BULK / LANDING POSTS:
    # LANDING
# MILL_ROUGH
# MILL_REGULAR
# MILL_POLISH



def _prepare_manipulator(    
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> None:

    # bookeeping
    validate = True
    settings.image.path = experiment.path


    # move to the landing grid

    # insert the manipulator

    # flatten to manipualtor (optional)

    # move manpiulator to the grid

    # weld

    # sever

    # retract manipulator

    return

def _calculate_landing_positions(microscope, settings) -> list[FibsemStagePosition]:
    """Calculate the landing positions for a given experiment."""
    # make user set the initial position for the landing grid
    # create a grid of positions, based on the grid sizes x, y
    # loop through each position until block is consumed


    # base state = top left corner
    base_state = microscope.get_microscope_state()

    # get the landing grid protocol
    landing_grid_protocol = settings.protocol["options"]["landing_grid"]
    grid_square = Point(landing_grid_protocol['x'], landing_grid_protocol['y'])
    n_rows, n_cols = landing_grid_protocol['rows'], landing_grid_protocol['cols']

    positions = []

    for i in range(n_rows):
        for j in range(n_cols):
            _new_position = microscope.project_stable_move( 
                dx=grid_square.x*j, 
                dy=-grid_square.y*i, 
                beam_type=BeamType.ION, 
                base_position=base_state.stage_position)            
            
            # position name is number of position in the grid
            _new_position.name = f"Landing Position {i*n_cols + j:02d}"
            
            positions.append(_new_position)

    return positions