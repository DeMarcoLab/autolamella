import os
import json
import datetime

import pandas as pd

from copy import deepcopy
from pathlib import Path
from autolamella.structures import Lamella, Experiment, LamellaState 
  

def create_history_dataframe(experiment: Experiment) -> pd.DataFrame:
    history = []
    lam: Lamella
    hist: LamellaState
    for lam in experiment.positions:

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

def parse_msg(msg: str):
    """parse message json"""
    # turn this into a loop
    # keywords = []

    return json.loads(msg.replace("'", '"').replace("None", '"None"').replace("True", '"True"').replace("False", '"False"'))

def get_timestamp(line: str) -> float:
    """get timestamp from line"""
    ts = line.split("—")[0].split(",")[0].strip()
    tsd = datetime.datetime.timestamp(datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
    return tsd

def get_function(line: str) -> str:
    """get the function name from the line"""
    return line.split("—")[-2].strip()

def get_message(line) -> str:
    """get the message from the line"""
    msg = line.split("—")[
        -1
    ].strip()  # should just be the message # TODO: need to check the delimeter character...
    return msg 

def parse_line(line: str) -> tuple[str, str, str]:
    """parse a line from the log file into a tuple of timestamp, function, and message"""

    tsd = get_timestamp(line)
    func = get_function(line)
    msg = get_message(line)

    return tsd, func, msg


def calculate_statistics_dataframe(path: Path, program="autolamella", encoding: str = "cp1252"):

    fname = os.path.join(path, "logfile.log")
    df_beam_shift = []
    current_lamella = "NULL" 
    current_stage = "SystemSetup"
    current_step = "SystemSetup"
    step_n = 0 
    steps_data = []
    
    state_data = []
    stage_data = []
    det_data = []
    click_data = []

    print("-" * 80)
    print(f"Parsing {fname}")
    # encoding = "cp1252" if "nt" in os.name else "cp1252" # TODO: this depends on the OS it was logged on, usually windows, need to make this more robust.
    with open(fname, encoding=encoding) as f:
        # Note: need to check the encoding as this is required for em dash (long dash) # TODO: change this delimiter so this isnt required.
        lines = f.read().splitlines()
        for i, line in enumerate(lines):

            if line == "":
                continue
            try:
                
                # get timestamp, function, and message from log line
                tsd, func, msg = parse_line(line)
                # msgd = parse_msg(msg) # TODO: enable, and remove indiviudal calls

                # TELEMETRY -> depcrecated in favour of manufacturer telemetry
                if "get_microscope_state" in func:
                    msgd = parse_msg(msg)

                    state_data.append(deepcopy(msgd["state"]))
                    
                if "get_stage_position" in func:
                    msgd = parse_msg(msg)
                    staged = msgd["stage"]
                    staged["timestamp"] = tsd
                    staged["lamella"] = current_lamella
                    staged["stage"] = current_stage
                    staged["step"] = current_step
                
                    stage_data.append(deepcopy(staged))

                if "log_status_message" in func:
                    if "STATUS" in msg:
                        continue        # skip old status messages 
                    
                    # global data
                    tsd = get_timestamp(line)
                    msgd = parse_msg(msg)
                    current_lamella = msgd["petname"]
                    current_stage = msgd["stage"]
                    current_step = msgd["step"]

                    # step data                    
                    step_d = deepcopy(msgd)
                    step_d["lamella"] = current_lamella
                    step_d["timestamp"] = tsd
                    step_d["step_n"] = step_n
                    step_n += 1
                    steps_data.append(deepcopy(step_d))

                
                if "beam_shift" in func:
                    msgd = parse_msg(msg)
                    msgd["timestamp"] = tsd
                    msgd["lamella"] = current_lamella
                    msgd["stage"] = current_stage
                    msgd["step"] = current_step
                    df_beam_shift.append(deepcopy(msgd))


                if "confirm_button" in func: # DETECTION INTERACTION
                    # log detection data
                    msgd = parse_msg(msg)
                    detd = deepcopy(msgd)

                    detd["px_x"] = msgd["px"]["x"]
                    detd["px_y"] = msgd["px"]["y"]
                    detd["dpx_x"] = msgd["dpx"]["x"]
                    detd["dpx_y"] = msgd["dpx"]["y"]
                    detd["dm_x"] = msgd["dm"]["x"]
                    detd["dm_y"] = msgd["dm"]["y"]
                    
                    del detd["dpx"]
                    del detd["dm"]
                    del detd["px"]

                    detd["timestamp"] = tsd
                    detd["lamella"] = current_lamella
                    detd["stage"] = current_stage
                    detd["step"] = current_step
                    det_data.append(deepcopy(detd))

                    # log detection interaction
                    if detd["is_correct"] == "False":
                        click_d = {
                            "lamella": detd["lamella"],
                            "stage": detd["stage"],
                            "step": detd["step"],
                            "type": "DET",
                            "subtype": detd["feature"],
                            "dm_x": detd["dm_x"],
                            "dm_y": detd["dm_y"],
                            "beam_type": detd["beam_type"],
                            "timestamp": detd["timestamp"],
                        }
                        click_data.append(deepcopy(click_d))    

                if "_single_click" in func: # MILLING INTERACTION
                    # log milling interaction
                    msgd = parse_msg(msg)
                    
                    clickd = {}
                    clickd["timestamp"] = tsd
                    clickd["lamella"] = current_lamella
                    clickd["stage"] = current_stage
                    clickd["step"] = current_step
                    
                    clickd["dm_x"] = msgd["dm"]["x"]
                    clickd["dm_y"] = msgd["dm"]["y"]
                    clickd["type"] = "MILL"
                    clickd["subtype"] = msgd["pattern"]
                    clickd["beam_type"] = msgd["beam_type"]

                    click_data.append(deepcopy(clickd))

                if "_double_click" in func: # MOVEMENT INTERACTION
                    
                    # log movement interaction
                    msgd = parse_msg(msg)
                    clickd = {}
                    clickd["timestamp"] = tsd
                    clickd["lamella"] = current_lamella
                    clickd["stage"] = current_stage
                    clickd["step"] = current_step

                    clickd["dm_x"] = msgd["dm"]["x"]
                    clickd["dm_y"] = msgd["dm"]["y"]
                    clickd["type"] = "MOVE"
                    clickd["subtype"] = msgd["movement_mode"]
                    clickd["beam_type"] = msgd["beam_type"]

                    click_data.append(deepcopy(clickd))

            except Exception as e:
                # print(e, " | ", line)
                pass
 
    # experiment
    experiment = Experiment.load(os.path.join(path, "experiment.yaml"))
    df_experiment = experiment.__to_dataframe__()
    df_history = create_history_dataframe(experiment)
    df_steps = pd.DataFrame(steps_data)
    df_stage = pd.DataFrame(stage_data)
    df_det = pd.DataFrame(det_data)
    df_beam_shift = pd.DataFrame.from_dict(df_beam_shift)
    df_click = pd.DataFrame(click_data)
    
    df_steps["duration"] = df_steps["timestamp"].diff() # TODO: fix this duration
    df_steps["duration"] = df_steps["duration"].shift(-1)


    # add date and name to all dataframes
    df_experiment["exp_name"] = experiment.name
    df_history["exp_name"] = experiment.name
    df_beam_shift["exp_name"] = experiment.name
    df_steps["exp_name"] = experiment.name
    df_stage["exp_name"] = experiment.name
    df_det["exp_name"] = experiment.name
    df_click["exp_name"] = experiment.name

    # add experiment id to all df
    df_history["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"
    df_beam_shift["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"
    df_steps["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"
    df_stage["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"
    df_det["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"
    df_click["exp_id"] = experiment._id if experiment._id is not None else "NO_ID"

    # write dataframes to csv, overwrite
    filename = os.path.join(path, 'history.csv')
    df_history.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'beam_shift.csv')
    df_beam_shift.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'experiment.csv')
    df_experiment.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'steps.csv')
    df_steps.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'stage.csv')
    df_stage.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'det.csv')
    df_det.to_csv(filename, mode='w', header=True, index=False)
    filename = os.path.join(path, 'click.csv')
    df_click.to_csv(filename, mode='w', header=True, index=False)


    return df_experiment, df_history, df_beam_shift, df_steps, df_stage, df_det, df_click
