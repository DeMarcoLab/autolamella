import logging
import time
from copy import deepcopy
from typing import List

from fibsem import milling
from fibsem.detection import detection
from fibsem.detection import utils as det_utils
from fibsem.detection.detection import DetectedFeatures, Feature
from fibsem.microscope import FibsemMicroscope
from fibsem.milling import FibsemMillingStage
from fibsem.structures import (
    FibsemImage,
    FibsemRectangle,
    FibsemStagePosition,
    ImageSettings,
)
from autolamella.ui import AutoLamellaUI
from autolamella.structures import Experiment

# CORE UI FUNCTIONS -> PROBS SEPARATE FILE
def _check_for_abort(parent_ui: AutoLamellaUI, msg: str = "Workflow aborted by user.") -> bool:
    # headless mode
    if parent_ui is None:
        return False

    if parent_ui.STOP_WORKFLOW:
        raise InterruptedError(msg)

def update_milling_ui(microscope: FibsemMicroscope, 
                      stages: List[FibsemMillingStage], 
                      parent_ui: AutoLamellaUI, 
                      msg:str, 
                      validate: bool, 
                      milling_enabled: bool = True):
    
    # headless mode
    if parent_ui is None:
        if milling_enabled:
            milling.mill_stages(microscope=microscope, stages=stages)
        return stages
    
    update_milling_stages_ui(parent_ui, stages=stages)

    pos, neg = "Run Milling", "Continue"

    # we only want the user to confirm the milling patterns, not acatually run them
    if milling_enabled is False:
        pos = "Continue"
        neg = None

    response = True
    if validate:
        response = ask_user(parent_ui, msg=msg, pos=pos, neg=neg, mill=milling_enabled)

    while response and milling_enabled:
        update_status_ui(parent_ui, f"Milling {len(stages)} stages...")
        parent_ui.MILLING_IS_RUNNING = True
        parent_ui.run_milling_signal.emit() # TODO: have the signal change the state, rather than here

        logging.info("WAITING FOR MILLING TO FINISH... ")
        while parent_ui.MILLING_IS_RUNNING or parent_ui.image_widget.ACQUIRING_IMAGES:
            time.sleep(1)

        update_status_ui(
           parent_ui, f"Milling Complete: {len(stages)} stages completed."
        )

        response = False
        if validate:
            response = ask_user(parent_ui, msg=msg, pos=pos, neg=neg, mill=milling_enabled)

    stages = deepcopy(parent_ui.milling_widget.get_milling_stages())

    update_milling_stages_ui(parent_ui, stages="clear")


    # if validate:
    #     response = ask_user(parent_ui, msg=msg, pos="Continue", mill=milling_enabled)
    #     stages = deepcopy(parent_ui.milling_widget.get_milling_stages())
    # else:
    #     update_status_ui(parent_ui, f"Milling {len(stages)} stages...") # TODO: better feedback here, change to milling tab for progress bar
    #     parent_ui.MILLING_IS_RUNNING = True
    #     parent_ui.run_milling_signal.emit()
        
    #     logging.info(f"WAITING FOR MILLING TO FINISH... ")
    #     while parent_ui.MILLING_IS_RUNNING or parent_ui.image_widget.ACQUIRING_IMAGES:
    #         time.sleep(1)
        
    #     update_status_ui(
    #         parent_ui, f"Milling Complete: {len(stages)} stages completed."
    #     )

    # update_milling_stages_ui(parent_ui, stages="clear")

    return stages


# TODO: think this can be consolidated into mill arg for ask_user?
def update_milling_stages_ui(
    parent_ui: AutoLamellaUI, stages: List[FibsemMillingStage] = None
):
    _check_for_abort(parent_ui)

    INFO = {
        "msg": "Updating Milling Stages",
        "stages": stages,
    }

    parent_ui.WAITING_FOR_UI_UPDATE = True
    parent_ui.workflow_update_signal.emit(INFO)
    logging.info("WAITING FOR UI UPDATE... ")
    while parent_ui.WAITING_FOR_UI_UPDATE:
        time.sleep(0.5)

def update_detection_ui(
    microscope: FibsemMicroscope, 
    image_settings: ImageSettings, # TODO: deprecate
    checkpoint: str,
    features: List[Feature], 
    parent_ui: AutoLamellaUI, validate: bool, 
    msg: str = "Lamella", position: FibsemStagePosition = None,
) -> DetectedFeatures:
    feat_str = ", ".join([f.name for f in features])
    if len(feat_str) > 15:
        feat_str = feat_str[:15] + "..."
    update_status_ui(parent_ui, f"{msg}: Detecting Features ({feat_str})...")

    det = detection.take_image_and_detect_features(
        microscope=microscope,
        image_settings=image_settings,
        features=features,
        point=position,
        checkpoint=checkpoint,
    )

    if validate and parent_ui is not None:
        ask_user(
            parent_ui,
            msg="Confirm Feature Detection. Press Continue to proceed.",
            pos="Continue",
            det=det,
        )

        det = parent_ui.det_widget._get_detected_features()

        # I need this to happen in the parent thread for it to work correctly
        parent_ui.detection_confirmed_signal.emit(True)

    else:
        det_utils.save_ml_feature_data(det)

    # TODO: set images in ui here
    return det


