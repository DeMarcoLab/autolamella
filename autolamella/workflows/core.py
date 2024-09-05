import logging
import time
from copy import deepcopy

from fibsem.structures import ImageSettings

from autolamella.structures import (
    AutoLamellaWaffleStage,
    Experiment,
    Lamella,
)

from autolamella.ui.AutoLamellaUI import AutoLamellaUI

import os
from datetime import datetime

import numpy as np
from fibsem import acquire, patterning,  calibration, alignment
from fibsem.microscope import FibsemMicroscope
from fibsem.structures import (
    BeamType,
    FibsemStagePosition,
    FibsemImage,
    MicroscopeSettings,
    Point, FibsemRectangle
)

from fibsem.detection import detection
from fibsem.detection.detection import (
    Feature,
    ImageCentre,
    LamellaCentre,
    LamellaLeftEdge,
    LamellaRightEdge,
    LamellaTopEdge,
    LamellaBottomEdge,
    detect_features,
    DetectedFeatures,
    VolumeBlockCentre
)
from autolamella.ui.AutoLamellaUI import AutoLamellaUI
from fibsem import config as fcfg
from autolamella.workflows import actions
from autolamella.workflows.ui import (set_images_ui, update_status_ui, 
                                      update_detection_ui, update_milling_ui, 
                                      ask_user, update_alignment_area_ui)


# DEFAULTS, TODO: move to a configuration file
DEFAULT_ALIGNMENT_AREA = {"left": 0.25, "top": 0.25, "width": 0.5, "height": 0.5}
DEFAULT_FIDUCIAL_PROTOCOL = {
    "height": 10.e-6,
    "width": 1.e-6,
    "depth": 1.0e-6,
    "rotation": 45,
    "milling_current": 2.0e-9,
    "preset": "30 keV; 20 nA", # TESCAN only
    "application_file": "Si",
    "passes": None,
    "hfw": 80.e-6,
    "type": "Fiducial",
    }
# TODO: complete the rest of the patterns

# CORE WORKFLOW STEPS
def log_status_message(lamella: Lamella, step: str):
    logging.debug({"msg": "status", "petname": lamella._petname, "stage": lamella.state.stage.name, "step": step})

def log_status_message_raw(stage: str, step: str, petname: str = "null"):
    logging.debug({"msg": "status", "petname": petname, stage: stage, "step": step })   


