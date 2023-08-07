import logging
import os
from copy import deepcopy
from datetime import datetime
from pprint import pprint

import numpy as np
from fibsem import acquire, milling, patterning, utils, calibration, alignment
from fibsem.microscope import FibsemMicroscope, ThermoMicroscope, TescanMicroscope
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
from fibsem import conversions


def log_status_message(lamella: Lamella, step: str):
    logging.debug(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | {step}")


def mill_trench(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("trench", True)
    settings.image.save_path = lamella.path

    # TODO: cross correlate the reference here
    # fname = os.path.join(lamella.path, f"ref_{AutoLamellaWaffleStage.SetupTrench.name}_ib.tif")
    # img = FibsemImage.load(fname)
    
    log_status_message(lamella, "MILL_TRENCH")

    settings.image.hfw = settings.protocol["trench"]["hfw"]
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

def mill_undercut(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:
    validate = settings.protocol["options"]["supervise"].get("undercut", True)
    settings.image.save_path = lamella.path

    # rotate flat to eb
    log_status_message(lamella, "MOVE_TO_UNDERCUT")
    _update_status_ui(parent_ui, f"{lamella.info} Moving to Undercut Position...")
    microscope.move_flat_to_beam(settings, BeamType.ELECTRON)

    # detect
    log_status_message(lamella, f"ALIGN_TRENCH")
    settings.image.beam_type = BeamType.ELECTRON
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
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
    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM

    features = [LamellaCentre()] 
    det = _validate_det_ui_v2(microscope, settings, features, parent_ui, validate, msg=lamella.info)
    
    # align vertical
    microscope.eucentric_move(
        settings, 
        dy=-det.features[0].feature_m.y,
    )
    # align horizontal
    microscope.stable_move(
        settings, 
        dx=det.features[0].feature_m.x,
        dy=0,
        beam_type=settings.image.beam_type
    )

    # lamella should now be centred in ion beam

    settings.image.hfw = fcfg.REFERENCE_HFW_MEDIUM
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)

    N_UNDERCUTS = int(settings.protocol["autolamella_undercut"].get("tilt_angle_step", 2))
    UNDERCUT_ANGLE_DEG = settings.protocol["autolamella_undercut"].get("tilt_angle", -10)
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
        offset = settings.protocol["autolamella_undercut"].get("height", 10) / 2
        point = deepcopy(det.features[0].feature_m)     
        point.y += offset if np.isclose(scan_rotation, 0) else -offset

        # mill undercut 1
        log_status_message(lamella, f"MILL_UNDERCUT_{_n}")
        stages = patterning._get_milling_stages("autolamella_undercut", settings.protocol, point=point)
        stages = _validate_mill_ui(stages, parent_ui,
            msg=f"Press Run Milling to mill the Undercut {_n} for {lamella._petname}. Press Continue when done.",
            validate=validate,
        )

        undercut_stages.append(stages[0])

    # log undercut stages
    lamella.protocol["undercut"] = deepcopy(patterning._get_protocol_from_stages(undercut_stages))
   

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_HIGH],
        label=f"ref_{lamella.state.stage.name}_final",
    )
    _set_images_ui(parent_ui, reference_images.high_res_eb, reference_images.high_res_ib)

    return lamella

