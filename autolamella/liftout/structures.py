import os
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

import pandas as pd
import petname
import yaml
from fibsem import utils as fibsem_utils
from fibsem.structures import (FibsemImage, FibsemState, MicroscopeState,
                               ReferenceImages, Point)

from autolamella.liftout.config import config as cfg


class AutoLiftoutStage(Enum):
    Setup = auto()
    MillTrench = auto()
    MillUndercut = auto()
    Liftout = auto()
    Landing = auto()
    SetupPolish = auto()
    MillRoughCut = auto()
    MillRegularCut = auto()
    MillPolishingCut = auto()
    Finished = auto()
    
class Experiment: 
    def __init__(self, path: Path = None, name: str = cfg.EXPERIMENT_NAME, program: str = "AutoLiftout", method: str = "AutoLiftout") -> None:


        self.name: str = name
        self._id = str(uuid.uuid4())
        self.path: Path = fibsem_utils.make_logging_directory(path=path, name=name)
        self.log_path: Path = fibsem_utils.configure_logging(
            path=self.path, log_filename="logfile"
        )
        self._created_at: float = datetime.timestamp(datetime.now())


        # TODO: user/data management (e.g. user, sample, id, etc.)

        self.state = None
        self.positions: list[Lamella] = []

        self.program = program
        self.method = method


    def __to_dict__(self) -> dict:

        state_dict = {
            "name": self.name,
            "_id": self._id,
            "path": self.path,
            "log_path": self.log_path,
            "positions": [lamella.__to_dict__() for lamella in self.positions],
            "created_at": self._created_at,
            "program": self.program,
            "method": self.method,
        }

        return state_dict

    def update(self, lamella: 'Lamella') -> None:
        self.save()

    def save(self) -> None:
        """Save the experiment data to yaml file"""

        with open(os.path.join(self.path, "experiment.yaml"), "w") as f:
            yaml.dump(self.__to_dict__(), f, indent=4)

    def __repr__(self) -> str:

        return f"""Experiment: 
        Path: {self.path}
        State: {self.state}
        Lamella: {len(self.positions)}
        """
    
    def __to_dataframe__(self) -> pd.DataFrame:

        lamella_list = []
        lamella: Lamella
        for lamella in self.positions:

            # lamella
            lamella_dict = {
                "experiment_name": self.name,
                "experiment_path": self.path,
                "experiment_created_at": self._created_at,
                "experiment_id": self._id, 
                "program": self.program,
                "method": self.method,
                "number": lamella._number,
                "petname": lamella._petname,
                "path": lamella.path,
                "lamella.x": lamella.lamella_state.absolute_position.x,
                "lamella.y": lamella.lamella_state.absolute_position.y,
                "lamella.z": lamella.lamella_state.absolute_position.z,
                "lamella.r": lamella.lamella_state.absolute_position.r,
                "lamella.t": lamella.lamella_state.absolute_position.t,
                "lamella.coordinate_system": lamella.lamella_state.absolute_position.coordinate_system,
                "landing.x": lamella.landing_state.absolute_position.x,
                "landing.y": lamella.landing_state.absolute_position.y,
                "landing.z": lamella.landing_state.absolute_position.z,
                "landing.r": lamella.landing_state.absolute_position.r,
                "landing.t": lamella.landing_state.absolute_position.t,
                "landing.coordinate_system": lamella.landing_state.absolute_position.coordinate_system,
                "landing_selected": lamella.landing_selected,
                "current_stage": lamella.state.stage.name,
                "last_timestamp": lamella.state.microscope_state.timestamp,
                "history: ": len(lamella.history),

            }

            lamella_list.append(lamella_dict)

        df = pd.DataFrame.from_dict(lamella_list)

        return df


    def to_dataframe_v2(self) -> pd.DataFrame:

        edict = {
            "name": self.name,
            "path": self.path,
            "date": self._created_at,
            "experiment_id": self._id,
            "program": self.program,
            "method": self.method, 
            "num_lamella": len(self.positions),
        }

        df = pd.DataFrame([edict])

        return df

    @staticmethod
    def load(fname: Path) -> 'Experiment':
        """Load a sample from disk."""

        # read and open existing yaml file
        if os.path.exists(fname):
            with open(fname, "r") as f:
                ddict = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"No file with name {fname} found.")

        # create sample
        path = os.path.dirname(ddict["path"])
        name = ddict["name"]
        experiment = Experiment(path=path, name=name)
        experiment._created_at = ddict.get("created_at", None)
        experiment._id = ddict.get("_id", "NULL")
        experiment.program = ddict.get("program", "AutoLiftout")
        experiment.method = ddict.get("method", "AutoLiftout") # TODO: implement

        # load lamella from dict
        for lamella_dict in ddict["positions"]:
            lamella = Lamella.__from_dict__(path=experiment.path, lamella_dict=lamella_dict)
            experiment.positions.append(deepcopy(lamella))

        return experiment