def pass_through_stage(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    # pass through stage
    return lamella 

# mill trench
def mill_trench(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("trench", True)
    settings.image.path = lamella.path

    log_status_message(lamella, "MOVE_TO_TRENCH")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Trench Position...")
    microscope.move_flat_to_beam(BeamType.ION)
    
    log_status_message(lamella, "MILL_TRENCH")

    if "stages" in lamella.protocol["trench"]:
      hfw = lamella.protocol["trench"]["stages"][0]["hfw"]
    else:
        hfw = lamella.protocol["trench"]["hfw"]
    settings.image.hfw = hfw
    settings.image.filename = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)
    update_status_ui(parent_ui, f"{lamella.info} Preparing Trench...")
    
    # define trench milling stage
    settings.image.beam_type = BeamType.ION
    stages = patterning.get_milling_stages("trench", 
                                           lamella.protocol, 
                                           point=Point.from_dict(lamella.protocol["trench"].get("point", {"x":0, "y":0})))
    stages = update_milling_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
    
    # log the protocol
    lamella.protocol["trench"] = deepcopy(patterning.get_protocol_from_stages(stages))
    lamella.protocol["trench"]["point"] = stages[0].pattern.point.to_dict()
    
    # charge neutralisation
    log_status_message(lamella, "CHARGE_NEUTRALISATION")
    update_status_ui(parent_ui, f"{lamella.info} Neutralising Sample Charge...")
    settings.image.beam_type = BeamType.ELECTRON
    calibration.auto_charge_neutralisation(microscope, settings.image)
    
    # reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.state.stage.name}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella

# mill undercut
def mill_undercut(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("undercut", True)
    settings.image.path = lamella.path

    # optional undercut
    _undercut_required = settings.protocol["options"].get("undercut_required", True)
    if _undercut_required is False:
        logging.info("Skipping undercut")
        return lamella

    # rotate flat to eb
    log_status_message(lamella, "MOVE_TO_UNDERCUT")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Undercut Position...")
    microscope.move_flat_to_beam(BeamType.ELECTRON, _safe=True)
    
    # OFFSET FOR COMPUCENTRIC ROTATION
    X_OFFSET = settings.protocol["options"].get("compucentric_x_offset", 0)
    Y_OFFSET = settings.protocol["options"].get("compucentric_y_offset", 0)
    microscope.stable_move(dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)
    
    # align feature coincident
    method = settings.protocol["options"].get("method", "autolamella-waffle")
    
    if method == "autolamella-serial-liftout":
        feature = VolumeBlockCentre()
    else: # autolamella-waffle, autolamella-liftout
        feature = LamellaCentre()

    lamella = align_feature_coincident(microscope=microscope,
                                       settings=settings,
                                       lamella=lamella,
                                       parent_ui=parent_ui,
                                       validate=validate,
                                       feature=feature)
    
    # mill under cut
    lamella.protocol["undercut"] = deepcopy(settings.protocol["milling"]["undercut"])

    # coerce old protocol into new
    if "stages" not in lamella.protocol["undercut"]:
        lamella.protocol["undercut"] = deepcopy({"stages": [lamella.protocol["undercut"]]})
    N_UNDERCUTS = len(lamella.protocol["undercut"]["stages"])

    UNDERCUT_ANGLE_DEG = settings.protocol["options"].get("undercut_tilt_angle", -5)
    _UNDERCUT_V_OFFSET = lamella.protocol["undercut"].get("v_offset", 0e-6)
    undercut_stages = []
    try:
        hfw = lamella.protocol["undercut"]["stages"][0].get("hfw", fcfg.REFERENCE_HFW_HIGH)
    except:
        logging.warning("No hfw found in undercut protocol, using default")
        hfw = fcfg.REFERENCE_HFW_HIGH

    for i in range(N_UNDERCUTS):

        _n = f"{i+1:02d}" # helper

        # tilt down, align to trench
        log_status_message(lamella, f"TILT_UNDERCUT_{_n}")
        update_status_ui(parent_ui, f"{lamella.info} Tilting to Undercut Position...")
        microscope.move_stage_relative(FibsemStagePosition(t=np.deg2rad(UNDERCUT_ANGLE_DEG)))

        # detect
        log_status_message(lamella, f"ALIGN_UNDERCUT_{_n}")
        settings.image.beam_type = BeamType.ION
        settings.image.hfw = hfw
        settings.image.filename = f"ref_{lamella.state.stage.name}_align_ml_{_n}"
        settings.image.save = True
        eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
        set_images_ui(parent_ui, eb_image, ib_image)

        # get pattern
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge()]

        det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)

        # # move pattern
        # if i > 0: # reduce the undercut height by half each time
        #     lamella.protocol["undercut"]["height"] /= 2

        if method == "autolamella-liftout":
            offset = lamella.protocol["undercut"]["stages"][i].get("trench_width", 2e-6) / 2 + _UNDERCUT_V_OFFSET
        else:         
            offset = lamella.protocol["undercut"]["stages"][i].get("height", 10) / 2 + _UNDERCUT_V_OFFSET
        point = deepcopy(det.features[0].feature_m)     
        point.y += offset if np.isclose(scan_rotation, 0) else -offset

        # mill undercut 1
        log_status_message(lamella, f"MILL_UNDERCUT_{_n}")

        stages = patterning.get_milling_stages("undercut", lamella.protocol, point=point)[i]
        stages = update_milling_ui([stages], parent_ui,
            msg=f"Press Run Milling to mill the Undercut {_n} for {lamella._petname}. Press Continue when done.",
            validate=validate,
        )
        
        undercut_stages.append(stages[0])

    # log undercut stages
    lamella.protocol["undercut"] = deepcopy(patterning.get_protocol_from_stages(undercut_stages))
    lamella.protocol["undercut"]["point"] = undercut_stages[0].pattern.point.to_dict()

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH
    settings.image.save = True
    settings.image.filename=f"ref_{lamella.state.stage.name}_undercut"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # optional return flat to electron beam (autoliftout)
    if settings.protocol["options"].get("undercut_return_to_electron", False):
        microscope.move_flat_to_beam(BeamType.ELECTRON, _safe=True)

    log_status_message(lamella, "ALIGN_FINAL")

    settings.image.beam_type = BeamType.ION
    settings.image.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaCentre()] 
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    
    # align vertical
    microscope.vertical_move(
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )
    
    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.state.stage.name}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