def mill_feature(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("features", True)
    settings.image.save_path = lamella.path
    
    if settings.protocol["fiducial"]["enabled"] is False:
        lamella.fiducial_area = None
    
    # check if using notch or microexpansion
    _feature_name = "notch" if settings.protocol["notch"]["enabled"] else "microexpansion"

    stages = patterning._get_milling_stages(
        _feature_name, lamella.protocol, point=Point.__from_dict__(lamella.protocol[_feature_name]["point"])
    )

    # existing_current = microscope.get("current", BeamType.ION)
    # existing_preset = "30 keV; UHR imaging"

    # if settings.protocol["lamella"]["alignment_current"] in ["Milling", "milling","Milling Current"]:
    #     alignment_current = stages[0].milling.milling_current
    #     alignment_preset = stages[0].milling.preset
    #     print(f'---------------using milling current--------------------')
    # else:
    #     print(f'---------------using imaging current--------------------')
    #     alignment_current = existing_current
    #     alignment_preset = existing_preset
        
    # print(f'------------------ alignment current {alignment_current} ------------------')
    # print(f'------------------ alignment preset {alignment_preset} ------------------')
    
    # if isinstance(microscope,(ThermoMicroscope)):
    #     microscope.set(key="current",value=alignment_current,beam_type=BeamType.ION)
    # elif isinstance(microscope,TescanMicroscope):
    #     microscope.set(key="preset",value=alignment_preset,beam_type=BeamType.ION)

    log_status_message(lamella, "ALIGN_REFERENCE")
    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.beam_type = BeamType.ION
    settings.image.label = f"alignment_target_{lamella.state.stage.name}"
    ref_image = FibsemImage.load(os.path.join(lamella.path, f"ref_alignment_ib.tif"))
    alignment.beam_shift_alignment(microscope, settings.image, 
                                    ref_image=ref_image,
                                    reduced_area=lamella.fiducial_area)
    settings.image.reduced_area = None

    # # TODO: CHANGE_CURRENT_BACK
    # if isinstance(microscope,(ThermoMicroscope)):
    #     microscope.set(key="current",value=existing_current,beam_type=BeamType.ION)
    # elif isinstance(microscope,TescanMicroscope):
    #     microscope.set(key="preset",value=existing_preset, beam_type=BeamType.ION)



    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)
    _update_status_ui(parent_ui, f"{lamella.info} Preparing {_feature_name}...")

    # define notch/microexpansion
    log_status_message(lamella, "MILL_FEATURES")

    stages = _validate_mill_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the {_feature_name} for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )

    # log feature stages
    lamella.protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol[_feature_name]["point"] = stages[0].pattern.point.__to_dict__()

    # take reference images
    log_status_message(lamella, "REFERENCE_IMAGES")
    reference_images = acquire.take_set_of_reference_images(
        microscope=microscope,
        image_settings=settings.image,
        hfws=[fcfg.REFERENCE_HFW_MEDIUM, fcfg.REFERENCE_HFW_SUPER],
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

    # TODO: CHANGE_CURRENT_HERE

    # beam_shift alignment
    log_status_message(lamella, "ALIGN_LAMELLA")
    _update_status_ui(parent_ui, f"{lamella.info} Aligning Reference Images...")

    # take reference image after milling fiducial
    use_fiducial = settings.protocol["fiducial"]["enabled"]
    if use_fiducial is False:
        lamella.fiducial_area = None # TODO: make this better

    # TODO: CHANGE_CURRENT_HERE

    # define feature
    # stages = patterning._get_milling_stages(
    #     "lamella", lamella.protocol, point=lamella.lamella_position
    # )

    # # filter stage based on the current stage
    # stage_map = {
    #     AutoLamellaWaffleStage.MillRoughCut: 0,
    #     AutoLamellaWaffleStage.MillRegularCut: 1,
    #     AutoLamellaWaffleStage.MillPolishingCut: 2,
    # }

    # idx = stage_map[lamella.state.stage]
    # stages = [stages[idx]]# TODO: make this so user can define a number of stages to run
    # prev current

    # existing_current = microscope.get("current", BeamType.ION)

    # existing_preset = "30 keV; UHR imaging"
    # print(f"------------------ existing current {existing_current} ------------------")
    # print(f'------------------ existing preset {existing_preset} ------------------')

    # if settings.protocol["lamella"]["alignment_current"] in ["Milling", "milling","Milling Current"]:
    #     alignment_current = stages[0].milling.milling_current
    #     alignment_preset = stages[0].milling.preset
    #     print(f'---------------using milling current--------------------')
    # else:
    #     print(f'---------------using imaging current--------------------')
    #     alignment_current = existing_current
    #     alignment_preset = existing_preset
        
    # print(f'------------------ alignment current {alignment_current} ------------------')
    # print(f'------------------ alignment preset {alignment_preset} ------------------')
    
    # if isinstance(microscope,(ThermoMicroscope)):
    #     microscope.set(key="current",value=alignment_current,beam_type=BeamType.ION)
    # elif isinstance(microscope,TescanMicroscope):
    #     microscope.set(key="preset",value=alignment_preset,beam_type=BeamType.ION)

    settings.image.save = True
    settings.image.hfw = fcfg.REFERENCE_HFW_SUPER
    settings.image.beam_type = BeamType.ION
    settings.image.label = f"alignment_target_{lamella.state.stage.name}"
    ref_image = FibsemImage.load(os.path.join(lamella.path, f"ref_alignment_ib.tif"))
    # for _ in range(
    #             int(settings.protocol["lamella"]["beam_shift_attempts"])
    #         ):
        # settings.image.reduced_area = lamella.fiducial_area
    settings.image.beam_type = BeamType.ION
    alignment.beam_shift_alignment(microscope, settings.image, 
                                    ref_image=ref_image,
                                        reduced_area=lamella.fiducial_area)

    settings.image.reduced_area = None

    # # TODO: CHANGE_CURRENT_BACK
    # if isinstance(microscope,(ThermoMicroscope)):
    #     microscope.set(key="current",value=existing_current,beam_type=BeamType.ION)
    # elif isinstance(microscope,TescanMicroscope):
    #     microscope.set(key="preset",value=existing_preset, beam_type=BeamType.ION)

    # take reference images
    _update_status_ui(parent_ui, f"{lamella.info} Acquiring Reference Images...")
    settings.image.label = f"ref_{lamella.state.stage.name}_start"
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)
    _set_images_ui(parent_ui, eb_image, ib_image)


    # define feature
    log_status_message(lamella, "MILL_LAMELLA")
    stages = patterning._get_milling_stages(
        "lamella", lamella.protocol, point=Point.__from_dict__(lamella.protocol["lamella"]["point"])
    )

    # filter stage based on the current stage
    stage_map = {
        AutoLamellaWaffleStage.MillRoughCut: 0,
        AutoLamellaWaffleStage.MillRegularCut: 1,
        AutoLamellaWaffleStage.MillPolishingCut: 2,
    }

    supervise_map = {
        AutoLamellaWaffleStage.MillRoughCut: "mill_rough",
        AutoLamellaWaffleStage.MillRegularCut: "mill_regular",
        AutoLamellaWaffleStage.MillPolishingCut: "mill_polishing",
    }
    validate = settings.protocol["options"]["supervise"].get(supervise_map[lamella.state.stage], True)

    idx = stage_map[lamella.state.stage]
    if idx in [0, 1]:
        stages = [stages[idx]]
    else:
        stages = stages[idx:]
        if not isinstance(stages, list):
            stages = [stages]
    
    stages = _validate_mill_ui(stages, parent_ui,
        msg=f"Press Run Milling to mill the Trenches for {lamella._petname}. Press Continue when done.",
        validate=validate,
    )

    # TODO: refactor this so it is like the original protocol
    lamella.protocol[lamella.state.stage.name] = deepcopy(patterning._get_protocol_from_stages(stages))
    lamella.protocol[lamella.state.stage.name]["point"] = stages[0].pattern.point.__to_dict__()
    
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

    return lamella