def set_images_ui(
    parent_ui: AutoLamellaUI,
    eb_image: FibsemImage = None,
    ib_image: FibsemImage = None,
):
    # headless mode
    if parent_ui is None:
        return
    
    _check_for_abort(parent_ui)

    INFO = {
        "msg": "Updating Images",
        "sem_image": eb_image,
        "fib_image": ib_image,

    }
    parent_ui.WAITING_FOR_UI_UPDATE = True
    parent_ui.workflow_update_signal.emit(INFO)

    logging.info("WAITING FOR UI UPDATE... ")
    while parent_ui.WAITING_FOR_UI_UPDATE:
        time.sleep(0.5)

def update_status_ui(parent_ui: AutoLamellaUI, msg: str, workflow_info: str = None) -> None:

    if parent_ui is None:
        logging.info(msg)
        return

    _check_for_abort(parent_ui)

    INFO = {
        "msg": msg,
        "workflow_info": workflow_info,
    }
    parent_ui.workflow_update_signal.emit(INFO)


def ask_user(
    parent_ui: AutoLamellaUI,
    msg: str,
    pos: str,
    neg: str = None,
    mill: bool = None,
    det: DetectedFeatures = None,
    correlate: bool = False,
) -> bool:

    if parent_ui is None:
        logging.warning(f"User input requested in headless mode: {msg}, always returning True.")
        return True

    INFO = {
        "msg": msg,
        "pos": pos,
        "neg": neg,
        "det": det,
        "milling_enabled": mill,
        "correlate": correlate,
    }
    parent_ui.workflow_update_signal.emit(INFO)

    parent_ui.WAITING_FOR_USER_INTERACTION = True
    logging.info("WAITING_FOR_USER_INTERACTION...")
    while parent_ui.WAITING_FOR_USER_INTERACTION:
        time.sleep(1)

    INFO = {
        "msg": "",
    }
    parent_ui.workflow_update_signal.emit(INFO) # clear the message

    return parent_ui.USER_RESPONSE

def ask_user_continue_workflow(parent_ui, msg: str = "Continue with the next stage?", validate: bool = True):

    ret = True
    if validate:
        ret = ask_user(parent_ui=parent_ui, msg=msg, pos="Continue", neg="Exit")
    return ret

def update_alignment_area_ui(alignment_area: FibsemRectangle, parent_ui: AutoLamellaUI, 
        msg: str = "Edit Alignment Area", validate: bool = True) -> FibsemRectangle:
    """ Update the alignment area in the UI and return the updated alignment area."""
    
    _check_for_abort(parent_ui)

    # headless mode, return the alignment area   
    if parent_ui is None or not validate:
        return alignment_area

    INFO = {
        "msg": msg,
        "pos": "Continue",
        "alignment_area": alignment_area,
    }
    parent_ui.workflow_update_signal.emit(INFO)

    parent_ui.WAITING_FOR_USER_INTERACTION = True
    logging.info("WAITING_FOR_USER_INTERACTION...")
    while parent_ui.WAITING_FOR_USER_INTERACTION:
        time.sleep(1)

    _check_for_abort(parent_ui)

    INFO = {
        "msg": "Clearing Alignment Area",
        "alignment_area": "clear",
    }

    parent_ui.WAITING_FOR_UI_UPDATE = True
    parent_ui.workflow_update_signal.emit(INFO)
    logging.info("WAITING FOR UI UPDATE... ")
    while parent_ui.WAITING_FOR_UI_UPDATE:
        time.sleep(0.5)

    # retrieve the updated alignment area
    alignment_area = deepcopy(parent_ui.image_widget.get_alignment_area())

    return alignment_area

def update_experiment_ui(parent_ui: AutoLamellaUI, experiment: Experiment) -> None:
    
    # headless mode
    if parent_ui is None:
        return

    parent_ui.update_experiment_signal.emit(deepcopy(experiment))


def ask_user_to_correlate(parent_ui: AutoLamellaUI, validate: bool = True):

    # headless mode
    if parent_ui is None:
        return 

    msg = "Use Fluorescence Correlation? Press Continue when done."
    pos, neg = "Correlate", "Skip"

    if validate: # correlation must be validated
        response = ask_user(parent_ui, msg=msg, pos=pos, neg=neg)
        if response:
            response = ask_user(parent_ui, msg="Press Continue when finished correlating.", 
                                pos="Continue", 
                                correlate=True)

            poi = None
            try:
                poi = parent_ui.correlation_widget.poi_coordinate 
            except Exception as e:
                logging.warning(f"Correlation results not found in UI. {e}")

            # close the correlation widget
            parent_ui.correlation_widget_signal.emit({"finished": True})

            return poi