def mill_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("lamella", True)
    settings.image.path = lamella.path
    method = settings.protocol["options"].get("method", "autolamella-waffle")


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
        and settings.protocol["options"].get("high_quality_image", {}).get("enabled", False)
        )

    # milling stages
    stages = patterning.get_milling_stages("lamella", lamella.protocol, 
                    point=Point.from_dict(lamella.protocol["lamella"]["point"]))

    num_polishing_stages = settings.protocol["options"].get("num_polishing_stages", 1)
    if lamella.state.stage.name == AutoLamellaWaffleStage.MillPolishingCut.name:
        stages = stages[-num_polishing_stages:]
    else:
        stages = stages[:-num_polishing_stages]

    if not isinstance(stages, list):
        stages = [stages]

    n_lamella = len(stages) # number of lamella stages

    # beam_shift alignment #TODO: clean up this execution, bit messy and redundant
    log_status_message(lamella, "ALIGN_LAMELLA")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Reference Images...")

    settings.image.save = True
    settings.image.hfw = stages[0].milling.hfw # fcfg.REFERENCE_HFW_SUPER
    settings.image.beam_type = BeamType.ION
    ref_image = FibsemImage.load(os.path.join(lamella.path, f"ref_alignment_ib.tif"))
    _ALIGNMENT_ATTEMPTS = int(settings.protocol["options"].get("alignment_attempts", 1))

    # beam alignment
    alignment_current = stages[0].milling.milling_current if _align_at_milling_current else None
    
    ### REPLACE WITH V2
    from autolamella.config import USE_BEAM_SHIFT_ALIGNMENT_V2
    if USE_BEAM_SHIFT_ALIGNMENT_V2:
        # V2
        alignment.multi_step_alignment_v2(microscope=microscope, 
                                        ref_image=ref_image, 
                                        beam_type=BeamType.ION, 
                                        alignment_current=alignment_current,
                                        steps=_ALIGNMENT_ATTEMPTS)
    else:
        logging.warning(f"Using alignment method v1 for {lamella._petname}... This method will be depreciated in the next version..")
        # V1
        tmp = deepcopy(settings.image)
        settings.image = ImageSettings.fromFibsemImage(ref_image)
        settings.image.filename = f"alignment_target_{lamella.state.stage.name}"
        settings.image.autocontrast = False
        alignment._multi_step_alignment(microscope=microscope, 
            image_settings=settings.image, 
            ref_image=ref_image, 
            reduced_area=lamella.fiducial_area, 
            alignment_current=alignment_current, 
            steps=_ALIGNMENT_ATTEMPTS)
        
        settings.image = tmp
        settings.image.reduced_area = None
    ####

    # TODO: INSERT BEAM SHIFT ALIGN FOR SEM HERE
    if settings.protocol["options"].get("use_sem_beam_shift_alignment", False):
        lamella = align_feature_beam_shift(
            microscope,
            settings,
            lamella=lamella,
            parent_ui=parent_ui,
            validate=validate,
            beam_type=BeamType.ELECTRON,
            hfw=settings.image.hfw,
        )

    # take reference images
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    settings.image.filename = f"ref_{lamella.state.stage.name}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)


    # define feature
    _MILL_FEATURES = bool(method in ["autolamella-on-grid", "autolamella-waffle"])
    features_stages = []
    if _MILL_FEATURES and lamella.state.stage.name == AutoLamellaWaffleStage.MillRoughCut.name:
        log_status_message(lamella, "MILL_FEATURE")

        # check if using notch or microexpansion
        if use_notch := bool(settings.protocol["options"].get("use_notch", False)):
            _feature_name = "notch"

            feature_stage = patterning.get_milling_stages(_feature_name, lamella.protocol, 
                                                          point=Point.from_dict(lamella.protocol[_feature_name]["point"]))
            features_stages += feature_stage

        if use_microexpansion := bool(settings.protocol["options"].get("use_microexpansion", False)):
            _feature_name = "microexpansion"
            feature_stage = patterning.get_milling_stages(_feature_name, lamella.protocol, 
                                                          point=Point.from_dict(lamella.protocol[_feature_name]["point"]))
            features_stages += feature_stage

        if features_stages:
            features_stages = update_milling_ui(features_stages, parent_ui,
                msg=f"Press Run Milling to mill the features for {lamella._petname}. Press Continue when done.",
                validate=validate,
            )

        if use_notch:
            _feature_name = "notch"
            idx = 0
            lamella.protocol[_feature_name] = deepcopy(patterning.get_protocol_from_stages(features_stages[idx]))
            lamella.protocol[_feature_name]["point"] = features_stages[idx].pattern.point.to_dict()

        if use_microexpansion:
            _feature_name = "microexpansion"
            idx = use_notch
            lamella.protocol[_feature_name] = deepcopy(patterning.get_protocol_from_stages(features_stages[idx]))
            lamella.protocol[_feature_name]["point"] = features_stages[idx].pattern.point.to_dict()


    # mill lamella trenches
    log_status_message(lamella, "MILL_LAMELLA")

    stages = update_milling_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the Trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )
   
    # TODO: refactor this so it is like the original protocol
    lamella.protocol[lamella.state.stage.name] = deepcopy(patterning.get_protocol_from_stages(stages[:n_lamella]))
    lamella.protocol[lamella.state.stage.name]["point"] = stages[0].pattern.point.to_dict()

    if _take_reference_images:
        # take reference images
        log_status_message(lamella, "REFERENCE_IMAGES")
        update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
        reference_images = acquire.take_set_of_reference_images(
            microscope=microscope,
            image_settings=settings.image,
            hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
            filename=f"ref_{lamella.state.stage.name}_final",
        )
        set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    if _take_high_quality_ref:
        log_status_message(lamella, "HIGH_QUALITY_REFERENCE_IMAGES")
        update_status_ui(parent_ui, f"{lamella.info} Acquiring High Quality Reference Images...")

        ddict = {"dwell_time": 2.0e-6,
            "resolution": fcfg.REFERENCE_RES_HIGH,
            "hfw": fcfg.REFERENCE_HFW_SUPER,
            "frame_integration": 2,
        }
        hq_settings = settings.protocol["options"].get("high_quality_image", ddict)
        # take high quality reference images
        settings.image.save = True
        settings.image.filename = f"ref_{lamella.state.stage.name}_final_ultra"
        settings.image.hfw = hq_settings["hfw"]
        settings.image.dwell_time = hq_settings["dwell_time"]
        settings.image.resolution = hq_settings["resolution"]
        settings.image.frame_integration = hq_settings["frame_integration"]
        settings.image.beam_type = BeamType.ELECTRON
        eb_image = acquire.new_image(microscope, settings.image)
        # set_images_ui(parent_ui, eb_image, ib_image)
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
    settings.image.path = lamella.path
    method = settings.protocol["options"].get("method", "autolamella-waffle")

    if "fiducial" not in settings.protocol["milling"]:
        settings.protocol["milling"]["fiducial"] = DEFAULT_FIDUCIAL_PROTOCOL

    log_status_message(lamella, "ALIGN_LAMELLA")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Lamella...")
    
    milling_angle = settings.protocol["options"].get("lamella_tilt_angle", 18)
    stage_position = microscope.get_stage_position()
    is_close = np.isclose(np.deg2rad(milling_angle), stage_position.t)
    if not is_close and validate and method == "autolamella-on-grid":
        ret = ask_user(parent_ui=parent_ui, 
                    msg=f"The current tilt ({np.rad2deg(stage_position.t)} deg) does not match the specified milling tilt ({milling_angle} deg). Press Tilt to go to the milling angle.", 
                    pos="Tilt", neg="Skip")
        if ret:
            actions.move_to_lamella_angle(microscope, settings.protocol)
            
    if method != "autolamella-on-grid":
        actions.move_to_lamella_angle(microscope, settings.protocol)

    if method == "autolamella-liftout":

        # OFFSET FOR COMPUCENTRIC ROTATION
        X_OFFSET = settings.protocol["options"].get("compucentric_x_offset", 0)
        Y_OFFSET = settings.protocol["options"].get("compucentric_y_offset", 0)
        microscope.stable_move(dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)

    if method != "autolamella-on-grid":
        lamella = align_feature_coincident(microscope, settings, lamella, parent_ui, validate)

    log_status_message(lamella, "SETUP_PATTERNS")

    # TODO: copy the entire milling protocol into each lamella protocol beforehand
    # load the default protocol unless in lamella protocol
    protocol = lamella.protocol if "lamella" in lamella.protocol else settings.protocol["milling"]
    lamella_position = Point.from_dict(protocol["lamella"].get("point", {"x": 0, "y": 0})) 
    lamella_stages = patterning.get_milling_stages("lamella", protocol, lamella_position)
    stages = deepcopy(lamella_stages)
    n_lamella = len(stages)

    settings.image.hfw = stages[0].milling.hfw # fcfg.REFERENCE_HFW_SUPER
    settings.image.filename = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # feature 
    if _MILL_FEATURES := method in ["autolamella-on-grid", "autolamella-waffle" ]:

        if use_notch := bool(settings.protocol["options"].get("use_notch", False)):
            _feature_name = "notch"

            protocol = lamella.protocol if _feature_name in lamella.protocol else settings.protocol["milling"]
            NOTCH_H_OFFSET = 0.5e-6                     
            notch_position = Point.from_dict(protocol[_feature_name].get("point", 
                    {"x":lamella_position.x + stages[0].pattern.protocol["lamella_width"] / 2 + NOTCH_H_OFFSET, 
                    "y": lamella_position.y})) 
            notch_stage = patterning.get_milling_stages(_feature_name, protocol, notch_position)
            n_notch = len(notch_stage)
            stages += notch_stage

        if use_microexpansion := bool(settings.protocol["options"].get("use_microexpansion", False)):
            _feature_name = "microexpansion"
            protocol = lamella.protocol if _feature_name in lamella.protocol else settings.protocol["milling"]                  
            feature_position = Point.from_dict(protocol[_feature_name].get("point", {"x": 0, "y": 0})) 
            microexpansion_stage = patterning.get_milling_stages(_feature_name, protocol, feature_position)
            n_microexpansion = len(microexpansion_stage)
            stages += microexpansion_stage

    # fiducial
    if use_fiducial:= settings.protocol["options"].get("use_fiducial", True):
        protocol = lamella.protocol if "fiducial" in lamella.protocol else settings.protocol["milling"]
        
        FIDUCIAL_X_OFFSET = 25e-6
        if method == "autolamella-liftout":
            FIDUCIAL_X_OFFSET *= -1
        
        fiducial_position = Point.from_dict(protocol["fiducial"].get("point", {"x": FIDUCIAL_X_OFFSET, "y": 0}))
        fiducial_stage = patterning.get_milling_stages("fiducial", protocol, fiducial_position)

        stages += fiducial_stage
    
    validate_position = True if method != "autolamella-on-grid" else validate
    if validate_position:
        stages = update_milling_ui(stages, parent_ui, 
            msg=f"Confirm the positions for the {lamella._petname} milling. Press Continue to Confirm.",
            validate=validate_position, # always validate non on-grid for now
            milling_enabled=False)
    
    # TODO: can I remove this now...d
    for stage in stages:
        logging.info(f"{stage.name}: {stage}") 

    # lamella
    n_lamella = len(lamella_stages)
    lamella.protocol["lamella"] = deepcopy(patterning.get_protocol_from_stages(stages[:n_lamella]))
    lamella.protocol["lamella"]["point"] = stages[0].pattern.point.to_dict()

    if _MILL_FEATURES:
        if use_notch:
            _feature_name = "notch"
            idx = n_lamella
            lamella.protocol[_feature_name] = deepcopy(patterning.get_protocol_from_stages(stages[idx]))
            lamella.protocol[_feature_name]["point"] = stages[idx].pattern.point.to_dict()

        if use_microexpansion:
            _feature_name = "microexpansion"
            idx = n_lamella + use_notch
            lamella.protocol[_feature_name] = deepcopy(patterning.get_protocol_from_stages(stages[idx]))
            lamella.protocol[_feature_name]["point"] = stages[idx].pattern.point.to_dict()

