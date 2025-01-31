import logging
import os
import time
from copy import deepcopy
from datetime import datetime
from typing import List, Tuple

import numpy as np
from fibsem import acquire, alignment, calibration
from fibsem import config as fcfg
from fibsem.detection.detection import (
    Feature,
    LamellaBottomEdge,
    LamellaCentre,
    LamellaTopEdge,
    VolumeBlockCentre,
)
from fibsem.microscope import FibsemMicroscope
from fibsem.milling import get_milling_stages, get_protocol_from_stages, FibsemMillingStage
from fibsem.structures import (
    BeamType,
    FibsemImage,
    FibsemRectangle,
    FibsemStagePosition,
    ImageSettings,
    Point,
    calculate_fiducial_area_v2,
)
from autolamella.structures import AutoLamellaProtocol

from autolamella.config import USE_BEAM_SHIFT_ALIGNMENT_V2
from autolamella.protocol.validation import (
    DEFAULT_ALIGNMENT_AREA,
    DEFAULT_FIDUCIAL_PROTOCOL,
    FIDUCIAL_KEY,
    MICROEXPANSION_KEY,
    MILL_POLISHING_KEY,
    MILL_ROUGH_KEY,
    NOTCH_KEY,
    SETUP_LAMELLA_KEY,
    TRENCH_KEY,
    UNDERCUT_KEY,
)
from autolamella.structures import (
    AutoLamellaStage,
    AutoLamellaMethod,
    Experiment,
    Lamella,
    get_autolamella_method,
)
from autolamella.ui import AutoLamellaUI
from autolamella.workflows import actions
from autolamella.workflows.ui import (
    ask_user,
    set_images_ui,
    update_alignment_area_ui,
    update_detection_ui,
    update_experiment_ui,
    update_milling_ui,
    update_status_ui,
)

from autolamella.structures import WORKFLOW_STAGE_TO_PROTOCOL_KEY

# constants
ATOL_STAGE_TILT = 0.017 # 1 degrees

# CORE WORKFLOW STEPS
def log_status_message(lamella: Lamella, step: str):
    logging.debug({"msg": "status", "petname": lamella.name, "stage": lamella.status, "step": step})

def log_status_message_raw(stage: str, step: str, petname: str = "null"):
    logging.debug({"msg": "status", "petname": petname, stage: stage, "step": step })   


