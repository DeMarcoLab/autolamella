import logging
import time
from copy import deepcopy

from fibsem.detection import detection
from fibsem.detection.detection import DetectedFeatures
from fibsem.patterning import FibsemMillingStage
from fibsem.structures import FibsemImage, FibsemStagePosition

from autolamella.structures import (
    AutoLamellaWaffleStage,
    Experiment,
    Lamella,
)

from autolamella.ui.AutoLamellaUI import AutoLamellaUI


from fibsem import acquire, calibration, patterning
from fibsem.structures import Point, BeamType, MicroscopeSettings
from fibsem.microscope import FibsemMicroscope
from fibsem import config as fcfg


import logging
import os
from copy import deepcopy
from datetime import datetime

import numpy as np
from fibsem import acquire, patterning,  calibration, alignment
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
    LamellaTopEdge,
    LamellaBottomEdge,
    detect_features,
    DetectedFeatures,
)
from autolamella.ui.AutoLamellaUI import AutoLamellaUI
from fibsem import config as fcfg

from autolamella.workflows.ui import (_set_images_ui, _update_status_ui, _validate_det_ui_v2, _validate_mill_ui)


# CORE WORKFLOW STEPS
def log_status_message(lamella: Lamella, step: str):
    logging.debug(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | {step}")

# mill trench
def mill_trench(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("trench", True)
    settings.image.save_path = lamella.path
    
    log_status_message(lamella, "MILL_TRENCH")

    settings.image.hfw = lamella.protocol["trench"]["stages"][0]["hfw"]
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    _update_status_ui(parent_ui, f"{lamella.info} Preparing Trench...")
    
    # define trench milling stage
    settings.image.beam_type = BeamType.ION
    stages = patterning._get_milling_stages("trench", lamella.protocol, point=Point.__from_dict__(lamella.protocol["trench"]["point"]))
    stages = _validate_mill_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
    
    # log the protocol
    lamella.protocol["trench"] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol["trench"]["point"] = stages[0].pattern.point.__to_dict__()
    
    # charge neutralisation
    log_status_message(lamella, "CHARGE_NEUTRALISATION")
    _update_status_ui(parent_ui, f"{lamella.info} Neutralising Sample Charge...")
    settings.image.beam_type = BeamType.ELECTRON
    calibration.auto_charge_neutralisation(microscope, settings.image)
    
    # refernce images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella

# mill undercut
def mill_undercut(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("undercut", True)
    settings.image.save_path = lamella.path

    # optional undercut
    _complete_undercut = settings.protocol["options"].get("complete_undercut", True)
    if _complete_undercut is False:
        logging.info("Skipping undercut")
        return lamella

    # rotate flat to eb
    log_status_message(lamella, "MOVE_TO_UNDERCUT")
    _update_status_ui(parent_ui, f"{lamella.info} Moving to Undercut Position...")
    microscope.move_flat_to_beam(settings, BeamType.ELECTRON, _safe=True) # TODO: TEST UNSAFE MOVE
    
    # OFFSET FOR COMPUCENTRIC ROTATION
    X_OFFSET = settings.protocol["options"].get("compucentric_x_offset", 0)
    Y_OFFSET = settings.protocol["options"].get("compucentric_y_offset", 0)
    microscope.stable_move(settings, dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)
    

    # detect
    log_status_message(lamella, f"ALIGN_TRENCH")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Trench (Rotated)...")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_trench_align_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    
    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.absolute_position)

    microscope.stable_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )
    
    # Align ion so it is coincident with the electron beam
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.absolute_position)
    
    # align vertical
    microscope.vertical_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )

    # lamella should now be centred in ion beam

    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    method = settings.protocol.get("method", "autolamella-waffle")
    lamella.protocol["undercut"] = deepcopy(settings.protocol["undercut"])
    N_UNDERCUTS = int(lamella.protocol["undercut"].get("tilt_angle_step", 1))
    UNDERCUT_ANGLE_DEG = lamella.protocol["undercut"].get("tilt_angle", -5)
    _UNDERCUT_V_OFFSET = lamella.protocol["undercut"].get("v_offset", 0e-6)
    undercut_stages = []

    for i in range(N_UNDERCUTS):

        _n = f"{i+1:02d}" # helper

        # tilt down, align to trench
        log_status_message(lamella, f"TILT_UNDERCUT_{_n}")
        _update_status_ui(parent_ui, f"{lamella.info} Tilting to Undercut Position...")
        microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(UNDERCUT_ANGLE_DEG)))

        # detect
        log_status_message(lamella, f"ALIGN_UNDERCUT_{_n}")
        settings.image.beam_type = BeamType.ION
        settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
        settings.image.label = f"ref_{lamella.state.stage.name}_align_ml_{_n}"
        settings.image.save = True
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        _set_images_ui(parent_ui, eb_image, ib_image)

        # get pattern
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge()]

        det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # move pattern
        if i > 0: # reduce the undercut height by half each time
            lamella.protocol["undercut"]["height"] /= 2

        
        if method == "autoliftout-default":
            offset = lamella.protocol["undercut"].get("trench_width", 2e-6) / 2 + _UNDERCUT_V_OFFSET
        else:         
            offset = lamella.protocol["undercut"].get("height", 10) / 2 + _UNDERCUT_V_OFFSET
        point = deepcopy(det.features[0].feature_m)     
        point.y += offset if np.isclose(scan_rotation, 0) else -offset

        # mill undercut 1
        log_status_message(lamella, f"MILL_UNDERCUT_{_n}")

        stages = patterning._get_milling_stages("undercut", lamella.protocol, point=point)
        stages = _validate_mill_ui(stages, parent_ui,
            msg=f"Press Run Milling to mill the Undercut {_n} for {lamella._petname}. Press Continue when done.",
            validate=validate,
        )
        
        undercut_stages.append(stages[0])

    # log undercut stages
    lamella.protocol["undercut"] = deepcopy(patterning._get_protocol_from_stages(undercut_stages))
    lamella.protocol["undercut"]["point"] = undercut_stages[0].pattern.point.__to_dict__()

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.label=f"ref_{lamella.state.stage.name}_undercut"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # optional return flat to electron beam (autoliftout)
    if settings.protocol["options"].get("return_to_eb_after_undercut", False):
        microscope.move_flat_to_beam(settings, BeamType.ELECTRON, _safe=True)

    log_status_message(lamella, "ALIGN_FINAL")

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
    
    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