# TODO: move to fibsem?
# TODO: need to inherit the state class?
class Lamella:
    def __init__(self, path: Path, number: int = 0, _petname: str = None) -> None:

        self._number: int = number
        self._id = str(uuid.uuid4())
        if _petname is None:
            self._petname = f"{self._number:02d}-{petname.generate(2)}"
        else:
            self._petname = _petname
        self._created_at: float = datetime.timestamp(datetime.now())

        # filesystem
        self.base_path = path
        self.path = os.path.join(self.base_path, self._petname)
        os.makedirs(self.path, exist_ok=True)

        self.lamella_state: MicroscopeState = MicroscopeState()
        self.landing_state: MicroscopeState = MicroscopeState()

        self.landing_selected: bool = False
        self.is_failure: bool = False

        # lamella specific protocol
        self.protocol: dict = {}


        self.state: AutoLiftoutState = AutoLiftoutState()

        # state history
        self.history: list[AutoLiftoutState] = []

    def __repr__(self) -> str:

        return f"""
        Lamella {self._number} ({self._petname}). 
        Lamella Coordinates: {self.lamella_state.absolute_position}, 
        Landing Coordinates: {self.landing_state.absolute_position}, 
        Current Stage: {self.state.stage},
        History: {len(self.history)} stages completed ({[state.stage.name for state in self.history]}).
        """
    
    @property
    def info(self):
        return f"Lamella {self._petname} [{self.state.stage.name}]"

    def __to_dict__(self):

        state_dict = {
            "id": str(self._id),
            "petname": self._petname,
            "number": self._number,
            "base_path": self.base_path,
            "path": self.path,
            "landing_selected": self.landing_selected,
            "is_failure": self.is_failure,
            "lamella_state": self.lamella_state.__to_dict__(),
            "landing_state": self.landing_state.__to_dict__(),
            "state": self.state.__to_dict__(),
            "protocol": self.protocol,
            "history": [state.__to_dict__() for state in self.history],
            "created_at": self._created_at,
        }

        return state_dict

    def load_reference_image(self, fname) -> FibsemImage:
        """Load a specific reference image for this lamella from disk
        Args:
            fname: str
                the filename of the reference image to load
        Returns:
            adorned_img: AdornedImage
                the reference image loaded as an AdornedImage
        """

        adorned_img = FibsemImage.load(os.path.join(self.path, f"{fname}.tif"))

        return adorned_img

    @staticmethod
    def __from_dict__(path: str, lamella_dict: dict) -> 'Lamella':

        lamella = Lamella(
            path=path, number=lamella_dict["number"], _petname=lamella_dict["petname"]
        )

        lamella._petname = lamella_dict["petname"]
        lamella._id = lamella_dict["id"]

        # load stage positions from yaml
        lamella.lamella_state = MicroscopeState.__from_dict__(lamella_dict["lamella_state"])
        lamella.landing_state = MicroscopeState.__from_dict__(lamella_dict["landing_state"])
        lamella.landing_selected = bool(lamella_dict["landing_selected"])
        lamella.is_failure = bool(lamella_dict.get("is_failure", False))

        # load protocol
        lamella.protocol = deepcopy(lamella_dict.get("protocol", {}))

        # load current state
        lamella.state = AutoLiftoutState.__from_dict__(lamella_dict["state"])

        # load history
        lamella.history = [
            AutoLiftoutState.__from_dict__(state_dict)
            for state_dict in lamella_dict["history"]
        ]

        return lamella

    # convert to method
    def get_reference_images(self, label: str) -> ReferenceImages:
        reference_images = ReferenceImages(
            low_res_eb=self.load_reference_image(f"{label}_low_res_eb"),
            high_res_eb=self.load_reference_image(f"{label}_high_res_eb"),
            low_res_ib=self.load_reference_image(f"{label}_low_res_ib"),
            high_res_ib=self.load_reference_image(f"{label}_high_res_ib"),
        )

        return reference_images

@dataclass
class AutoLiftoutState(FibsemState):
    stage: AutoLiftoutStage = AutoLiftoutStage.Setup
    microscope_state: MicroscopeState = MicroscopeState()
    start_timestamp: float = datetime.timestamp(datetime.now())
    end_timestamp: float = None

    def __to_dict__(self) -> dict:

        state_dict = {
            "stage": self.stage.name,
            "microscope_state": self.microscope_state.__to_dict__(),
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
        }

        return state_dict

    @classmethod
    def __from_dict__(self, state_dict: dict) -> 'AutoLiftoutState':

        autoliftout_state = AutoLiftoutState(
            stage=AutoLiftoutStage[state_dict["stage"]],
            microscope_state=MicroscopeState.__from_dict__(state_dict["microscope_state"]),
            start_timestamp=state_dict["start_timestamp"],
            end_timestamp=state_dict["end_timestamp"],
        )

        return autoliftout_state





# Experiment:
#   data_path: Path
#
#   positions: [Lamella, Lamella, Lamella]

# Lamella
#   lamella_state: MicroscopeState
#   landing_state: MicroscopeState
#   lamella_ref_images: ReferenceImages
#   landing_ref_images: ReferenceImages
#   state: AutoLiftoutState
#       stage: AutoLiftoutStage
#       microscope_state: MicroscopeState
#           eb_settings: BeamSettings
#           ib_settings: BeamSettings
#           absolute_position: StagePosition


######################## UTIL ########################


def create_experiment(experiment_name: str, path: Path = None):

    # create unique experiment name
    exp_name = f"{experiment_name}-{fibsem_utils.current_timestamp()}"

    # create experiment data struture
    experiment = Experiment(path=path, name=exp_name)

    # save experiment to disk
    experiment.save()

    return experiment


def load_experiment(path: Path) -> Experiment:

    sample_fname = os.path.join(path, "experiment.yaml")

    if not os.path.exists(sample_fname):
        raise ValueError(f"No experiment file found for this path: {path}")

    return Experiment.load(fname=sample_fname)



