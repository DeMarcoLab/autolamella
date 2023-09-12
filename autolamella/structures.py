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
import uuid

class AutoLamellaStage(Enum):
    Setup = 0
    FiducialMilled = 1
    MicroExpansion = 2
    RoughCut = 3
    RegularCut = 4
    PolishingCut = 5
    Finished = 6

class AutoLamellaWaffleStage(Enum):
    SetupTrench = auto()
    ReadyTrench = auto()
    MillTrench = auto()
    MillUndercut = auto()
    SetupLamella = auto()
    ReadyLamella = auto()
    MillFeatures = auto()
    MillRoughCut = auto()
    MillRegularCut = auto()
    MillPolishingCut = auto()
    Finished = auto()
    PreSetupLamella = auto()



@dataclass
class LamellaState:
    microscope_state: MicroscopeState = MicroscopeState()
    stage: AutoLamellaWaffleStage = AutoLamellaWaffleStage.SetupTrench
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
    fiducial_area: FibsemRectangle = FibsemRectangle()
    _number: int = 0
    lamella_position: Point = Point()
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
            "fiducial_area": self.fiducial_area.__to_dict__() if self.fiducial_area is not None else None,
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
        fiducial_area = FibsemRectangle.__from_dict__(data["fiducial_area"])
        return cls(
            _petname=data["petname"],
            state=state,
            path=data["path"],
            fiducial_area=fiducial_area,
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
        self._id = str(uuid.uuid4())
        self.path: Path = utils.make_logging_directory(path=path, name=name)
        self.log_path: Path = utils.configure_logging(
            path=self.path, log_filename="logfile"
        )
        self._created_at: float = datetime.timestamp(datetime.now())

        self.positions: list[Lamella] = []
        self.program = "AutoLamella"
        self.method = "AutoLamella"

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

        exp_data = []
        lamella: Lamella
        for lamella in self.positions:

            # lamella
            ldict = {
                "experiment_name": self.name,
                "experiment_path": self.path,
                "experiment_created_at": self._created_at,
                "experiment_id": self._id,
                "program": self.program,
                "method": self.method, 
                "number": lamella._number,
                "petname": lamella._petname,  # what?
                "path": lamella.path,
                "lamella.x": lamella.state.microscope_state.absolute_position.x,
                "lamella.y": lamella.state.microscope_state.absolute_position.y,
                "lamella.z": lamella.state.microscope_state.absolute_position.z,
                "lamella.r": lamella.state.microscope_state.absolute_position.r,
                "lamella.t": lamella.state.microscope_state.absolute_position.t,
                "last_timestamp": lamella.state.microscope_state.timestamp, # dont know if this is the correct timestamp to use here
            }

            exp_data.append(ldict)

        df = pd.DataFrame(exp_data)

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
        path = Path(fname).with_suffix(".yaml")
        if os.path.exists(path):
            with open(path, "r") as f:
                ddict = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"No file with name {path} found.")

        # create sample
        path = os.path.dirname(ddict["path"])
        name = ddict["name"]
        experiment = Experiment(path=path, name=name)
        experiment._created_at = ddict.get("created_at", None)
        experiment._id = ddict.get("_id", "NULL")
        experiment.program = ddict.get("program", "AutoLamella")
        experiment.method = ddict.get("method", "AutoLamella") 

        # load lamella from dict
        for lamella_dict in ddict["positions"]:
            lamella = Lamella.__from_dict__(data=lamella_dict)
            experiment.positions.append(lamella)

        return experiment
    
    def _create_protocol_dataframe(self) -> pd.DataFrame:
        plist = []
        for lamella in self.positions:
            if lamella.protocol:
                for k in lamella.protocol:


                    if "stages" not in lamella.protocol[k]:
                        continue # skip non milling stages
                    #     ddict = lamella.protocol[k]
                    #     if not isinstance(ddict, dict):
                    #         ddict = {k: lamella.protocol[k], "key": k, "milling_stage": 0, "lamella": lamella._petname}
                    #     ddict["milling_stage"] = 0
                    #     ddict["stage"] = k
                    #     ddict["lamella"] = lamella._petname
                    #     plist.append(deepcopy(ddict))


                    else:
                        for i, ddict in enumerate(lamella.protocol[k]["stages"]):

                            ddict["MillingStage"] = i
                            ddict["WorkflowStage"] = k
                            ddict["Lamella"] = lamella._petname

                            plist.append(deepcopy(ddict))

        df = pd.DataFrame(plist)

        # re-order columns starting with lamella, WorkflowStage, MillingStage
        cols = list(df.columns)
        cols.remove("Lamella")
        cols.remove("WorkflowStage")
        cols.remove("MillingStage")
        cols = ["Lamella", "WorkflowStage", "MillingStage"] + cols
        df = df[cols]


        return df

    def _convert_dataframe_to_protocol(self, df: pd.DataFrame) -> None:
        """Convert a dataframe to a protocol."""

        PROTOCOL_KEYS = ["trench", "MillUndercut", "fiducial", "notch", "MillRoughCut", "MillRegularCut", "MillPolishingCut", "microexpansion"]

        df.sort_values(by=["MillingStage"], inplace=True)

        for lamella in self.positions:
            petname = lamella._petname
            print("-"*50, petname, "-"*50)

            df_petname = df[df["Lamella"]==petname].copy(deep=True)

            for k in PROTOCOL_KEYS:
                # convert data frame back to dict

                # sort by milling_stage
                df_filt = df_petname[df_petname["WorkflowStage"]==k].copy(deep=True)

                if df_filt.empty:
                    continue 

                # drop na columns
                df_filt.dropna(axis=1, how="all", inplace=True)

                # drop milling_stage, lamella, stage
                df_filt.drop(columns=["MillingStage", "Lamella", "WorkflowStage"], inplace=True)

                ddict = deepcopy(df_filt.to_dict(orient="records"))

                lamella.protocol[k]["stages"] = deepcopy(ddict)

                from pprint import pprint
                print("KEY: ", k)
                pprint(lamella.protocol[k]["stages"])
                print('-'*100)