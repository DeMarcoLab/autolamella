import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import fibsem.utils as utils
import pandas as pd
import petname
import yaml
from fibsem.structures import (FibsemImage, FibsemRectangle, MicroscopeState,
                               Point)


class AutoLamellaStage(Enum):
    Setup = 0
    FiducialMilled = 1
    MicroExpansion = 2
    RoughCut = 3
    RegularCut = 4
    PolishingCut = 5
    Finished = 6

class AutoLamellaWaffleStage(Enum):
    Setup = 0
    MillTrench = 1
    MillUndercut = 2
    MillFeatures = 3
    MillRoughCut = 4
    MillRegularCut = 5
    MillPolishingCut = 6
    Finished = 7



@dataclass
class LamellaState:
    microscope_state: MicroscopeState = MicroscopeState()
    stage: AutoLamellaWaffleStage = AutoLamellaWaffleStage.Setup
    start_timestamp: float = datetime.timestamp(datetime.now())
    end_timestamp: float = None

    def __to_dict__(self):
        return {
            "microscope_state": self.microscope_state.__to_dict__() if self.microscope_state is not None else "not defined",
            "stage": self.stage.name,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
        }
    
    @classmethod
    def __from_dict__(cls, data):
        state = MicroscopeState.__from_dict__(data["microscope_state"])
        return cls(
            microscope_state=state,
            stage=AutoLamellaWaffleStage[data["stage"]],
            start_timestamp=data["start_timestamp"],
            end_timestamp=data["end_timestamp"]
        )
    

@dataclass
class Lamella:
    state: LamellaState = LamellaState()
    reference_image: FibsemImage = None
    path: Path = Path()
    fiducial_centre: Point = Point()
    fiducial_area: FibsemRectangle = FibsemRectangle()
    lamella_centre: Point = Point()
    lamella_number: int = 0
    trench_centre: Point = Point()
    mill_microexpansion: bool = False
    history: list[LamellaState] = None
    _petname: str = None
    _name: str = None
    
    def __post_init__(self):
        if self._petname is None:
            self._petname = f"{petname.generate(2)}"
        self._name = f"{self.lamella_number:02d}-{self._petname}"
        self.path = os.path.join(self.path, self._name)
        os.makedirs(self.path, exist_ok=True)

    def __to_dict__(self):
        if self.history is None:
            self.history = []
        return {
            "petname": self._petname,
            "state": self.state.__to_dict__() if self.state is not None else "Not defined",
            "reference_image": str(os.path.join(self.path, f"{self.reference_image.metadata.image_settings.label}.tif")) if self.reference_image is not None else "Not defined",
            "path": str(self.path) if self.path is not None else "Not defined",
            "fiducial_centre": self.fiducial_centre.__to_dict__() if self.fiducial_centre is not None else "Not defined",
            "fiducial_area": self.fiducial_area.__to_dict__() if self.fiducial_area is not None else "Not defined",
            "lamella_centre": self.lamella_centre.__to_dict__() if self.lamella_centre is not None else "Not defined",
            "trench_centre": self.trench_centre.__to_dict__() if self.trench_centre is not None else "Not defined",
            "lamella_number": self.lamella_number if self.lamella_number is not None else "Not defined",
            "history": [state.__to_dict__() for state in self.history] if self.history is not False else "Not defined",
        }

    @classmethod
    def __from_dict__(cls, data):
        state = LamellaState().__from_dict__(data["state"])
        fiducial_centre = Point.__from_dict__(data["fiducial_centre"])
        fiducial_area = FibsemRectangle.__from_dict__(data["fiducial_area"])
        lamella_centre = Point.__from_dict__(data["lamella_centre"])
        trench_centre = Point.__from_dict__(data["trench_centre"])
        return cls(
            _petname=data["petname"],
            state=state,
            reference_image=None,
            path=data["path"],
            fiducial_centre=fiducial_centre,
            fiducial_area=fiducial_area,
            lamella_centre=lamella_centre,
            trench_centre = trench_centre,
            lamella_number=data["lamella_number"],
            history=[LamellaState().__from_dict__(state) for state in data["history"]],
        )
    
    def update(self, stage: AutoLamellaWaffleStage):
        """_summary_

        Args:
            stage (AutoLamellaWaffleStage): current stage of the lamella

        Returns:
            lamella: lamella with udpated stage and history
        """
        self.state.end_timestamp = datetime.timestamp(datetime.now())
        self.history.append(deepcopy(self.state))
        self.state.stage = AutoLamellaWaffleStage(stage)
        self.state.start_timestamp = datetime.timestamp(datetime.now())
        return self

class Experiment: 
    def __init__(self, path: Path, name: str = "AutoLamella") -> None:

        self.name: str = name
        self.path: Path = utils.make_logging_directory(path=path, name=name)
        self.log_path: Path = utils.configure_logging(
            path=self.path, log_filename="logfile"
        )
        self._created_at: float = datetime.timestamp(datetime.now())

        self.positions: list[Lamella] = []

    def __to_dict__(self) -> dict:

        state_dict = {
            "name": self.name,
            "path": self.path,
            "log_path": self.log_path,
            "positions": [lamella.__to_dict__() for lamella in self.positions],
            "created_at": self._created_at,
        }

        return state_dict

    def save(self) -> None:
        """Save the sample data to yaml file"""

        with open(os.path.join(self.path, f"experiment.yaml"), "w") as f:
            yaml.safe_dump(self.__to_dict__(), f, indent=4)

        # for lamella in self.positions:
        #     path_image = os.path.join(self.path, f"{str(lamella.lamella_number).rjust(2, '0')}-{lamella._petname}", lamella.reference_image.metadata.image_settings.label)
        #     if lamella.reference_image is not None:
        #         lamella.reference_image.save(path_image)

    def __repr__(self) -> str:

        return f"""Experiment: 
        Path: {self.path}
        Positions: {len(self.positions)}
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
                "number": lamella.lamella_number,
                "petname": lamella._petname,  # what?
                "name": lamella._name,
                "path": lamella.path,
                "lamella.x": lamella.state.microscope_state.absolute_position.x,
                "lamella.y": lamella.state.microscope_state.absolute_position.y,
                "lamella.z": lamella.state.microscope_state.absolute_position.z,
                "lamella.r": lamella.state.microscope_state.absolute_position.r,
                "lamella.t": lamella.state.microscope_state.absolute_position.t,
                "lamella.centre": lamella.lamella_centre,
                "lamella.history": lamella.history,
                "fiducial.centre": lamella.fiducial_centre,
                "last_timestamp": lamella.state.microscope_state.timestamp, # dont know if this is the correct timestamp to use here
            }

            lamella_list.append(lamella_dict)

        df = pd.DataFrame.from_dict(lamella_list)

        return df

    @staticmethod
    def load(fname: Path) -> 'Experiment':
        """Load a sample from disk."""

        # read and open existing yaml file
        path = Path(fname).with_suffix(".yaml")
        if os.path.exists(path):
            with open(path, "r") as f:
                sample_dict = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"No file with name {path} found.")

        # create sample
        path = os.path.dirname(sample_dict["path"])
        name = sample_dict["name"]
        experiment = Experiment(path=path, name=name)
        experiment._created_at = sample_dict.get("created_at", None)

        # load lamella from dict
        for lamella_dict in sample_dict["positions"]:
            lamella = Lamella.__from_dict__(data=lamella_dict)
            experiment.positions.append(lamella)

        return experiment