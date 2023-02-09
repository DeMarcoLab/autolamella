from dataclasses import dataclass, asdict
from fibsem.structures import MicroscopeState, FibsemImage, Point, FibsemRectangle
import fibsem.utils as utils
from pathlib import Path
from enum import Enum
import yaml
import os
import pandas as pd
from datetime import datetime


class MovementMode(Enum):
    Stable = 1
    Eucentric = 2
    # Needle = 3

class MovementType(Enum):
    StableEnabled = 0 
    EucentricEnabled = 1
    TiltEnabled = 2

class AutoLamellaStage(Enum):
    Setup = 0
    FiducialMilled = 1
    RoughtCut = 2
    RegularCut = 3
    PolishingCut = 4

@dataclass
class LamellaState:
    microscope_state: MicroscopeState
    stage: AutoLamellaStage
    start_timestamp: float = datetime.timestamp(datetime.now())
    end_timestamp: float = None

    def __to_dict__(self):
        return {
            "microscope_state": self.microscope_state.__to_dict__(),
            "stage": self.stage,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
        }
    
    @classmethod
    def __from_dict__(cls, data):
        state = MicroscopeState.__from_dict__(data["microscope_state"])
        return cls(
            microscope_state=state,
            stage=data["stage"],
            start_timestamp=data["start_timestamp"],
            end_timestamp=data["end_timestamp"]
        )
    


@dataclass
class Lamella:
    state: LamellaState = None
    reference_image: FibsemImage = None
    path: Path = None
    fiducial_centre: Point = None
    fiducial_area: FibsemRectangle = None
    lamella_centre: Point = None
    lamella_area: FibsemRectangle = None
    lamella_number: int = None
    history: list[AutoLamellaStage] = None

    def __to_dict__(self):
        return {
            "state": self.state.__to_dict__(),
            "reference_image": self.reference_image,
            "path": self.path,
            "fiducial_centre": self.fiducial_centre.__to_dict__(),
            "fiducial_area": self.fiducial_area.__to_dict__(),
            "lamella_centre": self.lamella_centre.__to_dict__(),
            "lamella_area": self.lamella_area.__to_dict__(),
            "lamella_number": self.lamella_number,
            "history": self.history,
        }

    @classmethod
    def __from_dict__(cls, data):
        state = LamellaState().__from_dict__(data["state"])
        reference_image = data["reference_image"]
        fiducial_centre = Point.__from_dict__(data["fiducial_centre"])
        fiducial_area = FibsemRectangle.__from_dict__(data["fiducial_area"])
        lamella_centre = Point.__from_dict__(data["lamella_centre"])
        lamella_area = FibsemRectangle.__from_dict__(data["lamella_area"])
        return cls(
            state=state,
            reference_image=reference_image,
            path=data["path"],
            fiducial_centre=fiducial_centre,
            fiducial_area=fiducial_area,
            lamella_centre=lamella_centre,
            lamella_area=lamella_area,
            lamella_number=data["lamella_number"],
            history=data["history"],
        )

class Experiment: 
    def __init__(self, path: Path = None, name: str = "default") -> None:

        self.name: str = name
        self.path: Path = utils.make_logging_directory(path=path, name=name)
        self.log_path: Path = utils.configure_logging(
            path=self.path, log_filename="logfile"
        )

        self.positions: list[Lamella] = []

    def __to_dict__(self) -> dict:

        state_dict = {
            "name": self.name,
            "path": self.path,
            "log_path": self.log_path,
            "positions": [lamella.__to_dict__() for lamella in self.positions],
        }

        return state_dict

    def save(self) -> None:
        """Save the sample data to yaml file"""

        with open(os.path.join(self.path, f"{self.name}.yaml"), "w") as f:
            yaml.dump(self.__to_dict__(), f, indent=4)

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
                "number": lamella.lamella_number,
                #"petname": lamella._petname,  # what?
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
        if os.path.exists(fname):
            with open(fname, "r") as f:
                sample_dict = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"No file with name {fname} found.")

        # create sample
        path = os.path.dirname(sample_dict["path"])
        name = sample_dict["name"]
        experiment = Experiment(path=path, name=name)

        # load lamella from dict
        for lamella_dict in sample_dict["positions"]:
            lamella = Lamella.__from_dict__(path=experiment.path, lamella_dict=lamella_dict)
            experiment.positions[lamella.lamella_number] = lamella

        return experiment