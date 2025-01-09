import logging
import os
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List

import pandas as pd
import petname
import yaml
from fibsem.milling import (
    FibsemMillingStage,
    get_milling_stages,
    get_protocol_from_stages,
)
from fibsem.structures import (
    FibsemImage,
    FibsemRectangle,
    MicroscopeState,
    ReferenceImages,
)
from fibsem.utils import configure_logging

from autolamella import config as cfg
from autolamella.protocol.validation import (
    LANDING_KEY,
    LIFTOUT_KEY,
    MILL_POLISHING_KEY,
    MILL_ROUGH_KEY,
    SETUP_LAMELLA_KEY,
    TRENCH_KEY,
    UNDERCUT_KEY,
)


class AutoLamellaStage(Enum):
    Created = auto()
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
# TODO: investigate removing PreSetupLamella, ReadyTrench, ReadyLamella

    def __str__(self) -> str:
        return self.name

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
    path: Path
    state: LamellaState
    number: int
    petname: str
    protocol: dict
    is_failure: bool = False
    failure_note: str = ""
    failure_timestamp: float = None
    alignment_area: FibsemRectangle = FibsemRectangle()
    landing_selected: bool = False
    landing_state: MicroscopeState = MicroscopeState() # TODO: remove
    history: List[LamellaState] = None
    milling_workflows: Dict[str, List[FibsemMillingStage]] = None
    states: Dict[AutoLamellaStage, LamellaState] = None
    _id: str = str(uuid.uuid4())

    def __post_init__(self):
        os.makedirs(self.path, exist_ok=True)
        if self.protocol is None:
            self.protocol = {}
        if self.history is None:
            self.history = []
        if self.milling_workflows is None:
            self.milling_workflows = {}
        if self.states is None:
            self.states = {}
        if self._id is None:
            self._id = str(uuid.uuid4())

    @property
    def finished(self) -> bool:
        return self.state.stage == AutoLamellaStage.Finished

    @property
    def workflow_stages_completed(self) -> List[AutoLamellaStage]:
        return list(self.states.keys())

    @property
    def name(self) -> str:
        return self.petname
    
    @property
    def status(self) -> str:
        return self.state.stage.name
    
    @property
    def workflow(self) -> AutoLamellaStage:
        return self.state.stage
    
    def to_dict(self):
        return {
            "petname": self.petname,
            "state": self.state.to_dict() if self.state is not None else None,
            "path": str(self.path),
            "alignment_area": self.alignment_area.to_dict(),
            "protocol": self.protocol,
            "number": self.number,
            "history": [state.to_dict() for state in self.history] if self.history is not False else [],
            "is_failure": self.is_failure,
            "failure_note": self.failure_note,
            "failure_timestamp": self.failure_timestamp,
            "landing_state": self.landing_state.to_dict(),
            "landing_selected": self.landing_selected,
            "id": str(self._id),
            "states": {k.name: v.to_dict() for k, v in self.states.items()},
        }

    @property
    def info(self):
        return f"Lamella {self.petname} [{self.state.stage.name}]"

    @classmethod
    def from_dict(cls, data):
        state = LamellaState.from_dict(data["state"])

        # backwards compatibility
        alignment_area_ddict = data.get("fiducial_area", data.get("alingment_area", None))
        if alignment_area_ddict is not None:
            alignment_area = FibsemRectangle.from_dict(alignment_area_ddict)
        else:
            alignment_area = FibsemRectangle() # use default
        
        # load states:
        states = data.get("states", {})
        if states:
            states = {AutoLamellaStage[k]: LamellaState.from_dict(v) for k, v in states.items()}

        return cls(
            petname=data["petname"],
            state=state,
            path=data["path"],
            alignment_area=alignment_area,
            protocol=data.get("protocol", {}),
            number=data.get("number", data.get("number", 0)),
            history=[LamellaState().from_dict(state) for state in data["history"]],
            is_failure=data.get("is_failure", data.get("is_failure", False)),
            failure_note=data.get("failure_note", ""),
            failure_timestamp=data.get("failure_timestamp", None),
            landing_state = MicroscopeState.from_dict(data.get("landing_state", MicroscopeState().to_dict())), # tmp solution
            landing_selected = bool(data.get("landing_selected", False)),
            _id=data.get("id", None),
            states=states,
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

def create_new_lamella(experiment_path: str, number: int, state: LamellaState, protocol: Dict) -> Lamella:
    """Wrapper function to create a new lamella and configure paths."""

    # create the petname and path
    name = f"{number:02d}-{petname.generate(2)}"
    path = os.path.join(experiment_path, name)
    
    # create the lamella
    lamella = Lamella(
        petname=name,
        path=path,
        number=number,
        state=state,
        protocol=deepcopy(protocol), # TODO: replace with milling_workflows
    )

    # create the lamella directory
    os.makedirs(lamella.path, exist_ok=True)

    logging.info(f"Created new lamella {lamella.name} at {lamella.path}")

    return lamella

def create_new_experiment(path: Path, name: str, program: str = "AutoLamella", method: str = "autolamella-on-grid") -> 'Experiment':
    """Wrapper function to create an experiment and configure logging."""

    # create the experiment
    experiment = Experiment(path=path, name=name, program=program, method=method)

    # configure experiment logging
    os.makedirs(experiment.path, exist_ok=True)
    configure_logging(path=experiment.path, log_filename="logfile")

    # save the experiment
    experiment.save()

    logging.info(f"Created new experiment {experiment.name} at {experiment.path}")

    return experiment

class Experiment: 
    def __init__(self, path: Path, 
                 name: str = cfg.EXPERIMENT_NAME, 
                 program: str = "AutoLamella",
                 method: str = "autolamella-on-grid") -> None:
        """Create a new experiment."""
        self.name: str = name
        self._id = str(uuid.uuid4())
        self.path: Path = os.path.join(path, name)
        self.created_at: float = datetime.timestamp(datetime.now())

        self.positions: List[Lamella] = []

        self.program: str = program
        self.method: str = method

    def to_dict(self) -> dict:

        state_dict = {
            "name": self.name,
            "_id": self._id,
            "path": self.path,
            "positions": [lamella.to_dict() for lamella in self.positions],
            "created_at": self.created_at,
            "program": self.program,
            "method": self.method,
        }

        return state_dict
    
    @classmethod
    def from_dict(cls, ddict: dict) -> 'Experiment':

        path = os.path.dirname(ddict["path"])
        name = ddict["name"]
        experiment = Experiment(path=path, name=name)
        experiment.created_at = ddict.get("created_at", None)
        experiment._id = ddict.get("_id", "NULL")
        experiment.program = ddict.get("program", cfg.EXPERIMENT_NAME)
        experiment.method = ddict.get("method", "autoLamella-on-grid")

        # load lamella from dict
        for lamella_dict in ddict["positions"]:
            lamella = Lamella.from_dict(data=lamella_dict)
            experiment.positions.append(lamella)

        return experiment

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
                "experiment_created_at": self.created_at,
                "experiment_id": self._id,
                "program": self.program,
                "method": self.method, 
                "number": lamella.number,
                "petname": lamella.petname,  # what?
                "path": lamella.path,
                "lamella.x": lamella.state.microscope_state.stage_position.x,
                "lamella.y": lamella.state.microscope_state.stage_position.y,
                "lamella.z": lamella.state.microscope_state.stage_position.z,
                "lamella.r": lamella.state.microscope_state.stage_position.r,
                "lamella.t": lamella.state.microscope_state.stage_position.t,
                "last_timestamp": lamella.state.microscope_state.timestamp, # dont know if this is the correct timestamp to use here
                "current_stage": lamella.state.stage.name,
                "failure": lamella.is_failure,
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
            "date": self.created_at,
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

            petname = lam.petname

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
        """Load an experiment from disk."""

        # read and open existing yaml file
        path = Path(fname).with_suffix(".yaml")
        if os.path.exists(path):
            with open(path, "r") as f:
                ddict = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"No file with name {path} found.")

        # create experiment from dict
        experiment = Experiment.from_dict(ddict)
        experiment.path = os.path.dirname(fname) # TODO: make sure the paths are correctly re-assigned when loaded on a different machine

        return experiment
    
    def _create_protocol_dataframe(self) -> pd.DataFrame:
        # NOTE: this is based on the previous protocol structure... need to update
        plist = []
        exp_name = self.name
        for lamella in self.positions:
            if lamella.protocol:
                for k in lamella.protocol:


                    if "stages" not in lamella.protocol[k]:
                        continue # skip non milling stages
      
                    else:
                        for i, ddict in enumerate(lamella.protocol[k]["stages"]):

                            ddict["MillingStage"] = i
                            ddict["WorkflowStage"] = k
                            ddict["Lamella"] = lamella.name
                            ddict["Experiment"] = exp_name
                            # TODO: add point information

                            plist.append(deepcopy(ddict))

        df = pd.DataFrame(plist)

        # re-order columns starting with lamella, WorkflowStage, MillingStage
        cols = list(df.columns)
        cols.remove("Lamella")
        cols.remove("WorkflowStage")
        cols.remove("MillingStage")
        cols.remove("Experiment")
        cols = ["Experiment", "Lamella", "WorkflowStage", "MillingStage"] + cols
        df = df[cols]


        return df

    def _convert_dataframe_to_protocol(self, df: pd.DataFrame) -> None:
        """Convert a dataframe to a protocol."""

        PROTOCOL_KEYS = ["trench", "MillUndercut", "fiducial", "notch", "MillRoughCut", "MillRegularCut", "MillPolishingCut", "microexpansion"]

        df.sort_values(by=["MillingStage"], inplace=True)

        for lamella in self.positions:
            petname = lamella.petname
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

        return [lamella for lamella in self.positions if lamella.is_failure]


