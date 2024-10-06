import os
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import List

import fibsem.utils as utils
import pandas as pd
import petname
import yaml
from fibsem.structures import (
    FibsemImage,
    FibsemRectangle,
    MicroscopeState,
    ReferenceImages,
)

from autolamella import config as cfg


class AutoLamellaStage(Enum):
    SetupTrench = auto()
    ReadyTrench = auto()
    MillTrench = auto()
    MillUndercut = auto()
    LiftoutLamella = auto()
    LandLamella = auto()
    SetupLamella = auto()
    ReadyLamella = auto()
    MillRoughCut = auto()
    MillPolishingCut = auto()
    Finished = auto()
    PreSetupLamella = auto()




@dataclass
class LamellaState:
    microscope_state: MicroscopeState = MicroscopeState()
    stage: AutoLamellaStage = AutoLamellaStage.SetupTrench
    start_timestamp: float = datetime.timestamp(datetime.now())
    end_timestamp: float = None

    def to_dict(self):
        return {
            "microscope_state": self.microscope_state.to_dict() if self.microscope_state is not None else "not defined",
            "stage": self.stage.name,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
        }
    
    @classmethod
    def from_dict(cls, data):
        state = MicroscopeState.from_dict(data["microscope_state"])
        return cls(
            microscope_state=state,
            stage=AutoLamellaStage[data["stage"]],
            start_timestamp=data["start_timestamp"],
            end_timestamp=data["end_timestamp"]
        )
    

@dataclass
class Lamella:
    state: LamellaState = LamellaState()
    path: Path = Path()
    fiducial_area: FibsemRectangle = FibsemRectangle()
    _number: int = 0
    history: List[LamellaState] = None
    _petname: str = None
    protocol: dict = None    
    _is_failure: bool = False
    failure_note: str = ""
    failure_timestamp: float = None
    lamella_state: MicroscopeState = MicroscopeState()
    landing_state: MicroscopeState = MicroscopeState()
    landing_selected: bool = False
    _id: str = None

    
    def __post_init__(self):
        if self._petname is None:
            self._petname = f"{self._number:02d}-{petname.generate(2)}"
        if self._petname not in self.path:
            self.path = os.path.join(self.path, self._petname)
        os.makedirs(self.path, exist_ok=True)
        if self.protocol is None:
            self.protocol = {}
        if self.history is None:
            self.history = []

    def to_dict(self):
        if self.history is None:
            self.history = []
        return {
            "petname": self._petname,
            "state": self.state.to_dict() if self.state is not None else None,
            "path": str(self.path) if self.path is not None else None,
            "fiducial_area": self.fiducial_area.to_dict() if self.fiducial_area is not None else None,
            "protocol": self.protocol,
            "_number": self._number,
            "history": [state.to_dict() for state in self.history] if self.history is not False else [],
            "_is_failure": self._is_failure,
            "failure_note": self.failure_note,
            "failure_timestamp": self.failure_timestamp,
            "lamella_state": self.lamella_state.to_dict(),
            "landing_state": self.landing_state.to_dict(),
            "landing_selected": self.landing_selected,
            "id": str(self._id),
        }

    @property
    def info(self):
        return f"Lamella {self._petname} [{self.state.stage.name}]"

    @classmethod
    def from_dict(cls, data):
        state = LamellaState().from_dict(data["state"])
        if data.get("fiducial_area", None) is None:
            fiducial_area = None
        else:
            fiducial_area = FibsemRectangle.from_dict(data["fiducial_area"])
               
        return cls(
            _petname=data["petname"],
            _id=data.get("id", None),
            state=state,
            path=data["path"],
            fiducial_area=fiducial_area,
            protocol=data.get("protocol", {}),
            _number=data.get("_number", data.get("number", 0)),
            history=[LamellaState().from_dict(state) for state in data["history"]],
            _is_failure=data.get("_is_failure", data.get("is_failure", False)),
            failure_note=data.get("failure_note", ""),
            failure_timestamp=data.get("failure_timestamp", None),
            lamella_state = MicroscopeState.from_dict(data.get("lamella_state", MicroscopeState().to_dict())), # tmp solution
            landing_state = MicroscopeState.from_dict(data.get("landing_state", MicroscopeState().to_dict())), # tmp solution
            landing_selected = bool(data.get("landing_selected", False)),
        )
    

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

    # convert to method
    def get_reference_images(self, filename: str) -> ReferenceImages:
        reference_images = ReferenceImages(
            low_res_eb=self.load_reference_image(f"{filename}_low_res_eb"),
            high_res_eb=self.load_reference_image(f"{filename}_high_res_eb"),
            low_res_ib=self.load_reference_image(f"{filename}_low_res_ib"),
            high_res_ib=self.load_reference_image(f"{filename}_high_res_ib"),
        )

        return reference_images
    
