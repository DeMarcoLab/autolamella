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
    
    directory_name = os.path.basename(path)
    full_path = os.path.join(path, directory_name)
    experiment = Experiment.load(full_path) 

    return experiment
    

def create_history_dataframe(sample: Experiment) -> pd.DataFrame:
    history = []
    lam: Lamella
    hist: LamellaState
    for lam in sample.positions:

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
    beam_shift_info = []
    current_lamella = None 
    current_stage = "Setup"
    current_step = None

    end_timestamp = None
    step_n = 0 

    old_feature = None
    old_correct = None
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

                if "log_status_message" in func:
                    current_lamella = msg.split("|")[1].strip()
                    current_stage = msg.split("|")[2].strip().split(".")[-1].strip()
                    current_step = msg.split("|")[3].strip()

                    # datetime string to timestamp int
                    ts = line.split("—")[0].split(",")[0].strip()
                    tsd = datetime.datetime.timestamp(datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))

                    step_d = {"lamella": current_lamella, "stage": current_stage, "step": current_step, "timestamp": tsd, "step_n": step_n}
                    step_n += 1

                if "beam_shift" in func:
                    beam_type, shift = msg.split("|")[-2:]
                    beam_type = beam_type.strip()
                    if beam_type in ["Electron", "Ion", "Photon"]:
                        gamma_d = {
                            "beam_type": beam_type,
                            "shift": Point(shift),
                            "lamella": current_lamella,
                            "stage": current_stage,
                            "step": current_step,
                        }
                        beam_shift_info.append(deepcopy(gamma_d))
            except Exception as e:
                pass
                # print(f"EXCEPTION: {msg} {e}")

            # gamma
            # clicks
            # crosscorrelation
            # ml
            # history
            # sample

    # sample
    experiment = load_experiment(path)
    df_sample = experiment.__to_dataframe__()
    df_history = create_history_dataframe(experiment)

    # convert to datetime
    date = experiment.name.split("-")[-5:]
    date = datetime.datetime.strptime("-".join(date), "%Y-%m-%d.%I-%M-%S%p")

    # add date and name to all dataframes
    df_sample["date"] = date
    df_sample["name"] = experiment.name
    df_history["date"] = date
    df_history["name"] = experiment.name
    beam_shift_info = pd.DataFrame.from_dict(beam_shift_info)
    beam_shift_info["date"] = date
    beam_shift_info["name"] = experiment.name

    filename = os.path.join("autolamella", "tools", 'duration.csv')
    df_history.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join("autolamella", "tools", 'beam_shift.csv')
    beam_shift_info.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    filename = os.path.join("autolamella", "tools", 'sample.csv')
    df_sample.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)


def main():
    tkinter.Tk().withdraw()
    file_path = filedialog.askdirectory(title="Select experiment directory")
    calculate_statistics_dataframe(file_path)

if __name__ == "__main__":
    main()
