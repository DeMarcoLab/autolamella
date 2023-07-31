import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
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
    Setup = auto()
    ReadyTrench = auto()
    MillTrench = auto()
    MillUndercut = auto()
    ReadyLamella = auto()
    SetupLamella = auto()
    MillFeatures = auto()
    MillRoughCut = auto()
    MillRegularCut = auto()
    MillPolishingCut = auto()
    Finished = auto()



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
    path: Path = Path()
    fiducial_centre: Point = Point()
    fiducial_area: FibsemRectangle = FibsemRectangle()
    _number: int = 0
    lamella_position: Point = Point()
    trench_position: Point = Point()
    feature_position: Point = Point()
    history: list[LamellaState] = None
    _petname: str = None
    protocol: dict = None    
    _is_failure: bool = False

    
    def __post_init__(self):
        if self._petname is None:
            self._petname = f"{self._number:02d}-{petname.generate(2)}"
        if self._petname not in self.path:
            self.path = os.path.join(self.path, self._petname)
        os.makedirs(self.path, exist_ok=True)
        if self.protocol is None:
            self.protocol = {}

    def __to_dict__(self):
        if self.history is None:
            self.history = []
        return {
            "petname": self._petname,
            "state": self.state.__to_dict__() if self.state is not None else None,
            "path": str(self.path) if self.path is not None else None,
            "fiducial_centre": self.fiducial_centre.__to_dict__() if self.fiducial_centre is not None else None,
            "fiducial_area": self.fiducial_area.__to_dict__() if self.fiducial_area is not None else None,
            "lamella_position": self.lamella_position.__to_dict__(),
            "trench_position": self.trench_position.__to_dict__(),
            "feature_position": self.feature_position.__to_dict__(),
            "protocol": self.protocol,
            "_number": self._number,
            "history": [state.__to_dict__() for state in self.history] if self.history is not False else [],
            "_is_failure": self._is_failure,
        }

    @property
    def info(self):
        return f"Lamella {self._petname} [{self.state.stage.name}]"

    @classmethod
    def __from_dict__(cls, data):
        state = LamellaState().__from_dict__(data["state"])
        fiducial_centre = Point.__from_dict__(data["fiducial_centre"])
        fiducial_area = FibsemRectangle.__from_dict__(data["fiducial_area"])
        lamella_position = Point.__from_dict__(data.get("lamella_position", {"x": 0, "y": 0}))
        trench_position = Point.__from_dict__(data.get("trench_position", {"x": 0, "y": 0}))
        feature_position = Point.__from_dict__(data.get("feature_position", {"x": 0, "y": 0}))
        return cls(
            _petname=data["petname"],
            state=state,
            path=data["path"],
            fiducial_centre=fiducial_centre,
            fiducial_area=fiducial_area,
            lamella_position=lamella_position,
            trench_position = trench_position,
            feature_position = feature_position,
            protocol=data.get("protocol", {}),
            _number=data["_number"],
            history=[LamellaState().__from_dict__(state) for state in data["history"]],
            _is_failure=data.get("_is_failure", False),
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
                "number": lamella._number,
                "petname": lamella._petname,  # what?
                "path": lamella.path,
                "lamella.x": lamella.state.microscope_state.absolute_position.x,
                "lamella.y": lamella.state.microscope_state.absolute_position.y,
                "lamella.z": lamella.state.microscope_state.absolute_position.z,
                "lamella.r": lamella.state.microscope_state.absolute_position.r,
                "lamella.t": lamella.state.microscope_state.absolute_position.t,
                "lamella.position.x": lamella.lamella_position.x,
                "lamella.position.y": lamella.lamella_position.y,
                "trench.position.x": lamella.trench_position.x,
                "trench.position.y": lamella.trench_position.y,
                "feature.position.x": lamella.feature_position.x,
                "feature.position.y": lamella.feature_position.y,
                "lamella.history": lamella.history,
                "feature.position.x": lamella.feature_position.x,
                "feature.position.y": lamella.feature_position.y,
                "fiducial.centre.x": lamella.fiducial_centre.x,
                "fiducial.centre.y": lamella.fiducial_centre.y,
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