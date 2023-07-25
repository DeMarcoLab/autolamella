import logging
import os
from copy import deepcopy
from datetime import datetime
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
from fibsem import acquire, milling, patterning, utils, calibration
from fibsem.microscope import FibsemMicroscope
from fibsem.patterning import FibsemMillingStage
from fibsem.structures import (
    BeamType,
    FibsemStagePosition,
    FibsemImage,
    MicroscopeSettings,
    Point, FibsemRectangle
)
import time
from autolamella.structures import (
    AutoLamellaStage,
    AutoLamellaWaffleStage,
    Experiment,
    Lamella,
)
from fibsem.detection import detection
from fibsem.detection.detection import (
    ImageCentre,
    LamellaCentre,
    LamellaLeftEdge,
    LamellaRightEdge,
    LandingPost,
    NeedleTip,
    LandingPost,
    detect_features,
    DetectedFeatures,
)
from autolamella.ui.AutoLamellaUI import AutoLamellaUI
from fibsem import config as fcfg

def log_status_message(lamella: Lamella, step: str):
    logging.debug(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | {step}")


def mill_trench(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("trench", True)
    settings.image.save_path = lamella.path

    # TODO: cross correlate the reference here
    fname = os.path.join(lamella.path, "ref_position_ib.tif")
    img = FibsemImage.load(fname)

    settings.image.hfw = settings.protocol["trench"]["hfw"]
    settings.image.label = f"ref_trench_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    _update_status_ui(parent_ui, f"{lamella.info} Preparing Trench...")

    # define trench
    settings.protocol["trench"]["cleaning_cross_section"] = False
    stages = patterning._get_milling_stages("trench", settings.protocol, point=lamella.trench_position)
    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )

    # charge neutralisation
    _update_status_ui(parent_ui, f"{lamella.info} Neutralising Sample Charge...")
    settings.image.beam_type = BeamType.ELECTRON
    calibration.auto_charge_neutralisation(microscope, settings.image)

    # refernce images
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_SUPER],
        label="ref_trench",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella

def mill_undercut(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("undercut", True)
    settings.image.save_path = lamella.path

    # TODO: cross correlate the reference here
    fname = os.path.join(lamella.path, "ref_trench_high_res_ib.tif")
    img = FibsemImage.load(fname)

    # rotate flat to eb
    _update_status_ui(parent_ui, f"{lamella.info} Moving to Undercut Position...")
    microscope.move_flat_to_beam(settings, BeamType.ELECTRON)

    # tilt down, align to trench
    _update_status_ui(parent_ui, f"{lamella.info} Tilting to Undercut Position...")
    tilt_angle = settings.protocol["autolamella_undercut"].get("tilt_angle", 10)
    print(f'------------- tilt angle {tilt_angle} --------------------')
    microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(tilt_angle)))


    # detect
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_trench_align_ml_01"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    features = [LamellaCentre()] # TODO: add LamellaBottom / Top Edge
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # mill undercut 1
    settings.protocol["autolamella_undercut"]["cleaning_cross_section"] = False
    stages = patterning._get_milling_stages("autolamella_undercut", settings.protocol, point=det.features[0].feature_m)
    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the First Undercut for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )

    # tilt down, align to trench
    _update_status_ui(parent_ui, f"{lamella.info} Tilting to Undercut Position...")
    tilt_angle_step = settings.protocol["autolamella_undercut"].get("tilt_angle_step", 10)
    microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(tilt_angle_step)))
    
    # detect
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_trench_align_ml_02"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    features = [LamellaCentre()] # TODO: add LamellaBottom / Top Edge
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

    # mill undercut 2
    settings.protocol["autolamella_undercut"]["cleaning_cross_section"] = False
    stages = patterning._get_milling_stages("autolamella_undercut", settings.protocol, point=det.features[0].feature_m)
    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the Second Undercut for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )

    # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_SUPER],
        label="ref_undercut",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

