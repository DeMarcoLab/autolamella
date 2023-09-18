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
    LamellaTopEdge,
    LamellaBottomEdge,
    CopperAdapterBottomEdge,
    CopperAdapterTopEdge,
)

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
)
import numpy as np
from autolamella.liftout import actions
from autolamella.liftout.structures import AutoLiftoutStage, Experiment, Lamella
from autolamella.liftout.ui.AutoLiftoutUIv2 import AutoLiftoutUIv2
from fibsem import config as fcfg

from collections import Counter
from autolamella.liftout.structures import Lamella, Experiment, AutoLiftoutState, AutoLiftoutStage
from autolamella.liftout.autoliftout import log_status_message, start_of_stage_update, end_of_stage_update
from autolamella.liftout.autoliftout import ask_user, _update_status_ui, _validate_det_ui_v2, _update_mill_stages_ui, _set_images_ui,  _validate_mill_ui

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
    settings.image.save_path = lamella.path

    # move to liftout angle...
    log_status_message(lamella, "MOVE_TO_LIFTOUT_POSITION")
    _update_status_ui(parent_ui, f"{lamella.info} Moving to Liftout Position...")

    # TODO: set true tilt angle here

    # ALIGN LAMELLA TOP
    log_status_message(lamella, f"ALIGN_TRENCH")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning to Trench...")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_trench_align_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
    features = [LamellaBottomEdge() if np.isclose(scan_rotation, 0) else LamellaTopEdge()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    microscope.stable_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )

    # Align ion so it is coincident with the electron beam
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    features = [LamellaBottomEdge() if np.isclose(scan_rotation, 0) else LamellaTopEdge()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    
    # align vertical
    microscope.eucentric_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_trench_align_coincident"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # INSER MANIPUALTOR TO PARK
    log_status_message(lamella, "INSERT_MANIPULATOR")
    _update_status_ui(parent_ui, f"{lamella.info} Inserting Manipulator...")

    # insert the needle for liftout
    actions.move_needle_to_liftout_position(microscope, dx=0.0e-6, dz=25.0e-6)

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_manipualtor_inserted"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # align manipulator to top of lamella
    HFWS = [fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER]

    # TODO: we can move the needle closer initially, dont need to start so far away

    for i, hfw in enumerate(HFWS):

        log_status_message(lamella, f"NEEDLE_IB_DETECTION_{i:02d}")
        _update_status_ui(parent_ui, f"{lamella.info} Moving Manipulator to Lamella...")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = hfw

        # DETECT COPPER ADAPTER, LAMELLA TOP
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [CopperAdapterTopEdge(), LamellaBottomEdge()] if np.isclose(scan_rotation, 0) else [CopperAdapterBottomEdge(), LamellaTopEdge()]
        
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # MOVE TO LAMELLA TOP
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type, move_x=True
        )

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_landed"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # WELD
    log_status_message(lamella, "WELD_LAMELLA_TO_COPPER")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaBottomEdge() if np.isclose(scan_rotation, 0) else LamellaTopEdge()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    _V_OFFSET = 1e-6
    point = det.features[0].feature_m 
    point.y += settings.protocol["liftout_weld"].get("height", 5e-6) / 2 + 1e-6 # TODO: make this a parameter

    stages = _get_milling_stages("liftout_weld", settings.protocol, point)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["liftout_weld"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["liftout_weld"]["point"] = stages[0].pattern.point.__to_dict__()

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_weld"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)

    # SEVER
    log_status_message(lamella, "SEVER_LAMELLA_BLOCK")
    _update_status_ui(parent_ui, f"{lamella.info} Sever Manipulator...")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    point = det.features[0].feature_m 

    stages = _get_milling_stages("liftout_sever", settings.protocol, point)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to sever for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["liftout_sever"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["liftout_sever"]["point"] = stages[0].pattern.point.__to_dict__()

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_sever"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)


    # RETRACT MANIPULATOR
    log_status_message(lamella, "RETRACT_MANIPULATOR")
    _update_status_ui(parent_ui, f"{lamella.info} Retracting Manipulator...")

    for i in range(3):
        microscope.move_manipulator_corrected(dx=0, dy=10e-6, beam_type=BeamType.ION)
        settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_removal_{i:02d}"
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

def land_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLiftoutUIv2,
) -> Lamella:

    # bookkeeping
    validate = bool(settings.protocol["options"]["supervise"]["landing"])
    settings.image.save_path = lamella.path

    # # MOVE TO LANDING POSITION
    # log_status_message(lamella, "MOVE_TO_LANDING_POSITION")
    # _update_status_ui(parent_ui, f"{lamella.info} Moving to Landing Position...")

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)


    if validate:
        response = ask_user(parent_ui, msg=f"Press Continue to confirm to landing position for {lamella._petname}.", pos="Continue")

    # INSER MANIPUALTOR TO PARK
    log_status_message(lamella, "INSERT_MANIPULATOR")
    _update_status_ui(parent_ui, f"{lamella.info} Inserting Manipulator...")

    # insert the needle for liftout
    actions.move_needle_to_park_position(microscope)

    # reference images
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_LOW
    settings.image.label = f"ref_{lamella.state.stage.name}_manipualtor_inserted"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)


    # DETECT LAMELLA BOTTOM EDGE, LANDINGPOST_TOP
    # align manipulator to top of lamella
    log_status_message(lamella, "NEEDLE_IB_DETECTION")
    _update_status_ui(parent_ui, f"{lamella.info} Moving Lamella to Landing Post...")

    HFWS = [fcfg.REFERENCE_HFW_LOW, fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH]
    for i, hfw in enumerate(HFWS):

        log_status_message(lamella, f"NEEDLE_IB_DETECTION_{i:02d}")

        settings.image.beam_type = BeamType.ION
        settings.image.hfw = hfw

        # DETECT COPPER ADAPTER, LAMELLA TOP
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge(), LandingPost()]  # TODO: SCAN_ROTATION FOR LANDING_POST
        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # hover 25um above the post
        # det._offset = Point(0, -15e-6) 

        # MOVE TO LANDING POST
        detection.move_based_on_detection(
            microscope, settings, det, beam_type=settings.image.beam_type, move_x=True
        )

    # LAND LAMELLA ONTO LANDING POST 2
    # align manipulator to top of lamella
    # log_status_message(lamella, "NEEDLE_IB_DETECTION_2")

    # settings.image.beam_type = BeamType.ION
    # settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    # # DETECT COPPER ADAPTER, LAMELLA TOP
    # features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge(), LandingPost()]  # TODO: SCAN_ROTATION FOR LANDING_POST
    # det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # # MOVE TO LANDING POST
    # detection.move_based_on_detection(
    #     microscope, settings, det, beam_type=settings.image.beam_type, move_x=False
    # )

    # WELD BOTH SIDES
    log_status_message(lamella, "WELD_LAMELLA_TO_POST")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaLeftEdge(), LamellaRightEdge()]
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    left_point = det.features[0].feature_m 
    right_point = det.features[1].feature_m

    stages = _get_milling_stages("weld", settings.protocol, [left_point, right_point])
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to mill the weld for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["liftout_weld"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["liftout_weld"]["point"] = stages[0].pattern.point.__to_dict__()

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_weld_lamella_to_post"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)


    ######################### 

    # SEVER
    log_status_message(lamella, "SEVER_LAMELLA_BLOCK")
    _update_status_ui(parent_ui, f"{lamella.info} Severing Lamella Block...")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge()]  
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    _LAMELLA_THICKNESS = 10e-6 / 2  # TODO: make this a parameter
    _V_OFFSET = settings.protocol["landing_sever"].get("height", 2e-6) / 2 + _LAMELLA_THICKNESS
    
    if np.isclose(scan_rotation, 0):
        _V_OFFSET *= -1
    
    point = det.features[0].feature_m
    point.y += _V_OFFSET

    stages = _get_milling_stages("landing_sever", settings.protocol, point)
    stages = _validate_mill_ui(stages, parent_ui, 
        msg=f"Press Run Milling to sever for {lamella._petname}. Press Continue when done.", 
        validate=validate)
    
    lamella.protocol["landing_sever"] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
    lamella.protocol["landing_sever"]["point"] = stages[0].pattern.point.__to_dict__()

    # reference images
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.save = True
    settings.image.label = f"ref_{lamella.state.stage.name}_sever_lamella_block"
    acquire.take_reference_images(microscope=microscope, image_settings=settings.image)


    # RETRACT MANIPULATOR
    log_status_message(lamella, "RETRACT_MANIPULATOR")
    _update_status_ui(parent_ui, f"{lamella.info} Retracting Manipulator...")

    for i in range(3):
        microscope.move_manipulator_corrected(dx=0, dy=10e-6, beam_type=BeamType.ION)
        settings.image.label = f"ref_{lamella.state.stage.name}_manipulator_removal_{i:02d}"
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