class Experiment: 
    def __init__(self, path: Path = None, name: str = cfg.EXPERIMENT_NAME, program: str = "AutoLiftout", method: str = "AutoLiftout") -> None:


        self.name: str = name
        self._id = str(uuid.uuid4())
        self.path: Path = utils.make_logging_directory(path=path, name=name)
        self.log_path: Path = utils.configure_logging(
            path=self.path, log_filename="logfile"
        )
        self._created_at: float = datetime.timestamp(datetime.now())

        self.positions: List[Lamella] = []

        self.program = program
        self.method = method

    def to_dict(self) -> dict:

        state_dict = {
            "name": self.name,
            "_id": self._id,
            "path": self.path,
            "log_path": self.log_path,
            "positions": [lamella.to_dict() for lamella in self.positions],
            "created_at": self._created_at,
            "program": self.program,
            "method": self.method,
        }

        return state_dict

    def save(self) -> None:
        """Save the sample data to yaml file"""

        with open(os.path.join(self.path, "experiment.yaml"), "w") as f:
            yaml.safe_dump(self.to_dict(), f, indent=4)

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
                "lamella.x": lamella.state.microscope_state.stage_position.x,
                "lamella.y": lamella.state.microscope_state.stage_position.y,
                "lamella.z": lamella.state.microscope_state.stage_position.z,
                "lamella.r": lamella.state.microscope_state.stage_position.r,
                "lamella.t": lamella.state.microscope_state.stage_position.t,
                "last_timestamp": lamella.state.microscope_state.timestamp, # dont know if this is the correct timestamp to use here
                "current_stage": lamella.state.stage.name,
                "failure": lamella._is_failure,
                "failure_note": lamella.failure_note,
                "failure_timestamp": lamella.failure_timestamp,
            }

            if "autoliftout" in self.method:
                ldict.update({
                    "landing.x": lamella.landing_state.stage_position.x,
                    "landing.y": lamella.landing_state.stage_position.y,
                    "landing.z": lamella.landing_state.stage_position.z,
                    "landing.r": lamella.landing_state.stage_position.r,
                    "landing.t": lamella.landing_state.stage_position.t,
                    "landing.coordinate_system": lamella.landing_state.stage_position.coordinate_system,
                    "landing_selected": lamella.landing_selected,
                    "history: ": len(lamella.history),}
                )

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

    def history_dataframe(self) -> pd.DataFrame:
        """Create a dataframe with the history of all lamellas."""
        history = []
        lam: Lamella
        hist: LamellaState
        for lam in self.positions:

            petname = lam._petname

            for hist in lam.history:
                start, end = hist.start_timestamp, hist.end_timestamp
                stage_name = hist.stage.name

                hist_d = {
                    "petname": petname,
                    "stage": stage_name,
                    "start": start,
                    "end": end,
                }
                history.append(deepcopy(hist_d))

        df_stage_history = pd.DataFrame.from_dict(history)
        df_stage_history["duration"] = df_stage_history["end"] - df_stage_history["start"]

        return df_stage_history

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
        experiment.method = ddict.get("method", "autoLamella-default") 

        # load lamella from dict
        for lamella_dict in ddict["positions"]:
            lamella = Lamella.from_dict(data=lamella_dict)
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

    def at_stage(self, stage: AutoLamellaStage) -> List[Lamella]:
        """Return a list of lamellas at a specific stage"""

        return [lamella for lamella in self.positions if lamella.state.stage == stage]
        
    def at_failure(self) -> List[Lamella]:
        """Return a list of lamellas that have failed"""

        return [lamella for lamella in self.positions if lamella._is_failure]