def pass_through_stage(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    # pass through stage
    return lamella 

# mill trench
def mill_trench(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = protocol.supervision[lamella.workflow]
    image_settings = protocol.configuration.image
    image_settings.path = lamella.path

    log_status_message(lamella, "MOVE_TO_TRENCH")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Trench Position...")
    microscope.move_flat_to_beam(BeamType.ION)
    
    # align to reference image
    # TODO: support saving a reference image when selecting the trench from minimap
    reference_image_path = os.path.join(lamella.path, "ref_PositionReady.tif")
    align_trench_reference = protocol.tmp.get("align_trench_reference", False)
    if os.path.exists(reference_image_path) and align_trench_reference:
        log_status_message(lamella, "ALIGN_TRENCH_REFERENCE")
        update_status_ui(parent_ui, f"{lamella.info} Aligning Trench Reference...")
        ref_image = FibsemImage.load(reference_image_path)
        alignment.multi_step_alignment_v3(microscope=microscope, 
                                        ref_image=ref_image, 
                                        beam_type=BeamType.ION, 
                                        alignment_current=None,
                                        steps=1, system="stage")

    log_status_message(lamella, "MILL_TRENCH")

    # get trench milling stages
    stages = get_milling_stages(TRENCH_KEY, lamella.protocol)

    # acquire reference images
    image_settings.hfw = stages[0].milling.hfw
    image_settings.filename = f"ref_{lamella.status}_start"
    image_settings.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)
    update_status_ui(parent_ui, f"{lamella.info} Preparing Trench...")
    
    # define trench milling stage
    stages = update_milling_ui(microscope, stages, parent_ui,
        msg=f"Press Run Milling to mill the trenches for {lamella.name}. Press Continue when done.",
        validate=validate,
    )
    
    # log the protocol
    lamella.protocol[TRENCH_KEY] = deepcopy(get_protocol_from_stages(stages))
    
    # charge neutralisation
    log_status_message(lamella, "CHARGE_NEUTRALISATION")
    update_status_ui(parent_ui, f"{lamella.info} Neutralising Sample Charge...")
    image_settings.beam_type = BeamType.ELECTRON
    calibration.auto_charge_neutralisation(microscope, image_settings)
    
    # reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=image_settings,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.status}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

# mill undercut
def mill_undercut(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    method = protocol.method
    validate = protocol.supervision[lamella.workflow]
    image_settings = protocol.configuration.image
    image_settings.path = lamella.path

    # optional undercut
    is_undercut_required = protocol.tmp.get("undercut_required", True)
    if not is_undercut_required:
        logging.info("Skipping undercut")
        return lamella

    # rotate flat to eb
    log_status_message(lamella, "MOVE_TO_UNDERCUT")
    update_status_ui(parent_ui, f"{lamella.info} Moving to Undercut Position...")
    microscope.move_flat_to_beam(BeamType.ELECTRON, _safe=True)
    
    # OFFSET FOR COMPUCENTRIC ROTATION
    X_OFFSET = protocol.tmp.get("compucentric_x_offset", 0)
    Y_OFFSET = protocol.tmp.get("compucentric_y_offset", 0)
    microscope.stable_move(dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)
    
    # align feature coincident   
    feature = LamellaCentre()
    if method is AutoLamellaMethod.SERIAL_LIFTOUT:
        feature = VolumeBlockCentre()
        
    lamella = align_feature_coincident(
        microscope=microscope,
        image_settings=image_settings,
        lamella=lamella,
        checkpoint=protocol.options.checkpoint,
        parent_ui=parent_ui,
        validate=validate,
        feature=feature,
    )

    # mill under cut
    undercut_stages = get_milling_stages(UNDERCUT_KEY, lamella.protocol)
    post_milled_undercut_stages = []
    undercut_tilt_step =  np.deg2rad(protocol.options.undercut_tilt_angle)
    hfw = undercut_stages[0].milling.hfw

    for i, undercut_stage in enumerate(undercut_stages):

        nid = f"{i+1:02d}" # helper

        # tilt down, align to trench
        log_status_message(lamella, f"TILT_UNDERCUT_{nid}")
        update_status_ui(parent_ui, f"{lamella.info} Tilting to Undercut Position...")
        microscope.move_stage_relative(FibsemStagePosition(t=undercut_tilt_step))

        # detect
        log_status_message(lamella, f"ALIGN_UNDERCUT_{nid}")
        image_settings.beam_type = BeamType.ION
        image_settings.hfw = hfw
        image_settings.filename = f"ref_{lamella.status}_align_ml_{nid}"
        image_settings.save = True
        eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
        set_images_ui(parent_ui, eb_image, ib_image)

        # get pattern
        scan_rotation = microscope.get("scan_rotation", beam_type=BeamType.ION)
        features = [LamellaTopEdge() if np.isclose(scan_rotation, 0) else LamellaBottomEdge()]

        det = update_detection_ui(microscope=microscope, 
                                  image_settings=image_settings, 
                                  checkpoint=protocol.options.checkpoint, 
                                  features=features, 
                                  parent_ui=parent_ui, 
                                  validate=validate, 
                                  msg=lamella.info)

        # # move pattern
        # if i > 0: # reduce the undercut height by half each time
        #     lamella.protocol["undercut"]["height"] /= 2

        if method == AutoLamellaMethod.LIFTOUT:
            offset = undercut_stage.pattern.trench_width / 2 + 1e-6
        else:         
            offset = undercut_stage.pattern.height / 2
        point = deepcopy(det.features[0].feature_m)
        point.y += offset if np.isclose(scan_rotation, 0) else -offset

        # set pattern position
        undercut_stage.pattern.point = point

        # mill undercut 1
        log_status_message(lamella, f"MILL_UNDERCUT_{nid}")
        stages = update_milling_ui(microscope, [undercut_stage], parent_ui,
            msg=f"Press Run Milling to mill the Undercut {nid} for {lamella.name}. Press Continue when done.",
            validate=validate,
        )

        post_milled_undercut_stages.extend(stages)

    # log undercut stages
    lamella.protocol[UNDERCUT_KEY] = get_protocol_from_stages(post_milled_undercut_stages)

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    image_settings.beam_type = BeamType.ION
    image_settings.hfw = fcfg.REFERENCE_HFW_HIGH
    image_settings.save = True
    image_settings.filename=f"ref_{lamella.status}_undercut"
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)

    # optional return flat to electron beam (autoliftout)
    if protocol.tmp.get("undercut_return_to_electron", False):
        microscope.move_flat_to_beam(BeamType.ELECTRON, _safe=True)

    log_status_message(lamella, "ALIGN_FINAL")

    image_settings.beam_type = BeamType.ION
    image_settings.hfw = fcfg.REFERENCE_HFW_HIGH

    features = [LamellaCentre()]
    det = update_detection_ui(microscope=microscope,
                                image_settings=image_settings,
                                checkpoint=protocol.options.checkpoint,
                                features=features,
                                parent_ui=parent_ui,
                                validate=validate,
                                msg=lamella.info)

    # align vertical
    microscope.vertical_move(
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
    )

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=image_settings,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        filename=f"ref_{lamella.status}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

def mill_lamella(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    image_settings = protocol.configuration.image
    image_settings.path = lamella.path

    method = protocol.method
    validate = protocol.supervision[lamella.workflow]

    align_at_milling_current = protocol.options.alignment_at_milling_current
    take_reference_images = bool(
        lamella.state.stage is AutoLamellaStage.MillRough 
        or protocol.options.take_final_reference_images
        )
    acquire_high_quality_image =  bool(
        lamella.state.stage is AutoLamellaStage.MillPolishing 
        and protocol.tmp.get("high_quality_image", {}).get("enabled", False)
        )

    # milling stages
    milling_stage_name = WORKFLOW_STAGE_TO_PROTOCOL_KEY[lamella.workflow]
    stages: List[FibsemMillingStage] = get_milling_stages(key=milling_stage_name,
                                                          protocol=lamella.protocol)

    if not isinstance(stages, list):
        stages = [stages]

    n_lamella = len(stages) # number of lamella stages

    # beam_shift alignment #TODO: clean up this execution, bit messy and redundant
    log_status_message(lamella, "ALIGN_LAMELLA")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Reference Images...")

    image_settings.save = True
    image_settings.hfw = stages[0].milling.hfw
    image_settings.beam_type = BeamType.ION
    ref_image = FibsemImage.load(os.path.join(lamella.path, "ref_alignment_ib.tif"))

    # beam alignment
    alignment_attempts = protocol.options.alignment_attempts
    alignment_current = stages[0].milling.milling_current if align_at_milling_current else None

    ### REPLACE WITH V2
    if USE_BEAM_SHIFT_ALIGNMENT_V2:
        alignment.multi_step_alignment_v2(microscope=microscope, 
                                        ref_image=ref_image, 
                                        beam_type=BeamType.ION, 
                                        alignment_current=alignment_current,
                                        steps=alignment_attempts)
    else:
        logging.warning(f"Using alignment method v1 for {lamella.name}... This method will be depreciated in the next version..")
        # V1
        tmp = deepcopy(image_settings)
        image_settings = ImageSettings.fromFibsemImage(ref_image)
        image_settings.filename = f"alignment_target_{lamella.status}"
        image_settings.autocontrast = False
        alignment._multi_step_alignment(microscope=microscope, 
            image_settings=image_settings, 
            ref_image=ref_image, 
            reduced_area=lamella.alignment_area, 
            alignment_current=alignment_current, 
            steps=alignment_attempts)

        image_settings = tmp
        image_settings.reduced_area = None
    #### 

    # take reference images
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    image_settings.filename = f"ref_{lamella.status}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)

    # define feature
    use_stress_relief = bool(method in [AutoLamellaMethod.ON_GRID, AutoLamellaMethod.WAFFLE])
    features_stages = []
    if use_stress_relief and lamella.workflow is AutoLamellaStage.MillRough:
        log_status_message(lamella, "MILL_FEATURE")

        # check if using notch or microexpansion
        if use_notch := protocol.options.use_notch:
            features_stages.extend(get_milling_stages(NOTCH_KEY, lamella.protocol))                                                  

        if use_microexpansion := protocol.options.use_microexpansion:
            features_stages.extend(get_milling_stages(MICROEXPANSION_KEY, lamella.protocol)) 
                    
        if features_stages:

            # assign alignment area for all stages
            for fstage in features_stages:
                fstage.alignment.rect = lamella.alignment_area

            features_stages = update_milling_ui(microscope, features_stages, parent_ui,
                msg=f"Press Run Milling to mill the features for {lamella.name}. Press Continue when done.",
                validate=validate,
            )

        if use_notch:
            idx = 0
            lamella.protocol[NOTCH_KEY] = get_protocol_from_stages(features_stages[idx])

        if use_microexpansion:
            idx = use_notch
            lamella.protocol[NOTCH_KEY] = get_protocol_from_stages(features_stages[idx])

    # assign alignment area for all stages
    for stage in stages:
        stage.alignment.rect = lamella.alignment_area

    # mill lamella trenches
    log_status_message(lamella, "MILL_LAMELLA")

    stages = update_milling_ui(microscope, stages, parent_ui,
        msg=f"Press Run Milling to mill the Trenches for {lamella.name}. Press Continue when done.",
        validate=validate,
    )

    # log the protocol
    lamella.protocol[milling_stage_name] = get_protocol_from_stages(stages[:n_lamella])

    if take_reference_images:
        # take reference images
        log_status_message(lamella, "REFERENCE_IMAGES")
        update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
        reference_images = acquire.take_set_of_reference_images(
            microscope=microscope,
            image_settings=image_settings,
            hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
            filename=f"ref_{lamella.status}_final",
        )
        set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    if acquire_high_quality_image:
        log_status_message(lamella, "HIGH_QUALITY_REFERENCE_IMAGES")
        update_status_ui(parent_ui, f"{lamella.info} Acquiring High Quality Reference Images...")

        ddict = {"dwell_time": 2.0e-6,
            "resolution": fcfg.REFERENCE_RES_HIGH,
            "hfw": fcfg.REFERENCE_HFW_SUPER,
            "frame_integration": 2,
        }
        hq_settings = protocol.tmp.get("high_quality_image", ddict)
        # take high quality reference images
        image_settings.save = True
        image_settings.filename = f"ref_{lamella.status}_final_ultra"
        image_settings.hfw = hq_settings["hfw"]
        image_settings.dwell_time = hq_settings["dwell_time"]
        image_settings.resolution = hq_settings["resolution"]
        image_settings.frame_integration = hq_settings["frame_integration"]
        image_settings.beam_type = BeamType.ELECTRON
        eb_image = acquire.new_image(microscope, image_settings)
        # set_images_ui(parent_ui, eb_image, ib_image)
        image_settings.frame_integration = 1 # restore
        image_settings.resolution = fcfg.REFERENCE_RES_MEDIUM

    return lamella


def setup_lamella(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    method = protocol.method
    validate = protocol.supervision[lamella.workflow]
    image_settings: ImageSettings = protocol.configuration.image
    image_settings.path = lamella.path

    if FIDUCIAL_KEY not in lamella.protocol:
        lamella.protocol[FIDUCIAL_KEY] = DEFAULT_FIDUCIAL_PROTOCOL

    log_status_message(lamella, "ALIGN_LAMELLA")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Lamella...")

    milling_angle = protocol.options.milling_tilt_angle
    stage_position = microscope.get_stage_position()
    is_close = np.isclose(np.deg2rad(milling_angle), stage_position.t, atol=ATOL_STAGE_TILT)

    # TODO: migrate to milling angle, rather than stage tilt, make it automatic
    # is_close = actions.is_close_to_milling_angle(microscope=microscope, 
    #                                              milling_angle=np.deg2rad(milling_angle),
    #                                              atol=ATOL_STAGE_TILT * 2)

    if not is_close and validate and method is AutoLamellaMethod.ON_GRID:
        current_t = np.rad2deg(stage_position.t)
        ret = ask_user(parent_ui=parent_ui,
                    msg=f"Tilt to specified milling angle ({milling_angle:.2f} deg)? Current tilt is {current_t:.2f} deg.",
                    pos="Tilt", neg="Skip")
        if ret:
            actions.move_to_lamella_angle(microscope, 
                                          rotation=np.deg2rad(microscope.system.stage.rotation_reference),
                                          tilt=np.deg2rad(milling_angle))
                # actions.move_to_milling_angle(microscope=microscope,
    #                               milling_angle=np.deg2rad(milling_angle))

    if method != AutoLamellaMethod.ON_GRID:
        actions.move_to_lamella_angle(microscope,
                                rotation=np.deg2rad(microscope.system.stage.rotation_reference),
                                tilt=np.deg2rad(milling_angle))
            # actions.move_to_milling_angle(microscope=microscope,
    #                               milling_angle=np.deg2rad(milling_angle))

    if method is AutoLamellaMethod.LIFTOUT:

        # OFFSET FOR COMPUCENTRIC ROTATION
        X_OFFSET = protocol.tmp.get("compucentric_x_offset", 0)
        Y_OFFSET = protocol.tmp.get("compucentric_y_offset", 0)
        microscope.stable_move(dx=X_OFFSET, dy=Y_OFFSET, beam_type=BeamType.ELECTRON)

    if method != AutoLamellaMethod.ON_GRID:
        lamella = align_feature_coincident(microscope=microscope, 
                                           image_settings=image_settings, 
                                           lamella=lamella, 
                                           checkpoint=protocol.options.checkpoint, 
                                           parent_ui=parent_ui, 
                                           validate=validate)

    log_status_message(lamella, "SETUP_PATTERNS")

    rough_mill_stages = get_milling_stages(MILL_ROUGH_KEY, lamella.protocol)
    polishing_mill_stages = get_milling_stages(MILL_POLISHING_KEY, lamella.protocol) # TODO: store this on the lamella object, rather than re-calling from protocol?
    lamella_stages = rough_mill_stages + polishing_mill_stages
    stages = deepcopy(lamella_stages)
    n_lamella = len(stages)
    n_mill_rough = len(rough_mill_stages)
    n_mill_polishing = len(polishing_mill_stages)

    image_settings.hfw = stages[0].milling.hfw
    image_settings.filename = f"ref_{lamella.status}_start"
    image_settings.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)

    # feature 
    if use_stress_relief := method in [AutoLamellaMethod.ON_GRID, AutoLamellaMethod.WAFFLE]:

        if use_notch:= protocol.options.use_notch:
            stages.extend(get_milling_stages(NOTCH_KEY, lamella.protocol))

        if use_microexpansion := protocol.options.use_microexpansion:
            stages.extend(get_milling_stages(MICROEXPANSION_KEY, lamella.protocol))

    # fiducial
    if use_fiducial:= protocol.options.use_fiducial:
        fiducial_stage = get_milling_stages(FIDUCIAL_KEY, lamella.protocol)

        stages += fiducial_stage # TODO: remove dependency on this
    
    if validate:
        stages = update_milling_ui(microscope, stages, parent_ui, 
            msg=f"Confirm the positions for the {lamella.name} milling. Press Continue to Confirm.",
            validate=validate, # always validate non on-grid for now
            milling_enabled=False)

    # rough milling
    lamella.protocol[MILL_ROUGH_KEY] = deepcopy(get_protocol_from_stages(stages[:n_mill_rough]))

    # polishing
    lamella.protocol[MILL_POLISHING_KEY] = deepcopy(get_protocol_from_stages(stages[n_mill_rough:n_lamella]))

    # WORKFLOW: 
        # STAGE 1
        # STAGE 2
        # STAgE 3
        # STAGE 4 etc

    # MILL_ROUGH
    #   MICROEXPANSION
    #   NOTCH
    #   ROUGH_MILL_01
    #   ROUGH_MILL_02
    # MILL_POLISHING

    # TODO: instead of having these as separate parts of the milling config, just include them in the mill_rough part?
    if use_stress_relief:
        if use_notch:
            idx = n_lamella
            lamella.protocol[NOTCH_KEY] = deepcopy(get_protocol_from_stages(stages[idx]))

        if use_microexpansion:
            idx = n_lamella + use_notch
            lamella.protocol[MICROEXPANSION_KEY] = deepcopy(get_protocol_from_stages(stages[idx]))

    # fiducial
    if use_fiducial:
        n_fiducial = len(fiducial_stage)
        fiducial_stage = deepcopy(stages[-n_fiducial:])

        # save fiducial information
        fiducial_stage = fiducial_stage[0] # always single stage
        lamella.protocol[FIDUCIAL_KEY] = deepcopy(get_protocol_from_stages(fiducial_stage))
        lamella.alignment_area, _  = calculate_fiducial_area_v2(ib_image, 
            deepcopy(fiducial_stage.pattern.point), 
            fiducial_stage.pattern.height)
        alignment_hfw = fiducial_stage.milling.hfw

        # mill the fiducial
        fiducial_stage = get_milling_stages(FIDUCIAL_KEY, lamella.protocol)
        stages = update_milling_ui(microscope, fiducial_stage, parent_ui, 
            msg=f"Press Run Milling to mill the fiducial for {lamella.name}. Press Continue when done.", 
            validate=validate)
        lamella.protocol[FIDUCIAL_KEY] = deepcopy(get_protocol_from_stages(stages))
        lamella.alignment_area, _  = calculate_fiducial_area_v2(ib_image, 
            deepcopy(stages[0].pattern.point), 
            stages[0].pattern.height)
        alignment_hfw = stages[0].milling.hfw
    else:
        # non-fiducial based alignment
        lamella.alignment_area = FibsemRectangle.from_dict(DEFAULT_ALIGNMENT_AREA)
        alignment_hfw = stages[0].milling.hfw

    logging.debug(f"alignment_area: {lamella.alignment_area}")
    lamella.alignment_area = update_alignment_area_ui(alignment_area=lamella.alignment_area, 
                                              parent_ui=parent_ui, 
                                              msg="Edit Alignment Area. Press Continue when done.", 
                                              validate=validate )

    # set reduced area for fiducial alignment
    image_settings.reduced_area = lamella.alignment_area
    logging.info(f"Alignment: Use Fiducial: {use_fiducial}, Alignment Area: {lamella.alignment_area}")

    # TODO: the ref should also be acquired at the milling current? -> yes
    # for alignment
    image_settings.beam_type = BeamType.ION
    image_settings.save = True
    image_settings.hfw =  alignment_hfw
    image_settings.filename = "ref_alignment"
    image_settings.autocontrast = False # disable autocontrast for alignment
    ib_image = acquire.new_image(microscope, image_settings)
    image_settings.reduced_area = None
    image_settings.autocontrast = True
    log_status_message(lamella, "REFERENCE_IMAGES")
    update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")

    # # take reference images
    reference_images = acquire.take_set_of_reference_images(
        microscope,
        image_settings,
        hfws=[fcfg.REFERENCE_HFW_HIGH, fcfg.REFERENCE_HFW_SUPER],
        filename=f"ref_{lamella.status}_final",
    )
    set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella


def end_of_stage_update(
    microscope: FibsemMicroscope, 
    experiment: Experiment, 
    lamella: Lamella, 
    parent_ui: AutoLamellaUI, 
    save_state: bool = True, 
    update_ui: bool = True,
) -> Experiment:
    """Save the current microscope state configuration to disk, and log that the stage has been completed."""

    # save state information
    if save_state:
        lamella.state.microscope_state = microscope.get_microscope_state()
    lamella.state.end_timestamp = datetime.timestamp(datetime.now())

    # write history
    lamella.history.append(deepcopy(lamella.state))
    lamella.states[lamella.workflow] = deepcopy(lamella.state)

    # update and save experiment
    experiment.save()

    log_status_message(lamella, "FINISHED")
    update_status_ui(parent_ui, f"{lamella.info} Finished")
    if update_ui:
        update_experiment_ui(parent_ui, experiment)

    return experiment

def start_of_stage_update(
    microscope: FibsemMicroscope,
    lamella: Lamella,
    next_stage: AutoLamellaStage,
    parent_ui: AutoLamellaUI, 
    restore_state: bool = True,
) -> Lamella:
    """Check the last completed stage and reload the microscope state if required. Log that the stage has started."""
    last_completed_stage = lamella.state.stage

    # restore to the last state
    if last_completed_stage.value == next_stage.value - 1 and restore_state:
        logging.info(
            f"{lamella.name} restarting from end of stage: {last_completed_stage.name}"
        )
        update_status_ui(parent_ui, f"{lamella.info} Restoring Last State...")
        microscope.set_microscope_state(lamella.state.microscope_state)

    # set current state information
    lamella.state.stage = deepcopy(next_stage)
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    log_status_message(lamella, "STARTED")
    update_status_ui(parent_ui, f"{lamella.info} Starting...", workflow_info=f"{lamella.info}")

    return lamella

def align_feature_coincident(
    microscope: FibsemMicroscope,
    image_settings: ImageSettings,
    lamella: Lamella,
    checkpoint: str,
    parent_ui: AutoLamellaUI,
    validate: bool,
    hfw: float = fcfg.REFERENCE_HFW_MEDIUM,
    feature: Feature = LamellaCentre(),
) -> Lamella:
    """Align the feature in the electron and ion beams to be coincident."""

    # bookkeeping
    features = [feature]

    # update status
    log_status_message(lamella, "ALIGN_FEATURE_COINCIDENT")
    update_status_ui(parent_ui, f"{lamella.info} Aligning Feature Coincident ({feature.name})...")
    image_settings.beam_type = BeamType.ELECTRON
    image_settings.hfw = hfw
    image_settings.filename = f"ref_{lamella.status}_{feature.name}_align_coincident_ml"
    image_settings.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)

    # detect
    det = update_detection_ui(microscope=microscope,
                              image_settings=image_settings,
                              features=features,
                              checkpoint=checkpoint,
                              parent_ui=parent_ui, 
                              validate=validate, 
                              msg=lamella.info, 
                              position=lamella.state.microscope_state.stage_position)

    microscope.stable_move(
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
        beam_type=image_settings.beam_type
    )

    # Align ion so it is coincident with the electron beam
    image_settings.beam_type = BeamType.ION
    image_settings.hfw = hfw

    det = update_detection_ui(microscope=microscope,
                              image_settings=image_settings,
                              features=features,
                              checkpoint=checkpoint,
                              parent_ui=parent_ui, 
                              validate=validate, 
                              msg=lamella.info, 
                              position=lamella.state.microscope_state.stage_position)
    
    # align vertical
    microscope.vertical_move(
        dx=det.features[0].feature_m.x,
        dy=det.features[0].feature_m.y,
    )

    # reference images
    image_settings.save = True
    image_settings.hfw = hfw
    image_settings.filename = f"ref_{lamella.status}_{feature.name}_align_coincident_final"
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)
    set_images_ui(parent_ui, eb_image, ib_image)

    return lamella