from autolamella.liftout.autoliftout import setup_lamella, mill_lamella, mill_lamella_trench, mill_lamella_undercut
from autolamella.workflows.core import mill_trench, mill_undercut

# serial workflow functions
SERIAL_WORKFLOW_STAGES = {
    AutoLiftoutStage.MillTrench: mill_trench,
    AutoLiftoutStage.MillUndercut: mill_lamella_undercut,
    AutoLiftoutStage.Liftout: liftout_lamella,
    AutoLiftoutStage.Landing: land_lamella,
    AutoLiftoutStage.SetupPolish: setup_lamella,
    AutoLiftoutStage.MillRoughCut: mill_lamella,
    AutoLiftoutStage.MillRegularCut: mill_lamella,
    AutoLiftoutStage.MillPolishingCut: mill_lamella,
}

def run_serial_liftout_workflow(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLiftoutUIv2,
) -> Experiment:
    """Run the serial AutoLiftout workflow for a given experiment. """
    BATCH_MODE = bool(settings.protocol["options"]["batch_mode"])
    CONFIRM_WORKFLOW_ADVANCE = bool(settings.protocol["options"]["confirm_advance"])

    _update_status_ui(parent_ui, "Starting AutoLiftout Workflow...")
    logging.info(
        f"Serial Workflow started for {len(experiment.positions)} lamellae."
    )
    settings.image.save = False
    settings.image.save_path = experiment.path
    settings.image.label = f"{fibsem_utils.current_timestamp()}"

    # standard workflow
    lamella: Lamella
    for lamella in experiment.positions:
        if lamella.is_failure:
            logging.info(f"Skipping {lamella._petname} due to failure.")
            continue  # skip failures

        while lamella.state.stage.value < AutoLiftoutStage.Liftout.value:
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
    CONFIRM_WORKFLOW_ADVANCE = bool(settings.protocol["options"]["confirm_advance"])

    _update_status_ui(parent_ui, "Starting Serial Liftout (Landing) Workflow...")
    logging.info(
        f"Serial Landing Workflow started for {len(experiment.positions)} lamellae."
    )

    lamella = experiment.positions[0]
    settings.image.save = False
    settings.image.save_path = lamella.path
    settings.image.label = f"{fibsem_utils.current_timestamp()}"

    # move to landing position
    log_status_message(lamella, "MOVING_TO_LANDING_POSITION")
    _update_status_ui(parent_ui, "Moving to Landing Position...")   
    microscope.set_microscope_state(lamella.landing_state)

    # take images, 
    log_status_message(lamella, "REFERENCE_IMAGES")
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # calculate landing positions
    log_status_message(lamella, "CALCULATE_LANDING_POSITIONS")
    _update_status_ui(parent_ui, "Generating Landing Positions...")   
    positions = _calculate_landing_positions(microscope, settings)

    # see where we are in the workflow
    _counter = Counter([p.state.stage.name for p in experiment.positions])
    land_idx = _counter[AutoLiftoutStage.Landing.name]
    # count how many at finished
    finished_idx = _counter[AutoLiftoutStage.Finished.name]

    # start of workflow
    response = ask_user(parent_ui, msg=f"Land Another Lamella? ({land_idx} Lamella Landed, {finished_idx} Lamella Finished)", pos="Continue", neg="Finish")

    while response:

        # create another lamella
        experiment.positions.append(deepcopy(_create_lamella(microscope, experiment, positions)))
        experiment.save()
        lamella = experiment.positions[-1]

        # advance workflow
        lamella = start_of_stage_update(microscope, lamella, 
            next_stage=AutoLiftoutStage.Landing, parent_ui=parent_ui)

        # run the next workflow stage
        lamella = SERIAL_WORKFLOW_STAGES[AutoLiftoutStage.Landing](
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
        land_idx = _counter[AutoLiftoutStage.Landing.name]
        response = ask_user(parent_ui, msg=f"Land Another Lamella? ({land_idx} Lamella Landed), {finished_idx} Lamella Finished)", 
            pos="Continue", neg="Finish")

    return experiment



def _create_lamella(microscope: FibsemMicroscope, experiment: Experiment, positions: list[FibsemStagePosition]) -> Lamella:

    # create a new lamella for landing
    _counter = Counter([p.state.stage.name for p in experiment.positions])
    land_idx = _counter[AutoLiftoutStage.Landing.name]

    print("COUNTER: ", _counter, land_idx)

    lamella_no = max(len(experiment.positions) + 1, 1)
    lamella = Lamella(experiment.path, lamella_no)
    log_status_message(lamella, "CREATION")

    # set state
    lamella.state.stage = AutoLiftoutStage.Liftout
    lamella.state.microscope_state = microscope.get_current_microscope_state()
    lamella.state.microscope_state.absolute_position = deepcopy(positions[land_idx])
    lamella.landing_state = deepcopy(lamella.state.microscope_state)

    print("LANDING POSITION")
    pprint(lamella.state.microscope_state.absolute_position)
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
    settings.image.save_path = experiment.path


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
    base_state = microscope.get_current_microscope_state()

    # get the landing grid protocol
    landing_grid_protocol = settings.protocol["options"]["landing_grid"]
    grid_square = Point(landing_grid_protocol['x'], landing_grid_protocol['y'])
    n_rows, n_cols = landing_grid_protocol['rows'], landing_grid_protocol['cols']

    positions = []

    for i in range(n_rows):
        for j in range(n_cols):
            _new_position = microscope._calculate_new_position( 
                settings=settings, 
                dx=grid_square.x*j, 
                dy=-grid_square.y*i, 
                beam_type=BeamType.ION, 
                base_position=base_state.absolute_position)            
            
            # position name is number of position in the grid
            _new_position.name = f"Landing Position {i*n_cols + j:02d}"
            
            positions.append(_new_position)

    return positions