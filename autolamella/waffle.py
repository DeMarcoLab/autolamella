from fibsem import utils, acquire, patterning, milling
from fibsem.structures import BeamType, FibsemStagePosition, Point
from fibsem.patterning import FibsemMillingStage

from pprint import pprint
import numpy as np
import matplotlib.pyplot as plt


from fibsem.microscope import FibsemMicroscope
from fibsem.structures import MicroscopeSettings
from autolamella.structures import Lamella, Experiment, AutoLamellaStage

from copy import deepcopy
import os


def select_positions(microscope: FibsemMicroscope, settings: MicroscopeSettings, experiment: Experiment) -> Experiment:
    # move flat to ION
    microscope.move_flat_to_beam(settings=settings, beam_type=BeamType.ION)

    response = input("Land another lamella?")
    response = True if "y" in response else False    
    while response:
        # create another lamella
        # add to experiment
        # set it to start at the current grid, Liftout State
        num_lamella = len(experiment.positions)
        lamella = Lamella(path=experiment.path, lamella_number=num_lamella
        )  # TODO: change when change to list
        lamella.state.stage = AutoLamellaStage.Setup
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

        response = input("Land another lamella?")
        response = True if "y" in response else False 

    return experiment   


def mill_trench(microscope: FibsemMicroscope, settings: MicroscopeSettings, lamella: Lamella) -> Lamella:
    
    settings.image.save_path = lamella.path 


    # define trench
    stages = patterning._get_milling_stages("trench", settings.protocol)

    # mill stages
    milling.mill_stages(microscope, settings, stages)
    print("-"*80)
    # take reference images
    settings.image.label = "ref_trench_high_res"
    settings.image.hfw = 80e-6
    settings.image.save = True
    eb_image, ib_image = acquire.take_reference_images(microscope, settings.image)

    return lamella