########## PROTOCOL V2 ##########

@dataclass
class FibsemProtocol(ABC):
    pass

@dataclass
class MethodConfig:
   name: str
   workflow: List[AutoLamellaStage]

class AutoLamellaMethod(Enum):
   ON_GRID = MethodConfig(
       name="AutoLamella-OnGrid",
       workflow=[
           AutoLamellaStage.SetupLamella,
           AutoLamellaStage.ReadyLamella, 
           AutoLamellaStage.MillRoughCut,
           AutoLamellaStage.MillPolishingCut,
           AutoLamellaStage.Finished,
       ]
   )

   TRENCH = MethodConfig(
       name="AutoLamella-Trench",
       workflow=[
           AutoLamellaStage.SetupTrench,
           AutoLamellaStage.ReadyTrench,
           AutoLamellaStage.MillTrench,
       ]
   )

   WAFFLE = MethodConfig(
       name="AutoLamella-Waffle",
       workflow=[
           AutoLamellaStage.SetupTrench,
           AutoLamellaStage.ReadyTrench,
           AutoLamellaStage.MillTrench,
           AutoLamellaStage.MillUndercut,
           AutoLamellaStage.SetupLamella,
           AutoLamellaStage.ReadyLamella,
           AutoLamellaStage.MillRoughCut,
           AutoLamellaStage.MillPolishingCut,
           AutoLamellaStage.Finished,
       ]
   )

   LIFTOUT = MethodConfig(
       name="AutoLamella-Liftout",
       workflow=[
           AutoLamellaStage.SetupTrench,
           AutoLamellaStage.ReadyTrench,
           AutoLamellaStage.MillTrench,
           AutoLamellaStage.MillUndercut,
           AutoLamellaStage.LiftoutLamella,
           AutoLamellaStage.LandLamella,
           AutoLamellaStage.SetupLamella,
           AutoLamellaStage.ReadyLamella,
           AutoLamellaStage.MillRoughCut,
           AutoLamellaStage.MillPolishingCut,
           AutoLamellaStage.Finished,
       ]
   )

   SERIAL_LIFTOUT = MethodConfig(
       name="AutoLamella-Serial-Liftout",
       workflow=[
           AutoLamellaStage.SetupTrench,
           AutoLamellaStage.ReadyTrench,
           AutoLamellaStage.MillTrench,
           AutoLamellaStage.MillUndercut,
           AutoLamellaStage.LiftoutLamella,
           AutoLamellaStage.LandLamella,
           AutoLamellaStage.SetupLamella,
           AutoLamellaStage.ReadyLamella,
           AutoLamellaStage.MillRoughCut,
           AutoLamellaStage.MillPolishingCut,
           AutoLamellaStage.Finished,
       ]
   )

   @property
   def name(self) -> str:
       return self.value.name

   @property
   def workflow(self) -> List[AutoLamellaStage]:
       return self.value.workflow

