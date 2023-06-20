
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



from autolamella import waffle as wfl

PROTOCOL_PATH = r"C:\Users\pcle0002\Documents\repos\autolamella\autolamella\protocol_waffle.yaml"
microscope, settings = utils.setup_session(manufacturer="Demo", protocol_path=PROTOCOL_PATH)

PATH = os.path.join(os.getcwd(), "waffle")

experiment = Experiment(path=PATH, name=f"waffle-demo-{utils.current_timestamp()}")

print(experiment)

experiment = wfl.select_positions(microscope, settings, experiment)
experiment.save()

from autolamella.structures import AutoLamellaWaffleStage


for lamella in experiment.positions:

    print(lamella._petname, lamella.state.stage)

    lamella = wfl.start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.MillTrench)

    # lamella = wfl.mill_trench(microscope, settings, lamella)

    experiment = wfl.end_of_stage_update(microscope, experiment, lamella)
    print(experiment.positions[0].state.stage)

    print("-"*80)