def mill_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("lamella", True)
    settings.image.save_path = lamella.path
    method = settings.protocol.get("method", "autolamella-waffle")


    supervise_map = {
        AutoLamellaWaffleStage.MillRoughCut.name: "mill_rough",
        AutoLamellaWaffleStage.MillPolishingCut.name: "mill_polishing",
    }
    validate = settings.protocol["options"]["supervise"].get(supervise_map[lamella.state.stage.name], True)
    
    _align_at_milling_current = bool(settings.protocol["options"].get("alignment_at_milling_current", True))
    _take_reference_images = bool(
        lamella.state.stage is AutoLamellaWaffleStage.MillRoughCut 
        or settings.protocol["options"].get("take_final_reference_images", True))
    _take_high_quality_ref =  bool(
        lamella.state.stage is AutoLamellaWaffleStage.MillPolishingCut 
        and settings.protocol["options"].get("take_final_high_quality_reference_images", False)
        )

    # milling stages
    stages = patterning._get_milling_stages("lamella", lamella.protocol, 
                    point=Point.__from_dict__(lamella.protocol["lamella"]["point"]))

    if lamella.state.stage.name == AutoLamellaWaffleStage.MillPolishingCut.name:
        stages = stages[-1]
    else:
        stages = stages[:-1]

    if not isinstance(stages, list):
        stages = [stages]

    # beam_shift alignment
    log_status_message(lamella, "ALIGN_LAMELLA")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Reference Images...")

    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.beam_type = BeamType.ION
    ref_image = FibsemImage.load(os.path.join(lamella.path, f"ref_alignment_ib.tif"))
    _ALIGNMENT_ATTEMPTS = int(settings.protocol["options"].get("alignment_attempts", 1))

    # beam alignment
    alignment_current = stages[0].milling.milling_current if _align_at_milling_current else None
    settings.image.label = f"alignment_target_{lamella.state.stage.name}"
    alignment._multi_step_alignment(microscope=microscope, 
        image_settings=settings.image, 
        ref_image=ref_image, 
        reduced_area=lamella.fiducial_area, 
        alignment_current=alignment_current, 
        steps=_ALIGNMENT_ATTEMPTS)

    settings.image.reduced_area = None

    # take reference images
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)


    # define feature
    _MILL_FEATURES = bool("autolamella" in method)
    if _MILL_FEATURES and lamella.state.stage.name == AutoLamellaWaffleStage.MillRoughCut.name:
        log_status_message(lamella, "MILL_FEATURE")

        # check if using notch or microexpansion
        _feature_name = "notch" if method == "autolamella-waffle" else "microexpansion"

        feature_stages = patterning._get_milling_stages(
            _feature_name, lamella.protocol, point=Point.__from_dict__(lamella.protocol[_feature_name]["point"])
        )

        feature_stages = _validate_mill_ui(feature_stages, parent_ui,
            msg=f"Press Run Milling to mill the {_feature_name} for {lamella._petname}. Press Continue when done.",
            validate=validate,
        )

        # log feature stages
        lamella.protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(feature_stages))
        lamella.protocol[_feature_name]["point"] = feature_stages[0].pattern.point.__to_dict__()

    # mill lamella trenches
    log_status_message(lamella, "MILL_LAMELLA")

    stages = _validate_mill_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the Trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
   
    # TODO: refactor this so it is like the original protocol
    lamella.protocol[lamella.state.stage.name] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol[lamella.state.stage.name]["point"] = stages[0].pattern.point.__to_dict__()

    if _take_reference_images:
        # take reference images
        log_status_message(lamella, "REFERENCE_IMAGES")
        _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
        reference_images = acquire.take_set_of_reference_images(
            microscope=microscope,
            image_settings=settings.image,
            hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
            label=f"ref_{lamella.state.stage.name}_final",
        )
        _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    if _take_high_quality_ref:
        log_status_message(lamella, "HIGH_QUALITY_REFERENCE_IMAGES")
        _update_status_ui(parent_ui, f"{lamella.info} Acquiring High Quality Reference Images...")
        settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
        settings.image.label = f"ref_{lamella.state.stage.name}_final_ultra"
        settings.image.save = True
        settings.image.resolution = fcfg.REFERENCE_RES_HIGH
        settings.image.frame_integration = 4
        settings.image.beam_type = BeamType.ELECTRON
        eb_image = acquire.new_image(microscope, settings.image)
        # _set_images_ui(parent_ui, eb_image, ib_image)
        settings.image.frame_integration = 1 # restore
        settings.image.resolution = fcfg.REFERENCE_RES_MEDIUM


    return lamella


