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
    Point,
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

    _update_status_ui(parent_ui, f"{lamella.info} Preparing Trench...")

    # define trench
    settings.protocol["trench"]["cleaning_cross_section"] = False
    stages = patterning._get_milling_stages("trench", settings.protocol, point=lamella.trench_centre)
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
    microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(10)))

    # detect
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_trench_align_ml_01"
    settings.image.save = True
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
    microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(10)))
    
    # detect
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.label = f"ref_trench_align_ml_02"
    settings.image.save = True

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

def mill_notch(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui=None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("notch", True)
    settings.image.save_path = lamella.path

    # TODO: cross correlate the reference here
    # fname = os.path.join(lamella.path, "ref_position_lamella_ib.tif")
    # img = FibsemImage.load(fname)

    _update_status_ui(parent_ui, f"{lamella.info} Preparing Notch...")

    # define notch
    stages = patterning._get_milling_stages(
        "notch", settings.protocol, point=lamella.notch_centre
    )
    _validate_mill_ui(microscope, settings, stages, parent_ui,
        msg=f"Press Run Milling to mill the Notch for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
    # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_SUPER],
        label="ref_notch",
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

    # define notch
    stages = patterning._get_milling_stages(
        "lamella", settings.protocol, point=lamella.lamella_centre
    )

    # filter stage based on the current stage
    stage_map = {
        AutoLamellaWaffleStage.MillRoughCut: 0,
        AutoLamellaWaffleStage.MillRegularCut: 1,
        AutoLamellaWaffleStage.MillPolishingCut: 2,
    }
    idx = stage_map[lamella.state.stage]
    stages = [stages[idx]]

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


def end_of_stage_update(
    microscope: FibsemMicroscope, experiment: Experiment, lamella: Lamella
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

    return experiment


def start_of_stage_update(
    microscope: FibsemMicroscope,
    lamella: Lamella,
    next_stage: AutoLamellaStage,
) -> Lamella:
    """Check the last completed stage and reload the microscope state if required. Log that the stage has started."""
    last_completed_stage = lamella.state.stage

    # restore to the last state
    if last_completed_stage.value == next_stage.value - 1:
        logging.info(
            f"{lamella._petname} restarting from end of stage: {last_completed_stage.name}"
        )
        microscope.set_microscope_state(lamella.state.microscope_state)

    # set current state information
    lamella.state.stage = next_stage
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    logging.info(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | STARTED")

    return lamella


WORKFLOW_STAGES = {
    AutoLamellaWaffleStage.MillTrench: mill_trench,
    AutoLamellaWaffleStage.MillUndercut: mill_undercut,
    AutoLamellaWaffleStage.MillFeatures: mill_notch,
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
            )

            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella)

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
            )

            lamella = mill_undercut(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella)

            parent_ui.update_experiment_signal.emit(experiment)

        logging.info(
            "----------------------------------------------------------------------------------------"
        )
    return experiment


def run_notch_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui=None,
) -> Experiment:
    for lamella in experiment.positions:
        logging.info(
            f"------------------------{lamella._petname}----------------------------------------"
        )
        if lamella.state.stage == AutoLamellaWaffleStage.MillUndercut:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1),
            )

            lamella = mill_notch(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella)

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
                lamella = start_of_stage_update(microscope, lamella, stage)

                lamella = mill_lamella(microscope, settings, lamella, parent_ui)

                experiment = end_of_stage_update(microscope, experiment, lamella)

                parent_ui.update_experiment_signal.emit(experiment)

            logging.info(
                "----------------------------------------------------------------------------------------"
            )
    return experiment


def _validate_mill_ui(microscope, settings, stages, parent_ui, msg, validate: bool):
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

    _update_mill_stages_ui(parent_ui, stages="clear")


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