#     # TODO: integrate this style
#     # lamella.protocol[AutoLamellaWaffleStage.MillRoughCut.name] = deepcopy(patterning.get_protocol_from_stages(stages[0]))
#     # lamella.protocol[AutoLamellaWaffleStage.MillRoughCut.name]["point"] = stages[0].pattern.point.to_dict()
#     # lamella.protocol[AutoLamellaWaffleStage.MillPolishingCut.name] = deepcopy(patterning.get_protocol_from_stages(stages[2]))
#     # lamella.protocol[AutoLamellaWaffleStage.MillPolishingCut.name]["point"] = stages[2].pattern.point.to_dict()

    # feature
    # if "autolamella" in method:
    #     n_features = len(feature_stage)
    #     lamella.protocol[_feature_name] = deepcopy(patterning.get_protocol_from_stages(stages[n_lamella:n_lamella+n_features]))
    #     lamella.protocol[_feature_name]["point"] = stages[n_lamella].pattern.point.to_dict()

    # fiducial
    if use_fiducial:
        n_fiducial = len(fiducial_stage)
        fiducial_stage = deepcopy(stages[-n_fiducial:])

        # save fiducial information
        fiducial_stage = fiducial_stage[0] # always single stage
        lamella.protocol["fiducial"] = deepcopy(patterning.get_protocol_from_stages(fiducial_stage))
        lamella.protocol["fiducial"]["point"] = fiducial_stage.pattern.point.to_dict()
        lamella.fiducial_area, _  = _calculate_fiducial_area_v2(ib_image, 
            deepcopy(fiducial_stage.pattern.point), 
            lamella.protocol["fiducial"]["stages"][0]["height"])
        alignment_hfw = fiducial_stage.milling.hfw

        # mill the fiducial
        fiducial_stage = patterning.get_milling_stages("fiducial", lamella.protocol, Point.from_dict(lamella.protocol["fiducial"]["point"]))
        stages = update_milling_ui(fiducial_stage, parent_ui, 
            msg=f"Press Run Milling to mill the fiducial for {lamella._petname}. Press Continue when done.", 
            validate=validate)
        alignment_hfw = stages[0].milling.hfw
    else:
        # non-fiducial based alignment
        alignment_area_dict = settings.protocol["options"].get("alignment_area", DEFAULT_ALIGNMENT_AREA)
        lamella.fiducial_area = FibsemRectangle.from_dict(alignment_area_dict)
        alignment_hfw = lamella.protocol["lamella"]["stages"][0]["hfw"]

    logging.info(f"ALIGNMENT AREA WORKFLOW: {lamella.fiducial_area}")
    lamella.fiducial_area = update_alignment_area_ui(alignment_area=lamella.fiducial_area, 
                                              parent_ui=parent_ui, 
                                              msg="Edit Alignment Area. Press Continue when done.", 
                                              validate=validate )

    # set reduced area for fiducial alignment
    settings.image.reduced_area = lamella.fiducial_area
    logging.info(f"Alignment: Use Fiducial: {use_fiducial}, Alignment Area: {lamella.fiducial_area}")

    # TODO: the ref should also be acquired at the milling current? -> yes
    # for alignment
    settings.image.beam_type = BeamType.ION
    settings.image.save = True
    settings.image.hfw =  alignment_hfw
    settings.image.filename = f"ref_alignment"
    settings.image.autocontrast = False # disable autocontrast for alignment
    logging.info(f"REDUCED_AREA: {settings.image.reduced_area}")
    ib_image = acquire.new_image(microscope, settings.image)
    settings.image.reduced_area = None
    settings.image.autocontrast = True
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    # # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope,
        settings.image,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        filename=f"ref_{lamella.state.stage.name}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)


    return lamella


