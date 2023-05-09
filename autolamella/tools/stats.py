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

def calculate_statistics_dataframe(path: Path) -> AutoLiftoutStatistics:

    fname = os.path.join(path, "logfile.log")
    gamma_info = []
    click_info = []
    move_info = []
    ml_info = []

    step_duration_info = []

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
                    step_duration_info.append(deepcopy(step_d))
                    step_n += 1

                if "gamma" in func:
                    beam_type, diff, gamma = msg.split("|")[-3:]
                    beam_type = beam_type.strip()
                    if beam_type in ["Electron", "Ion", "Photon"]:
                        gamma_d = {
                            "beam_type": beam_type,
                            "diff": float(diff),
                            "gamma": float(gamma),
                            "lamella": current_lamella,
                            "stage": current_stage,
                            "step": current_step,
                        }
                        gamma_info.append(deepcopy(gamma_d))
                                                
                if "double_click" in func:
                    
                    if "Milling" in msg:
                        # milling click
                        split_msg = msg.split(",")
                        click_source = split_msg[0].strip()
                        beam_type = split_msg[1].split(".")[-1].strip()
                        click_type = split_msg[2].strip()
                        pos_x = split_msg[-2].split("(")[-1].strip()
                        pos_y = split_msg[-1].split(")")[0].strip()
                        click_source = "Milling"                      
                    else:
                        # movement
                        split_msg = msg.split("|")
                        click_type = split_msg[0].split(":")[-1].strip()
                        beam_type = split_msg[-1].split(".")[-1]
                        pos = split_msg[-2].strip().split(" ")
                        pos_x = pos[1].replace(",", "")
                        pos_y = pos[2]
                        click_source = "Movement"
                    
                    click_d = {
                        "source": click_source,
                        "beam_type": beam_type,
                        "type": click_type,
                        "x": float(pos_x),
                        "y": float(pos_y),
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                    }

                    click_info.append(deepcopy(click_d))

                if "on_click" in func:
                    split_msg = msg.split("|")
                    if "DectectedFeature" == split_msg[0].split(" ")[0].strip():
                        # click_type = split_msg[0].split(":")[-1].strip()
                        # print(split_msg)
                        click_source = "DetectedFeature"
                        if "BeamType" in split_msg[-1]:
                            click_type = split_msg[-1].split(".")[-1]
                        else:
                            click_type = split_msg[0].split(" ")[-2].strip()
                            # print(beam_type)

                        beam_type = "ELECTRON" # TODO: need to fix this
                        # print(split_msg)
                        pos = split_msg[-1].strip().split(", ")
                        pos_x = pos[0]
                        pos_y = pos[1]
                        click_d = {
                            "source": click_source,
                            "beam_type": beam_type,
                            "type": click_type,
                            "x": float(pos_x),
                            "y": float(pos_y),
                            "lamella": current_lamella,
                            "stage": current_stage,
                            "step": current_step,
                        }
                        click_info.append(deepcopy(click_d))


                # ml
                if "Feature" == msg.split("|")[0].strip():
                    # print(msg)
                    feature_type = msg.split("|")[1].split(".")[-1].strip()
                    correct = msg.split("|")[2].strip()
                    # if feature_type == old_feature and correct == old_correct and correct == False:
                    #     print("duplicate feature: ", feature_type, msg)
                    #     continue
                    ml_d = {
                        "feature": feature_type,
                        "correct": correct,
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                    }
                    ml_info.append(deepcopy(ml_d))
                    # old_feature = feature_type
                    # old_correct = correct

                if "move_stage" in func:
                    if "move_stage_relative" in func:
                        beam_type = "ION"
                        mode = "Stable"
                        split_msg = [char.split("=") for char in msg.split(" ")[-3:]]
                        x, y, z = [m[1].replace(",", "") for m in split_msg]
                        z = z.replace(")", "")

                    if "move_stage_eucentric" in func:
                        # TODO: add beam here
                        beam_type = "ION"
                        mode = "Eucentric"
                        z = msg.split(" ")[-1].split("=")[-1].replace(")", "")
                        x, y = 0, 0

                    move_d = {
                        "beam_type": beam_type,
                        "mode": mode,
                        "x": float(x),
                        "y": float(y),
                        "z": float(z),
                        "lamella": current_lamella,
                        "stage": current_stage,
                        "step": current_step,
                    }
                    move_info.append(deepcopy(move_d))
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
    sample = load_experiment(path)
    df_sample = sample.__to_dataframe__()
    df_history = create_history_dataframe(sample)
    df_gamma=pd.DataFrame.from_dict(gamma_info)
    df_click=pd.DataFrame.from_dict(click_info)
    df_move=pd.DataFrame.from_dict(move_info)
    df_ml=pd.DataFrame.from_dict(ml_info)

    df_step_duration = pd.DataFrame.from_dict(step_duration_info)    

    # convert to datetime
    date = sample.name.split("-")[-5:]
    date = datetime.datetime.strptime("-".join(date), "%Y-%m-%d.%I-%M-%S%p")

    # add date and name to all dataframes
    df_sample["date"] = date
    df_sample["name"] = sample.name
    df_history["date"] = date
    df_history["name"] = sample.name
    df_gamma["date"] = date
    df_gamma["name"] = sample.name
    df_click["date"] = date
    df_click["name"] = sample.name
    df_move["date"] = date
    df_move["name"] = sample.name
    df_ml["date"] = date
    df_ml["name"] = sample.name
    df_step_duration["date"] = date
    df_step_duration["name"] = sample.name

    df_step_duration["duration"] = df_step_duration["timestamp"].diff() # TODO: fix this duration
    df_step_duration["duration"] = df_step_duration["duration"].shift(-1)


    return AutoLiftoutStatistics(
        gamma=df_gamma,
        click=df_click,
        move=df_move,
        ml=df_ml,
        sample=df_sample,
        history=df_history,
        name=sample.name,
        date= date,
        step_duration=df_step_duration

    )



if __name__ == "__main__":
    main()