DEFAULT_AUTOLAMELLA_METHOD = AutoLamellaMethod.ON_GRID.name

WORKFLOW_STAGE_TO_PROTOCOL_KEY = {
    AutoLamellaStage.MillTrench: TRENCH_KEY,
    AutoLamellaStage.MillUndercut: UNDERCUT_KEY,
    AutoLamellaStage.SetupLamella: SETUP_LAMELLA_KEY,
    AutoLamellaStage.LiftoutLamella: LIFTOUT_KEY,
    AutoLamellaStage.LandLamella: LANDING_KEY,
    AutoLamellaStage.MillRoughCut: MILL_ROUGH_KEY,
    AutoLamellaStage.MillPolishingCut: MILL_POLISHING_KEY,
}

@dataclass
class AutoLamellaProtocolOptions:
    use_fiducial: bool
    use_microexpansion: bool
    use_notch: bool
    take_final_reference_images: bool
    alignment_attempts: int 
    alignment_at_milling_current: bool
    milling_tilt_angle: float
    undercut_tilt_angle: float
    checkpoint: str
    turn_beams_off: bool = False

    def to_dict(self):
        return {
            "use_fiducial": self.use_fiducial,
            "use_notch": self.use_notch,
            "use_microexpansion": self.use_microexpansion,
            "take_final_reference_images": self.take_final_reference_images,
            "alignment_attempts": self.alignment_attempts,
            "alignment_at_milling_current": self.alignment_at_milling_current,
            "milling_tilt_angle": self.milling_tilt_angle,
            "undercut_tilt_angle": self.undercut_tilt_angle,
            "checkpoint": self.checkpoint,
            "turn_beams_off": self.turn_beams_off,
        }

    @classmethod
    def from_dict(cls, ddict: dict) -> 'AutoLamellaProtocolOptions':        
        return cls(
            use_fiducial=ddict.get("use_fiducial", True),
            use_notch=ddict.get("use_notch", False),
            use_microexpansion=ddict.get("use_microexpansion", True),
            take_final_reference_images=ddict["take_final_reference_images"],
            alignment_attempts=ddict.get("alignment_attempts", 3),
            alignment_at_milling_current=ddict.get("alignment_at_milling_current", False),
            milling_tilt_angle=ddict.get("milling_tilt_angle", ddict.get("lamella_tilt_angle", 18)),
            undercut_tilt_angle=ddict.get("undercut_tilt_angle", -5),
            checkpoint=ddict.get("checkpoint", "autolamella-mega-20240107.pt"),
            turn_beams_off=ddict.get("turn_beams_off", False),
        )

