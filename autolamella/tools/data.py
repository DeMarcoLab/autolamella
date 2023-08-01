import os
import sys
# Get the path of the parent directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to the Python module search path
sys.path.append(parent_dir)
from structures import Lamella, Experiment, LamellaState 
from fibsem.structures import Point
from copy import deepcopy
import pandas as pd
import tkinter
from tkinter import filedialog
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
    current_lamella = None 
    current_stage = "Setup"
    current_step = None
    step_n = 0 
    steps_data = []

    stage_position = []

    print("-" * 80)
    with open(fname, encoding="cp1252") as f:
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
                if "move_stage_absolute" in func or "move_stage_relative" in func:

                    TYPE = "absolute" if "move_stage_absolute" in func else "relative"

                    pos_msg = msg.split("(")[1].split(")")[0].split(",")
                    name = pos_msg[0].split("=")[-1].strip()
                    x = pos_msg[1].split("=")[-1].strip()
                    y = pos_msg[2].split("=")[-1].strip()
                    z = pos_msg[3].split("=")[-1].strip()
                    r = pos_msg[4].split("=")[-1].strip()
                    t = pos_msg[5].split("=")[-1].strip()
                    vals = [x, y, z, r, t]
                    vals = [float(v) if v != 'None' else 0 for v in vals ]


                    mdict = {"lamella": current_lamella, "stage": current_stage, "step": current_step, 
                        "timestamp": tsd, "step_n": step_n, 
                        "type": TYPE, "name": name, "x": vals[0], "y": vals[1], 
                        "z": vals[2], "r": vals[3], "t": vals[4]}
                    stage_position.append(deepcopy(mdict))

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
            except Exception as e:
                pass
                #print(e)
 
    # sample
    experiment = load_experiment(path)
    df_experiment = experiment.__to_dataframe__()
    df_history = create_history_dataframe(experiment)
    df_steps = pd.DataFrame(steps_data)
    df_stage = pd.DataFrame(stage_position)

    
    df_steps["duration"] = df_steps["timestamp"].diff() # TODO: fix this duration
    df_steps["duration"] = df_steps["duration"].shift(-1)


    # add date and name to all dataframes
    df_experiment["name"] = experiment.name
    df_history["name"] = experiment.name
    df_beam_shift = pd.DataFrame.from_dict(df_beam_shift)
    df_beam_shift["name"] = experiment.name

    filename = os.path.join(path, 'duration.csv')
    df_history.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join(path, 'beam_shift.csv')
    df_beam_shift.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join(path, 'experiment.csv')
    df_experiment.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

    return df_experiment, df_history, df_beam_shift, df_steps, df_stage

def main():
    tkinter.Tk().withdraw()
    file_path = filedialog.askdirectory(title="Select experiment directory")
    calculate_statistics_dataframe(file_path)

if __name__ == "__main__":
    main()