def end_of_stage_update(
    microscope: FibsemMicroscope, experiment: Experiment, lamella: Lamella, parent_ui: AutoLamellaUI, _save_state: bool = True,
) -> Experiment:
    """Save the current microscope state configuration to disk, and log that the stage has been completed."""

    # save state information
    if _save_state:
        lamella.state.microscope_state = microscope.get_microscope_state()
    lamella.state.end_timestamp = datetime.timestamp(datetime.now())

    # write history
    lamella.history.append(deepcopy(lamella.state))

    # # update and save experiment
    experiment.save()

    log_status_message(lamella, "FINISHED")
    update_status_ui(parent_ui, f"{lamella.info} Finished")

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
        update_status_ui(parent_ui, f"{lamella.info} Restoring Last State...")
        microscope.set_microscope_state(lamella.state.microscope_state)

    # set current state information
    lamella.state.stage = deepcopy(next_stage)
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    log_status_message(lamella, "STARTED")
    update_status_ui(parent_ui, f"{lamella.info} Starting...")

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

def align_feature_coincident(microscope: FibsemMicroscope, settings: MicroscopeSettings, 
                              lamella: Lamella, parent_ui: AutoLamellaUI, 
                              validate: bool, 
                              hfw: float = fcfg.REFERENCE_HFW_MEDIUM,
                              feature: Feature = LamellaCentre()) -> Lamella:
    """Align the feature in the electron and ion beams to be coincident."""

    # bookkeeping
    features = [feature]

    # update status
    log_status_message(lamella, f"ALIGN_FEATURE_COINCIDENT")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Feature Coincident ({feature.name})...")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = hfw
    settings.image.filename = f"ref_{lamella.state.stage.name}_{feature.name}_align_coincident_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # detect
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.stage_position)

    microscope.stable_move(
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )

    # Align ion so it is coincident with the electron beam
    settings.image.beam_type = BeamType.ION
    settings.image.hfw = hfw

    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.stage_position)
    
    # align vertical
    microscope.vertical_move(
        dx=det.features[0].feature_m.x,
        dy=-det.features[0].feature_m.y,
    )

    # reference images
    settings.image.save = True
    settings.image.hfw = hfw
    settings.image.filename = f"ref_{lamella.state.stage.name}_{feature.name}_align_coincident_final"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    return lamella

