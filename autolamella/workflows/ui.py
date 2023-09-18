import logging
from copy import deepcopy

from fibsem.patterning import FibsemMillingStage
from fibsem.structures import (
    FibsemStagePosition,
    FibsemImage,
)
import time

from fibsem.detection import detection
from fibsem.detection.detection import DetectedFeatures
from autolamella.ui.AutoLamellaUI import AutoLamellaUI



# CORE UI FUNCTIONS -> PROBS SEPARATE FILE

def _validate_mill_ui(stages: list[FibsemMillingStage], parent_ui: AutoLamellaUI, msg, validate: bool,milling_enabled: bool = True):
    _update_mill_stages_ui(parent_ui, stages=stages)

    if validate:
        response = ask_user(parent_ui, msg=msg, pos="Continue", mill=milling_enabled)
        stages = deepcopy(parent_ui.milling_widget.get_milling_stages())
    else:
        _update_status_ui(parent_ui, f"Milling {len(stages)} stages...")
        parent_ui._MILLING_RUNNING = True
        parent_ui._run_milling_signal.emit()
        
        logging.info(f"WAITING FOR MILLING TO FINISH... ")
        while parent_ui._MILLING_RUNNING or parent_ui.image_widget.TAKING_IMAGES:
            time.sleep(1)
        
        _update_status_ui(
            parent_ui, f"Milling Complete: {len(stages)} stages completed."
        )

    _update_mill_stages_ui(parent_ui, stages="clear")

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

    parent_ui.WAITING_FOR_UI_UPDATE = True
    parent_ui.ui_signal.emit(INFO)
    logging.info(f"WAITING FOR UI UPDATE... ")
    while parent_ui.WAITING_FOR_UI_UPDATE:
        time.sleep(0.5)

def _validate_det_ui_v2(
    microscope, settings, features, parent_ui, validate: bool, msg: str = "Lamella", position: FibsemStagePosition = None,
) -> DetectedFeatures:
    feat_str = ", ".join([f.name for f in features])
    _update_status_ui(parent_ui, f"{msg}: Detecting Features ({feat_str})...")

    det = detection.take_image_and_detect_features(
        microscope=microscope,
        settings=settings,
        features=features,
        point=position,
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