def get_autolamella_method(name: str) -> AutoLamellaMethod:
    method_aliases = {
        AutoLamellaMethod.ON_GRID: ["autolamella-on-grid", "on-grid", "AutoLamella-OnGrid"],
        AutoLamellaMethod.WAFFLE: ["autolamella-waffle", "waffle", "AutoLamella-Waffle"],
        AutoLamellaMethod.TRENCH: ["autolamella-trench", "trench", "AutoLamella-Trench"],
        AutoLamellaMethod.LIFTOUT: ["autolamella-liftout", "liftout", "AutoLamella-Liftout"],
        AutoLamellaMethod.SERIAL_LIFTOUT: ["autolamella-serial-liftout", "serial-liftout", "AutoLamella-Serial-Liftout"],
    }
    
    # Create a flattened mapping of all aliases to their methods
    name_mapping = {
        alias.lower(): method 
        for method, aliases in method_aliases.items() 
        for alias in aliases
    }
    
    normalized_name = name.lower()
    if normalized_name not in name_mapping:
        valid_names = sorted(set(alias for aliases in method_aliases.values() for alias in aliases))
        raise ValueError(f"Unknown method: {name}. Valid methods are: {valid_names}")
    
    return name_mapping[normalized_name]

def get_supervision(stage: AutoLamellaStage, protocol: dict) -> bool:
    key = WORKFLOW_STAGE_TO_PROTOCOL_KEY.get(stage, None)
    return protocol.get("supervise", {}).get(key, True)

@dataclass
class AutoLamellaProtocol(FibsemProtocol):
    name: str
    method: AutoLamellaMethod
    supervision: Dict[AutoLamellaStage, bool]
    configuration: dict                             # microscope configuration
    options: AutoLamellaProtocolOptions             # options for the protocol
    milling: Dict[str, List[FibsemMillingStage]]    # milling workflows

    def to_dict(self):
        return {
            "name": self.name,
            "method": self.method.name,
            "supervision": {k.name: v for k, v in self.supervision.items()},
            "configuration": self.configuration,
            "options": self.options.to_dict(),
            "milling": {k: get_protocol_from_stages(v) for k, v in self.milling.items()},
        }

    @classmethod
    def from_dict(cls, ddict: dict) -> 'AutoLamellaProtocol':

        method = get_autolamella_method(ddict.get("method", DEFAULT_AUTOLAMELLA_METHOD))

        # load the supervision tasks
        supervision_tasks = {k: get_supervision(k, ddict["options"]) for k in WORKFLOW_STAGE_TO_PROTOCOL_KEY.keys()}
        # filter out tasks that arent part of the method
        supervision_tasks = {k: v for k, v in supervision_tasks.items() if k in method.workflow}
        
        return cls(
            name=ddict["name"],
            method=method,
            supervision=supervision_tasks,
            configuration=ddict.get("configuration", {}),
            options=AutoLamellaProtocolOptions.from_dict(ddict["options"]),
            milling={k: get_milling_stages(k, ddict["milling"]) for k in ddict["milling"]}
        )
    # TODO: tests before integration