def mill_feature(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("features", True)
    settings.image.save_path = lamella.path

    # check if using notch or microexpansion
    _feature_name = "notch" if settings.protocol["notch"]["enabled"] else "microexpansion"
    # TODO: cross correlate the reference here
    # fname = os.path.join(lamella.path, "ref_position_lamella_ib.tif")
    # img = FibsemImage.load(fname)

    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_{_feature_name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    _update_status_ui(parent_ui, f"{lamella.info} Preparing {_feature_name}...")

    # define notch/microexpansion
    stages = patterning._get_milling_stages(
        _feature_name, lamella.protocol, point=lamella.feature_position
    )

    # optional fiducial
    use_fiducial = settings.protocol["fiducial"]["enabled"]
    if use_fiducial:
        fiducial_stage = patterning._get_milling_stages("fiducial", lamella.protocol, lamella.fiducial_centre)
        stages += fiducial_stage


    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the {_feature_name} for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
    # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_SUPER],
        label=f"ref_{_feature_name}",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella



def mill_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("lamella", True)
    settings.image.save_path = lamella.path

    # TODO: cross correlate the reference here
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Lamella...")

    # define feature
    stages = patterning._get_milling_stages(
        "lamella", lamella.protocol, point=lamella.lamella_position
    )

    # filter stage based on the current stage
    stage_map = {
        AutoLamellaWaffleStage.MillRoughCut: 0,
        AutoLamellaWaffleStage.MillRegularCut: 1,
        AutoLamellaWaffleStage.MillPolishingCut: 2,
    }
    idx = stage_map[lamella.state.stage]
    stages = [stages[idx]]# TODO: make this so user can define a number of stages to run

    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the Trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )


    # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        label=f"ref_lamella_{lamella.state.stage.name}",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella


def setup_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("setup_lamella", True)
    settings.image.save_path = lamella.path


    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_setup_lamella"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # select positions and protocol for feature (notch or microexpansion), lamella
    _feature_name = "notch" if settings.protocol["notch"]["enabled"] else "microexpansion"
    feature_stages = patterning._get_milling_stages(_feature_name, settings.protocol)
    
    lamella_stages = patterning._get_milling_stages("lamella", settings.protocol)
    stages = lamella_stages + feature_stages

    # optional fiducial
    use_fiducial = settings.protocol["fiducial"]["enabled"]
    if use_fiducial:
        fiducial_stage = patterning._get_milling_stages("fiducial", settings.protocol)
        stages += fiducial_stage

    stages =_validate_mill_ui(microscope, settings, stages, parent_ui, 
        msg=f"Confirm the positions for the {lamella._petname} milling. Don't run milling yet, this is just setup.", 
        validate=validate)
    
    from pprint import pprint 
    pprint(stages)

    # lamella
    n_lamella = len(lamella_stages)
    lamella.lamella_position = stages[0].pattern.point
    lamella.protocol["lamella"] = deepcopy(patterning._get_protocol_from_stages(stages[:n_lamella]))
    
    # feature
    n_features = len(feature_stages)
    lamella.feature_position = stages[n_lamella].pattern.point
    lamella.protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(stages[n_lamella:n_lamella+n_features]))

    logging.info(f"Feature position: {lamella.feature_position}")
    logging.info(f"Lamella position: {lamella.lamella_position}")

    # fiducial
    if use_fiducial:
        n_fiducial = len(fiducial_stage)
        lamella.fiducial_centre = stages[-n_fiducial].pattern.point
        lamella.protocol["fiducial"] = deepcopy(patterning._get_protocol_from_stages(stages[-n_fiducial:]))
        print("FIDUCIAL: ", lamella.protocol["fiducial"])
        lamella.fiducial_area, _  = _calculate_fiducial_area_v2(ib_image, lamella.fiducial_centre, lamella.protocol["fiducial"]["stages"][0]["height"])
        # lamella.fiducial_area = FibsemRectangle(0, 1.0, 0, 1.0)
        print("FIDUCIAL AREA: ", lamella.fiducial_area)
        logging.info(f"Fiducial centre: {lamella.fiducial_centre}")


    log_status_message(lamella, "LAMELLA_SETUP_REF")
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    # # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        label="ref_setup_lamella",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella


