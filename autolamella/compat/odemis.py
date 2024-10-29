import os
from copy import deepcopy
from datetime import datetime
from typing import List

from fibsem.microscopes.odemis_microscope import add_odemis_path
from fibsem.patterning import get_milling_stages, get_protocol_from_stages
from fibsem.structures import FibsemImage, FibsemStagePosition
from fibsem.utils import save_yaml

from autolamella.structures import AutoLamellaStage, Experiment, Lamella, LamellaState
from autolamella.waffle import run_autolamella
from autolamella.workflows.core import log_status_message

add_odemis_path()

from odemis.acq.feature import CryoFeature


def create_lamella_from_feature(feature: CryoFeature, 
                                path: str,
                                num: int,
                                reference_image_path: str,
                                workflow_stage: AutoLamellaStage = AutoLamellaStage.SetupLamella) -> Lamella:
    """Create a Lamella object from a CryoFeature object."""
    pos = FibsemStagePosition.from_odemis_dict(feature.stage_pos.value)

    # get the microscope state from the reference image
    image: FibsemImage = FibsemImage.load_odemis_image(reference_image_path)
    state = deepcopy(image.metadata.microscope_state)

    # create the lamella with the correct state
    lamella = Lamella(
            _petname=feature.name.value,
            path=path,
            _number=num,
            state=LamellaState(
                stage=workflow_stage,
                microscope_state=state,
                start_timestamp=datetime.timestamp(datetime.now()),
            ),
        )

    log_status_message(lamella, "STARTED") # for logging

    # update the position
    lamella.state.microscope_state.stage_position = deepcopy(pos)
    lamella.state.microscope_state.stage_position.name = lamella._petname

    # save the reference image in required format and location
    save_reference_image(reference_image_path, lamella.path)

    return lamella

def save_reference_image(odemis_image_path: str, path: str, filename: str = "ref_alignment_ib") -> None:
    """Save odemis reference image as fibsem image for use in autolamella alignment."""
    
    # open odemis image, and convert to fibsem
    image = FibsemImage.load_odemis_image(odemis_image_path)
    
    # adjust md
    image.metadata.image_settings.save = True
    image.metadata.image_settings.path = path
    image.metadata.image_settings.filename = filename
    
    # save
    image.save()


def create_experiment_from_odemis(path: str, protocol: dict, name: str = "AutoLamella", program: str = "Odemis", method: str = "on-grid") -> Experiment:
    """Create an experiment from an Odemis project folder."""

    experiment_name = f"{name}-{os.path.basename(path)}"
    experiment = Experiment(path=path, name=experiment_name, program=program, method=method)
    experiment.save()

    # save the protocol
    save_yaml(os.path.join(experiment.path, "protocol.yaml"), protocol)

    return experiment

def load_experiment(path: str) -> Experiment:
    """Load an experiment from a path."""
    return Experiment.load(path)

def add_features_to_experiment(experiment: Experiment, features: List[CryoFeature], protocol: dict) -> Experiment:
    """Add features to an experiment."""
    odemis_project_path = os.path.dirname(experiment.path)

    for feature in features:
    
        # reference image path
        reference_image_path = os.path.join(odemis_project_path, "test-image-FIBSEM-001.ome.tiff") 
        # reference_image_path = os.path.join(odemis_project_path, f"{feature.name.value}-Reference-FIB.ome.tiff") # TODO: update for each feature

        # create lamella
        lamella = create_lamella_from_feature(feature,
                                        path=experiment.path, 
                                        num=len(experiment.positions) + 1, 
                                        reference_image_path=reference_image_path,
                                        workflow_stage=AutoLamellaStage.ReadyLamella)
        # add milling protocol
        for k in protocol["milling"].keys():
            stages = get_milling_stages(k, protocol["milling"])
            lamella.protocol[k] = get_protocol_from_stages(stages)
            lamella.protocol[k]["point"] = stages[0].pattern.point.to_dict()
            # required: point, pattern_type, cross_section, depth, trench_height, width, height
            # milling current
            # each trench stage should be 0.5um less wide than the previous one
        
        # TODO: this currently uses the same protocol for all lamellae, 
        # update to use different protocols for each lamella based on what the user selects in the ui

        experiment.positions.append(deepcopy(lamella))
        experiment.save()
    return experiment