def setup_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("setup_lamella", True)
    settings.image.save_path = lamella.path
    method = settings.protocol.get("method", "autolamella-waffle")


    log_status_message(lamella, "ALIGN_LAMELLA")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Lamella...")

    if method == "autoliftout-default":
        from autolamella.liftout import actions

        actions.move_to_lamella_angle(microscope, settings.protocol)
        # OFFSET FOR COMPUCENTRIC ROTATION
        X_OFFSET = settings.protocol["options"].get("compucentric_x_offset", 0)
        Y_OFFSET = settings.protocol["options"].get("compucentric_y_offset", 0)
        microscope.stable_move(settings, dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)

    if method != "autolamella-default":
        lamella = _align_lamella_coincident(microscope, settings, lamella, parent_ui, validate)

    log_status_message(lamella, "SETUP_PATTERNS")
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

   
    # load the default protocol unless in lamella protocol
    protocol = lamella.protocol if "lamella" in lamella.protocol else settings.protocol
    lamella_position = Point.__from_dict__(protocol["lamella"].get("point", {"x": 0, "y": 0})) 
    lamella_stages = patterning._get_milling_stages("lamella", protocol, lamella_position)
    stages = deepcopy(lamella_stages)

    # feature 
    if "autolamella" in method:
        _feature_name = "notch" if method == "autolamella-waffle" else "microexpansion"
        protocol = lamella.protocol if _feature_name in lamella.protocol else settings.protocol
        NOTCH_H_OFFSET = 0.5e-6                     
        feature_position = Point.__from_dict__(protocol[_feature_name].get("point", 
                {"x":lamella_position.x + stages[0].pattern.protocol["lamella_width"] / 2 + NOTCH_H_OFFSET, 
                "y": lamella_position.y} if _feature_name == "notch" else {"x": 0, "y": 0})) 
        feature_stage = patterning._get_milling_stages(_feature_name, protocol, feature_position)
        stages += feature_stage

    # fiducial
    protocol = lamella.protocol if "fiducial" in lamella.protocol else settings.protocol
    FIDUCIAL_X_OFFSET = 25e-6
    if method == "autoliftout-default":
        FIDUCIAL_X_OFFSET *= -1
    fiducial_position = Point.__from_dict__(protocol["fiducial"].get("point", {"x": FIDUCIAL_X_OFFSET, "y": 0}))
    fiducial_stage = patterning._get_milling_stages("fiducial", protocol, fiducial_position)
    stages += fiducial_stage
    
    if validate:
        stages =_validate_mill_ui(stages, parent_ui, 
            msg=f"Confirm the positions for the {lamella._petname} milling. Press Continue to Confirm.",
            validate=True, # always validate, until we fix milling issue
            milling_enabled=False)
       
    from pprint import pprint
    print("-"*80) 
    pprint(stages)
    print("-"*80)

    # lamella
    n_lamella = len(lamella_stages)
    lamella.protocol["lamella"] = deepcopy(patterning._get_protocol_from_stages(stages[:n_lamella]))
    lamella.protocol["lamella"]["point"] = stages[0].pattern.point.__to_dict__()