def end_of_stage_update(
    microscope: FibsemMicroscope, experiment: Experiment, lamella: Lamella, parent_ui: AutoLamellaUI
) -> Experiment:
    """Save the current microscope state configuration to disk, and log that the stage has been completed."""

    # save state information
    lamella.state.microscope_state = microscope.get_current_microscope_state()
    lamella.state.end_timestamp = datetime.timestamp(datetime.now())

    # write history
    lamella.history.append(deepcopy(lamella.state))

    # # update and save experiment
    experiment.save()

    logging.info(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | FINISHED")
    _update_status_ui(parent_ui, f"{lamella.info} Finished")

    return experiment


def start_of_stage_update(
    microscope: FibsemMicroscope,
    lamella: Lamella,
    next_stage: AutoLamellaStage,
    parent_ui: AutoLamellaUI
) -> Lamella:
    """Check the last completed stage and reload the microscope state if required. Log that the stage has started."""
    last_completed_stage = lamella.state.stage

    # restore to the last state
    if last_completed_stage.value == next_stage.value - 1:
        logging.info(
            f"{lamella._petname} restarting from end of stage: {last_completed_stage.name}"
        )
        _update_status_ui(parent_ui, f"{lamella.info} Restoring Last State...")
        microscope.set_microscope_state(lamella.state.microscope_state)

    # set current state information
    lamella.state.stage = next_stage
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    logging.info(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | STARTED")
    _update_status_ui(parent_ui, f"{lamella.info} Starting...")

    return lamella


WORKFLOW_STAGES = {
    AutoLamellaWaffleStage.MillTrench: mill_trench,
    AutoLamellaWaffleStage.MillUndercut: mill_undercut,
    AutoLamellaWaffleStage.SetupLamella: setup_lamella,
    AutoLamellaWaffleStage.MillFeatures: mill_feature,
    AutoLamellaWaffleStage.MillRoughCut: mill_lamella,
    AutoLamellaWaffleStage.MillRegularCut: mill_lamella,
    AutoLamellaWaffleStage.MillPolishingCut: mill_lamella,
}


def run_trench_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui=None,
) -> Experiment:
    for lamella in experiment.positions:
        logging.info(
            f"------------------------{lamella._petname}----------------------------------------"
        )
        if lamella.state.stage == AutoLamellaWaffleStage.ReadyTrench:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1), 
                parent_ui=parent_ui
            )

            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)

        logging.info(
            "----------------------------------------------------------------------------------------"
        )
    return experiment


def run_undercut_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui=None,
) -> Experiment:
    for lamella in experiment.positions:
        logging.info(
            f"------------------------{lamella._petname}----------------------------------------"
        )
        if lamella.state.stage == AutoLamellaWaffleStage.MillTrench:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1),
                parent_ui=parent_ui
            )

            lamella = mill_undercut(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)

        logging.info(
            "----------------------------------------------------------------------------------------"
        )
    return experiment

def run_lamella_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui=None,
) -> Experiment:


    stages = [
        AutoLamellaWaffleStage.SetupLamella,
        AutoLamellaWaffleStage.MillFeatures,
        AutoLamellaWaffleStage.MillRoughCut,
        AutoLamellaWaffleStage.MillRegularCut,
        AutoLamellaWaffleStage.MillPolishingCut,
    ]
    for stage in stages:
        for lamella in experiment.positions:
            logging.info(
                f"------------------------{lamella._petname}----------------------------------------"
            )
            if lamella.state.stage == AutoLamellaWaffleStage(stage.value - 1):
                lamella = start_of_stage_update(microscope, lamella, stage, parent_ui)
                print(f"---------------------stage: {stage.name}----------------------")
                lamella = WORKFLOW_STAGES[lamella.state.stage](microscope, settings, lamella, parent_ui)
                print(f'-------------------lamella protocol after stage  {lamella.protocol}')
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

                parent_ui.update_experiment_signal.emit(experiment)

            logging.info(
                "----------------------------------------------------------------------------------------"
            )

    # finish
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.MillPolishingCut:
            lamella.state.stage = AutoLamellaWaffleStage.Finished
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)
            parent_ui.update_experiment_signal.emit(experiment)

    return experiment


