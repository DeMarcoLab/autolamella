import logging
import os
from copy import deepcopy
from datetime import datetime
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
from fibsem import acquire, milling, patterning, utils
from fibsem.microscope import FibsemMicroscope
from fibsem.patterning import FibsemMillingStage
from fibsem.structures import (BeamType, FibsemStagePosition,
                               MicroscopeSettings, Point)

from autolamella.structures import (AutoLamellaStage, AutoLamellaWaffleStage,
                                    Experiment, Lamella)


def select_positions(microscope: FibsemMicroscope, settings: MicroscopeSettings, experiment: Experiment) -> Experiment:
    # move flat to ION
    microscope.move_flat_to_beam(settings=settings, beam_type=BeamType.ION)

    response = input("Enter y to set this position for the lamella.")
    response = True if "y" in response else False    
    while response:
        # create another lamella
        # add to experiment
        # set it to start at the current grid, Liftout State
        num_lamella = len(experiment.positions)
        lamella = Lamella(path=experiment.path, lamella_number=num_lamella
        )  # TODO: change when change to list
        lamella.state.stage = AutoLamellaWaffleStage.Setup
        lamella.state.microscope_state = (
            microscope.get_current_microscope_state()
        )

        settings.image.save_path = lamella.path

        acquire.take_set_of_reference_images(
            microscope=microscope,
            image_settings=settings.image,
            hfws=[150e-6, 80e-6],
            label="ref_initial_position",
        )


        experiment.positions.append(deepcopy(lamella))

        response = input("Enter y to set this position for the lamella.")
        response = True if "y" in response else False 

    return experiment   


def mill_trench(microscope: FibsemMicroscope, settings: MicroscopeSettings, lamella: Lamella, parent_ui = None) -> Lamella:
    
    settings.image.save_path = lamella.path 

    # define trench
    settings.protocol["trench"]["cleaning_cross_section"] = False
    stages = patterning._get_milling_stages("trench", settings.protocol, point=lamella.lamella_centre)

    # TODO: draw milling stages on UI

    # mill stages
    milling.mill_stages(microscope, settings, stages)
    
    # take reference images
    settings.image.label = "ref_trench_high_res"
    settings.image.hfw = settings.protocol["trench"]["hfw"]
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)

    if parent_ui is not None:
        parent_ui.image_widget.update_viewer(eb_image.data, BeamType.ELECTRON.name )
        parent_ui.image_widget.update_viewer(ib_image.data, BeamType.ION.name )

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

    logging.info(f"STATUS | {lamella._petname} | {lamella.state.stage} | FINISHED")

    return experiment


def start_of_stage_update(
    microscope: FibsemMicroscope, lamella: Lamella, next_stage: AutoLamellaStage,
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
    logging.info(f"STATUS | {lamella._petname} | {lamella.state.stage} | STARTED")

    return lamella



def run_trench_milling(microscope: FibsemMicroscope, settings: MicroscopeSettings, experiment: Experiment, parent_ui = None) -> Experiment:

    for lamella in experiment.positions:
        logging.info(f"------------------------{lamella._name}----------------------------------------")
        if lamella.state.stage == AutoLamellaWaffleStage.Setup:
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.MillTrench)
        
            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella)
        logging.info('----------------------------------------------------------------------------------------')
    return experiment