def setup_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    lamella: Lamella,
    parent_ui: AutoLamellaUI = None,
) -> Lamella:

    validate = settings.protocol["options"]["supervise"].get("setup_lamella", True)
    settings.image.save_path = lamella.path

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
    _feature_name = "notch" if settings.protocol["notch"]["enabled"]  else "microexpansion"
    protocol = lamella.protocol if _feature_name in lamella.protocol else settings.protocol
    NOTCH_H_OFFSET = 0.5e-6                     
    feature_position = Point.__from_dict__(protocol[_feature_name].get("point", 
            {"x":lamella_position.x + stages[0].pattern.protocol["lamella_width"] / 2 + NOTCH_H_OFFSET, 
            "y": lamella_position.y} if _feature_name == "notch" else {"x": 0, "y": 0})) 
    feature_stage = patterning._get_milling_stages(_feature_name, protocol, feature_position)
    stages += feature_stage

    # fiducial
    if use_fiducial := settings.protocol["fiducial"]["enabled"]:
        protocol = lamella.protocol if "fiducial" in lamella.protocol else settings.protocol
        fiducial_position = Point.__from_dict__(protocol["fiducial"].get("point", {"x": 25e-6, "y": 0})) 
        fiducial_stage = patterning._get_milling_stages("fiducial", protocol, fiducial_position)
        stages += fiducial_stage

    stages =_validate_mill_ui(stages, parent_ui, 
        msg=f"Confirm the positions for the {lamella._petname} milling. Press Continue to Confirm.",
        validate=True,
        milling_enabled=False)
    
    from pprint import pprint
    print("-"*80) 
    pprint(stages)
    print("-"*80)

    # lamella
    n_lamella = len(lamella_stages)
    lamella.protocol["lamella"] = deepcopy(patterning._get_protocol_from_stages(stages[:n_lamella]))
    lamella.protocol["lamella"]["point"] = stages[0].pattern.point.__to_dict__()

    # feature
    n_features = len(feature_stage)
    lamella.protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(stages[n_lamella:n_lamella+n_features]))
    lamella.protocol[_feature_name]["point"] = stages[n_lamella].pattern.point.__to_dict__()

    # fiducial
    if use_fiducial:
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
            msg=f"Milling Fiducial for {lamella._petname}.", 
            validate=False)
    
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
    parent_ui: AutoLamellaUI=None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.ReadyTrench and not lamella._is_failure:
            
            # finish readying the lamella
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            parent_ui.update_experiment_signal.emit(experiment)
            
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1), 
                parent_ui=parent_ui
            )

            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)


    return experiment