#     # TODO: integrate this style
#     # lamella.protocol[AutoLamellaWaffleStage.MillRoughCut.name] = deepcopy(patterning._get_protocol_from_stages(stages[0]))
#     # lamella.protocol[AutoLamellaWaffleStage.MillRoughCut.name]["point"] = stages[0].pattern.point.__to_dict__()
#     # lamella.protocol[AutoLamellaWaffleStage.MillPolishingCut.name] = deepcopy(patterning._get_protocol_from_stages(stages[2]))
#     # lamella.protocol[AutoLamellaWaffleStage.MillPolishingCut.name]["point"] = stages[2].pattern.point.__to_dict__()

    # feature
    if "autolamella" in method:
        n_features = len(feature_stage)
        lamella.protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(stages[n_lamella:n_lamella+n_features]))
        lamella.protocol[_feature_name]["point"] = stages[n_lamella].pattern.point.__to_dict__()

    # fiducial
    # save fiducial information
    n_fiducial = len(fiducial_stage)
    lamella.protocol["fiducial"] = deepcopy(patterning._get_protocol_from_stages(stages[-n_fiducial:]))
    lamella.protocol["fiducial"]["point"] = stages[-n_fiducial].pattern.point.__to_dict__()
    lamella.fiducial_area, _  = _calculate_fiducial_area_v2(ib_image, 
        deepcopy(stages[-n_fiducial].pattern.point), 
        lamella.protocol["fiducial"]["stages"][0]["height"])

    # mill the fiducial
    fiducial_stage = patterning._get_milling_stages("fiducial", lamella.protocol, Point.__from_dict__(lamella.protocol["fiducial"]["point"]))
    stages =_validate_mill_ui(fiducial_stage, parent_ui, 
        msg=f"Press Run Milling to mill the fiducial for {lamella._petname}. Press Continue when done.", 
        validate=validate)

    # set reduced area for fiducial alignment
    settings.image.reduced_area = lamella.fiducial_area
    print(f"REDUCED_AREA: ", lamella.fiducial_area)

    
    # for alignment
    settings.image.beam_type = BeamType.ION
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_alignment"
    print(f"REDUCED_AREA: ", settings.image.reduced_area)
    ib_image = acquire.new_image(microscope, settings.image)
    settings.image.reduced_area = None
    
    log_status_message(lamella, "REFERENCE_IMAGES")
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    # # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella


def end_of_stage_update(
    microscope: FibsemMicroscope, experiment: Experiment, lamella: Lamella, parent_ui: AutoLamellaUI, _save_state: bool = True,
) -> Experiment:
    """Save the current microscope state configuration to disk, and log that the stage has been completed."""

    # save state information
    if _save_state:
        lamella.state.microscope_state = microscope.get_current_microscope_state()
    lamella.state.end_timestamp = datetime.timestamp(datetime.now())

    # write history
    lamella.history.append(deepcopy(lamella.state))

    # # update and save experiment
    experiment.save()

    log_status_message(lamella, "FINISHED")
    _update_status_ui(parent_ui, f"{lamella.info} Finished")

    return experiment


def start_of_stage_update(
    microscope: FibsemMicroscope,
    lamella: Lamella,
    next_stage: AutoLamellaWaffleStage,
    parent_ui: AutoLamellaUI, 
    _restore_state: bool = True,
) -> Lamella:
    """Check the last completed stage and reload the microscope state if required. Log that the stage has started."""
    last_completed_stage = lamella.state.stage

    # restore to the last state
    if last_completed_stage.value == next_stage.value - 1 and _restore_state:
        logging.info(
            f"{lamella._petname} restarting from end of stage: {last_completed_stage.name}"
        )
        _update_status_ui(parent_ui, f"{lamella.info} Restoring Last State...")
        microscope.set_microscope_state(lamella.state.microscope_state)

    # set current state information
    lamella.state.stage = deepcopy(next_stage)
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    log_status_message(lamella, "STARTED")
    _update_status_ui(parent_ui, f"{lamella.info} Starting...")

    return lamella

# TODO: move to fibsem
from fibsem import conversions
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

def _align_lamella_coincident(microscope: FibsemMicroscope, settings: MicroscopeSettings, lamella: Lamella, parent_ui: AutoLamellaUI, validate: bool, hfw: float = fcfg.REFERENCE_HFW_MEDIUM) -> Lamella:
    """Align the lamella in the electron and ion beams"""

    # update status
    log_status_message(lamella, f"ALIGN_TRENCH")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Trench (Rotated)...")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_trench_align_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    # detect
    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.absolute_position)

    microscope.stable_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )

    # Align ion so it is coincident with the electron beam
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.absolute_position)
    
    # align vertical
    microscope.vertical_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )

    return lamella
