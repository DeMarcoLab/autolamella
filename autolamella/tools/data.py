import os
import sys
from autolamella.structures import Lamella, Experiment, LamellaState 
from fibsem.structures import Point
from copy import deepcopy
import pandas as pd
import yaml
import datetime
from pathlib import Path

def load_experiment(path):
    
    directory_name = os.path.basename(os.path.normpath(path))
    full_path = os.path.join(path, "experiment.yaml")
    experiment = Experiment.load(full_path) 

    return experiment
    

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

def calculate_statistics_dataframe(path: Path):

    fname = os.path.join(path, "logfile.log")
    df_beam_shift = []
    current_lamella = "NULL" 
    current_stage = "SystemSetup"
    current_step = "SystemSetup"
    step_n = 0 
    steps_data = []
    
    state_data = []
    stage_data = []
    move_data = []
    det_data = []
    click_data = []


    print("-" * 80)
    encoding = "cp1252" if "nt" in os.name else None
    with open(fname, encoding=encoding) as f:
        # Note: need to check the encoding as this is required for em dash (long dash) # TODO: change this delimiter so this isnt required.
        lines = f.read().splitlines()
        for i, line in enumerate(lines):

            if line == "":
                continue
            try:
                msg = line.split("—")[
                    -1
                ].strip()  # should just be the message # TODO: need to check the delimeter character...
                func = line.split("—")[-2].strip()
                ts = line.split("—")[0].split(",")[0].strip()
                tsd = datetime.datetime.timestamp(datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))

                # MOVEMENT
                if "get_" in func:
                    import json
                    if "get_current_microscope_state" in func:
                        state_dict = str(msg.split("|")[1].strip()).replace("'", '"').replace("None", '"None"')
                        state_dict = json.loads(state_dict)

                        state_data.append(deepcopy(state_dict))

                        # print("STATE: ", state_dict)
                        
                    if "get_stage_position" in func:
                        stage_dict = str(msg.split("|")[1].strip()).replace("'", '"').replace("None", '"None"')
                        stage_dict = json.loads(stage_dict)
                        stage_dict["timestamp"] = tsd
                        stage_dict["lamella"] = current_lamella
                        stage_dict["stage"] = current_stage
                        stage_dict["step"] = current_step
                    
                        stage_data.append(deepcopy(stage_dict))


                if "STATUS" in msg:
                    if "Widget" in msg:
                        continue
                    current_lamella = msg.split("|")[1].strip()
                    current_stage = msg.split("|")[2].strip().split(".")[-1].strip()
                    current_step = msg.split("|")[3].strip()

                    # datetime string to timestamp int
                    ts = line.split("—")[0].split(",")[0].strip()
                    tsd = datetime.datetime.timestamp(datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
                    step_d = {"lamella": current_lamella, "stage": current_stage, "step": current_step, "timestamp": tsd, "step_n": step_n}
                    step_n += 1
                    steps_data.append(deepcopy(step_d))
                
                if "beam_shift" in func:
                    beam_type, shiftx, shifty = msg.split("|")[-3:]
                    beam_type = beam_type.strip()
                    if beam_type.upper() in ["ELECTRON", "ION", "PHOTON"]:
                        gamma_d = {
                            "beam_type": beam_type,
                            "shift.x": float(shiftx),
                            "shift.y": float(shifty),
                            "lamella": current_lamella,
                            "stage": current_stage,
                            "step": current_step,
                        }
                        df_beam_shift.append(deepcopy(gamma_d))

                if "confirm_button" in func: # DETECTION

                    feat = msg.split("|")[0].strip()
                    dpx = msg.split("|")[1].split("=")
                    dpx_x = int(dpx[1].split(",")[0].strip())
                    dpx_y = int(dpx[-1].split(")")[0].strip())
                    
                    dm =  msg.split("|")[2].split("=") 
                    dm_x = float(dm[1].split(",")[0].strip())
                    dm_y = float(dm[-1].split(")")[0].strip())

                    _is_correct = msg.split("|")[3].strip()
                    beam_type = msg.split("|")[4].split(".")[-1].strip().upper()
                    fname = msg.split("|")[5].strip()

                    detd = {
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                        "feature": feat,
                        "dpx_x": dpx_x,
                        "dpx_y": dpx_y,
                        "dm_x": dm_x,
                        "dm_y": dm_y,
                        "is_correct": _is_correct,
                        "timestamp": tsd,
                        "beam_type": beam_type,
                        "fname": fname,
                    }
                    det_data.append(deepcopy(detd))
                    
                    if _is_correct == "False":
                        click_d = {
                            "lamella": current_lamella,
                            "stage": current_stage,
                            "step": current_step,
                            "type": "DET",
                            "subtype": feat,
                            "dm_x": dm_x,
                            "dm_y": dm_y,
                            "beam_type": beam_type,
                        }
                        click_data.append(deepcopy(click_d))

                if "_single_click" in func: # MILLING

                    ctype = msg.split("|")[0].strip()
                    subtype = msg.split("|")[1].strip()
                    dm = msg.split("|")[2].split("=")
                    dm_x = float(dm[1].split(",")[0].strip())
                    dm_y = float(dm[-1].split(")")[0].strip())

                    click_d = {
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                        "type": ctype,
                        "subtype": subtype,
                        "dm_x": dm_x,
                        "dm_y": dm_y,
                        "beam_type": "ION"
                    }
                    click_data.append(deepcopy(click_d))

                if "_double_click" in func: # MOVEMENT

                    ctype = "MOVE"
                    subtype = msg.split("|")[0].split(":")[-1].strip().upper()
                    dm = msg.split("|")[2].split(",")
                    dm_x = float(dm[1].split(" ")[1].strip())
                    dm_y = float(dm[-1].strip())
                    beam_type = msg.split("|")[-1].split(".")[-1].strip().upper()
                    click_d = {
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                        "type": ctype,
                        "subtype": subtype,
                        "dm_x": dm_x,
                        "dm_y": dm_y,
                        "beam_type": beam_type,
                    }
                    
                    click_data.append(deepcopy(click_d))


            except Exception as e:
                # print(e, " | ", line)
                pass
 
    # sample
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

    filename = os.path.join(path, 'duration.csv')
    df_history.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join(path, 'beam_shift.csv')
    df_beam_shift.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join(path, 'experiment.csv')
    df_experiment.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

    return df_experiment, df_history, df_beam_shift, df_steps, df_stage, df_det, df_click