def run_undercut_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.MillTrench and not lamella._is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1),
                parent_ui=parent_ui
            )

            lamella = mill_undercut(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)

    # ready lamella
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.MillUndercut and not lamella._is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage.SetupLamella,
                parent_ui=parent_ui,
                _restore_state=False,
            )
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            parent_ui.update_experiment_signal.emit(experiment)

    return experiment

def run_setup_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.SetupLamella and not lamella._is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage(lamella.state.stage.value + 1),
                parent_ui=parent_ui
            )

            lamella = setup_lamella(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)

    return experiment

def run_lamella_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:


    stages = [
        # AutoLamellaWaffleStage.ReadyLamella,
        AutoLamellaWaffleStage.MillFeatures,
        AutoLamellaWaffleStage.MillRoughCut,
        AutoLamellaWaffleStage.MillRegularCut,
        AutoLamellaWaffleStage.MillPolishingCut,
    ]
    for stage in stages:
        for lamella in experiment.positions:
            if lamella.state.stage == AutoLamellaWaffleStage(stage.value - 1) and not lamella._is_failure:
                lamella = start_of_stage_update(microscope, lamella, stage, parent_ui)
                lamella = WORKFLOW_STAGES[lamella.state.stage](microscope, settings, lamella, parent_ui)
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

                parent_ui.update_experiment_signal.emit(experiment)


    # finish
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.MillPolishingCut and not lamella._is_failure:
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.Finished, parent_ui, _restore_state=False)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            parent_ui.update_experiment_signal.emit(experiment)

    return experiment


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
        while parent_ui._MILLING_RUNNING:
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