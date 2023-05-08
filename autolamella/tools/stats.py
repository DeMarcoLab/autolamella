import os
import sys
# Get the path of the parent directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to the Python module search path
sys.path.append(parent_dir)
from structures import Lamella, Experiment, LamellaState 
from copy import deepcopy
import pandas as pd
import tkinter
from tkinter import filedialog
import yaml

def main():
    tkinter.Tk().withdraw()
    file_path = filedialog.askopenfilename(title="Select experiment directory")
    experiment = Experiment.load(file_path) 
    df = create_history_dataframe(experiment)
    filename = os.path.join("autolamella", "tools", 'data.csv')
    df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

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

main()