def _validate_mill_ui(microscope, settings, stages, parent_ui: AutoLamellaUI, msg, validate: bool):
    _update_mill_stages_ui(parent_ui, stages=stages)

    if validate:
        response = ask_user(parent_ui, msg=msg, pos="Continue", mill=True)
        stages = deepcopy(parent_ui.milling_widget.get_milling_stages())
    else:
        _update_status_ui(parent_ui, f"Milling {len(stages)} stages...")
        milling.mill_stages(
            microscope, settings, stages
        )  # TODO: make a ui version of this?
        _update_status_ui(
            parent_ui, f"Milling Complete: {len(stages)} stages completed."
        )

    parent_ui.WAITING_FOR_UI_UPDATE = True

    _update_mill_stages_ui(parent_ui, stages="clear")

    logging.info(f"WAITING FOR UI UPDATE... ")
    while parent_ui.WAITING_FOR_UI_UPDATE:
        time.sleep(0.5)

    return stages


# TODO: think this can be consolidated into mill arg for ask_user?
def _update_mill_stages_ui(
    parent_ui: AutoLamellaUI, stages: list[FibsemMillingStage] = None
):
    INFO = {
        "msg": "Updating Milling Stages",
        "pos": None,
        "neg": None,
        "det": None,
        "eb_image": None,
        "ib_image": None,
        "movement": None,
        "mill": None,
        "stages": stages,
    }

    parent_ui.ui_signal.emit(INFO)


def _validate_det_ui_v2(
    microscope, settings, features, parent_ui, validate: bool, msg: str = "Lamella"
) -> DetectedFeatures:
    feat_str = ", ".join([f.name for f in features])
    _update_status_ui(parent_ui, f"{msg}: Detecting Features ({feat_str})...")

    det = detection.take_image_and_detect_features(
        microscope=microscope,
        settings=settings,
        features=features,
    )

    if validate:
        ask_user(
            parent_ui,
            msg=f"Confirm Feature Detection. Press Continue to proceed.",
            pos="Continue",
            det=det,
        )

        det = parent_ui.det_widget._get_detected_features()

        # I need this to happen in the parent thread for it to work correctly
        parent_ui.det_confirm_signal.emit(True)

    return det


def _set_images_ui(
    parent_ui: AutoLamellaUI,
    eb_image: FibsemImage = None,
    ib_image: FibsemImage = None,
):
    INFO = {
        "msg": "Updating Images",
        "pos": None,
        "neg": None,
        "det": None,
        "eb_image": eb_image,
        "ib_image": ib_image,
        "movement": None,
        "mill": None,
    }
    parent_ui.ui_signal.emit(INFO)


def _update_status_ui(parent_ui: AutoLamellaUI, msg: str):
    INFO = {
        "msg": msg,
        "pos": None,
        "neg": None,
        "det": None,
        "eb_image": None,
        "ib_image": None,
        "movement": None,
        "mill": None,
    }
    parent_ui.ui_signal.emit(INFO)


def ask_user(
    parent_ui: AutoLamellaUI,
    msg: str,
    pos: str,
    neg: str = None,
    image: bool = True,
    movement: bool = True,
    mill: bool = None,
    det: DetectedFeatures = None,
) -> bool:
    INFO = {
        "msg": msg,
        "pos": pos,
        "neg": neg,
        "det": det,
        "eb_image": None,
        "ib_image": None,
        "movement": movement,
        "mill": mill,
    }
    parent_ui.ui_signal.emit(INFO)

    parent_ui.WAITING_FOR_USER_INTERACTION = True
    logging.info("WAITING_FOR_USER_INTERACTION...")
    while parent_ui.WAITING_FOR_USER_INTERACTION:
        time.sleep(1)
        # print("waiting for user interaction")

    INFO = {
        "msg": "",
        "pos": None,
        "neg": None,
        "det": None,
        "eb_image": None,
        "ib_image": None,
        "movement": None,
        "mill": None,
    }
    parent_ui.ui_signal.emit(INFO)

    return parent_ui.USER_RESPONSE

from fibsem import conversions

def _calculate_fiducial_area_v2(image: FibsemImage, fiducial_centre: Point, fiducial_length:float)->tuple[FibsemRectangle, bool]:
    pixelsize = image.metadata.pixel_size.x
    
    fiducial_centre.y = fiducial_centre.y * -1
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