def align_feature_beam_shift(microscope: FibsemMicroscope, 
                            settings: MicroscopeSettings, 
                            lamella: Lamella, parent_ui: AutoLamellaUI, 
                            validate: bool, 
                            beam_type: BeamType = BeamType.ELECTRON,
                            hfw: float = fcfg.REFERENCE_HFW_MEDIUM,
                            feature: Feature = LamellaCentre()) -> Lamella:
    """Align the feature to the centre of the image using the beamshift."""

    # bookkeeping
    features = [feature]

    # update status
    log_status_message(lamella, f"ALIGN_FEATURE_BEAM_SHIFT")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Feature with beam shift ({feature.name})...")
    settings.image.beam_type = beam_type
    settings.image.hfw = hfw
    settings.image.filename = f"ref_{lamella.state.stage.name}_{feature.name}_align_beam_shift_ml"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    # detect
    det = update_detection_ui(microscope, settings, features, parent_ui, validate, msg=lamella.info, position=lamella.state.microscope_state.stage_position)

    # TODO: add movement modes; stable move, vertical move, beam shift

    microscope.beam_shift(
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=settings.image.beam_type
    )

    # reference images
    settings.image.save = True
    settings.image.hfw = hfw
    settings.image.filename = f"ref_{lamella.state.stage.name}_{feature.name}_align_beam_shift_final"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    set_images_ui(parent_ui, eb_image, ib_image)

    return lamella
