import glob
import os
from copy import deepcopy

import pandas as pd
import plotly.express as px
import streamlit as st
import autolamella
from autolamella.tools.data import calculate_statistics_dataframe
from fibsem.structures import FibsemImage
from autolamella.structures import Experiment
from fibsem.imaging import _tile

import autolamella.config as cfg

import plotly.io as pio


pio.templates.default = "plotly_white"

st.set_page_config(page_title="OpenFIBSEM Analytics", page_icon=':snowflake:', layout="wide")
page_title = st.title("AutoLamella Analytics")

#################### EXPERIMENT SECTION ####################

# select experiment

path_cols = st.sidebar.columns(2)
LOG_PATH = st.sidebar.text_input("Log Path", cfg.LOG_PATH)
paths = glob.glob(os.path.join(LOG_PATH, "*/"))
EXPERIMENT_NAME = st.sidebar.selectbox(label="Experiment ", options=[os.path.basename(os.path.dirname(path)) for path in paths])
EXPERIMENT_PATH = os.path.join(LOG_PATH, EXPERIMENT_NAME)

program = st.sidebar.selectbox(label="Program", options=["autolamella", "autoliftout"])
encoding = st.sidebar.text_input("Encoding", "cp1252")

encoding = None if encoding == "None" else encoding

page_title.title(f"{EXPERIMENT_NAME} Analytics ({program.capitalize()})")

(df_experiment, df_history, 
df_beam_shift, 
    df_steps, df_stage, 
    df_det, df_click) = calculate_statistics_dataframe(EXPERIMENT_PATH, program=program, encoding=encoding)

# experiment metrics
cols = st.columns(4)

# experiment metrics
n_lamella = len(df_history["petname"].unique())
n_trenches = len(df_history[df_history["stage"] == "MillTrench"]["petname"].unique())

if program == "autolamella":
    n_undercut = len(df_history[df_history["stage"] == "MillUndercut"]["petname"].unique())
    cols[2].metric(label="Undercut", value=n_undercut)

if program == "autoliftout":
    n_liftout = len(df_history[df_history["stage"] == "Landing"]["petname"].unique())
    cols[2].metric(label="Landing", value=n_liftout)

n_polish = len(df_history[df_history["stage"] == "MillPolishingCut"]["petname"].unique())

cols[0].metric(label="Lamella", value=n_lamella)
cols[1].metric(label="Trenches", value=n_trenches)
cols[3].metric(label="Polish", value=n_polish)


# average duration
# group by petname
df_hist2 = deepcopy(df_history)

try:
    # drop if stage == "ReadyTrench"
    df_hist2 = df_hist2[df_hist2["stage"] != "ReadyTrench"]
    df_hist2 = df_hist2[df_hist2["stage"] != "SetupTrench"]
    df_hist2 = df_hist2[df_hist2["stage"] != "Setup"]

    df_group = df_hist2.groupby("petname").sum().reset_index()
    df_group["avg_duration"] = df_group["duration"].mean() / 60
    df_group["avg_duration"] = df_group["avg_duration"].round(2).astype(str) + " min"
    avg_duration = df_group["avg_duration"].iloc[0]



    # total duration
    total_duration = df_hist2["duration"].sum() / 60 / 60
    total_duration = str(total_duration.round(2)) + " hrs"
    longest_stage = df_hist2.groupby("stage").mean().sort_values("duration", ascending=False).iloc[0]

    # duration metrics
    cols[0].metric(label="Avg Duration (Per Lamella)", value=avg_duration)
    cols[1].metric(label="Total Duration (All Lamella)", value=total_duration)
    cols[2].metric(label="Longest Stage (Average)", value=f"{longest_stage.name}: {round(longest_stage.duration/60, 1)} min")
    # automation metrics
except:
    pass

# total clicks, avg click size
total_clicks = len(df_click)

avg_dx = "N/A"
avg_dy = "N/A"
if len(df_click) > 0:
    df_click["mag_dm_x"] = abs(df_click["dm_x"])
    df_click["mag_dm_y"] = abs(df_click["dm_y"])
    avg_dx = str(round(df_click["mag_dm_x"].mean()*1e6, 2)) + " um"
    avg_dy = str(round(df_click["mag_dm_y"].mean()*1e6, 2)) + " um"



cols[0].metric(label="Total Clicks", value=total_clicks)
cols[1].metric(label="Avg Click Size (dx)", value=avg_dx)
cols[2].metric(label="Avg Click Size (dy)", value=avg_dy)

# ml accuracy
# total correct, total incorrect, accuracy

if len(df_det) > 0:
    total_correct = len(df_det[df_det["is_correct"] == 'True'])
    total_incorrect = len(df_det[df_det["is_correct"] == 'False'])
    accuracy = total_correct / (total_correct + total_incorrect)
    
    BASE_ACCURACY = 0.0
    d_accuracy = accuracy - BASE_ACCURACY

    accuracy_str = str(round(accuracy*100, 2)) + "%"
    d_accuracy_str = str(round(d_accuracy*100, 2)) + "%"
    cols[0].metric(label="ML Total Correct ", value=total_correct)
    cols[1].metric(label="ML Total Incorrect", value=total_incorrect)
    cols[2].metric(label="ML Accuracy", value=accuracy_str, delta=d_accuracy_str)


tab_experiment, tab_history, tab_automation, tab_stage, tab_lamella, tab_protocol, tab_telemetry = st.tabs(["Experiment", "Duration", "Automation", "Stage", "Lamella", "Protocol","Telemetry", ])

with tab_experiment:
    st.subheader("Experiment Analytics")

    # plot time series with x= step_n and y = timestamp with step  as hover text
    df_steps.dropna(inplace=True)
    df_steps.duration = df_steps.duration.astype(int)

    # convert timestamp to datetime, aus timezone 
    df_steps.timestamp = pd.to_datetime(df_steps.timestamp, unit="s")

    # convert timestamp to australian timezone
    df_steps.timestamp = df_steps.timestamp.dt.tz_localize("UTC").dt.tz_convert("Australia/Sydney")

    fig_timeline = px.scatter(df_steps, x="step_n", y="timestamp", color="stage", symbol="lamella",
        title="AutoLamella Timeline", 
        hover_name="stage", hover_data=df_steps.columns)
        # size = "duration", size_max=20)
    st.plotly_chart(fig_timeline, use_container_width=True)

    if len(df_click) > 0:
        df_click.dropna(inplace=True)

        # convert timestamp to datetime, aus timezone 
        df_click.timestamp = pd.to_datetime(df_click.timestamp, unit="s")

        # convert timestamp to australian timezone
        df_click.timestamp = df_click.timestamp.dt.tz_localize("UTC").dt.tz_convert("Australia/Sydney")

        import numpy as np
        df_click["magnitude"] = np.sqrt(df_click["dm_x"]**2 + df_click["dm_y"]**2)

        fig_timeline = px.scatter(df_click, x="timestamp", y="magnitude", color="stage", symbol="type",
            title="AutoLamella Interaction Timeline", 
            hover_name="stage", hover_data=df_click.columns,)
            # size = "duration", size_max=20)
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        tab_experiment.warning("No interaction data available")


with tab_history:
    # Duration
    cols = st.columns(2)
    fig_duration = px.bar(df_history, x="petname", y="duration", color="stage", barmode="group", hover_data=df_history.columns, title="Lamella Duration by Stage")
    cols[0].plotly_chart(fig_duration, use_container_width=True)

    # Duration
    fig_duration = px.bar(df_history, x="stage", y="duration", color="petname", barmode="group", hover_data=df_history.columns, title="Stage Duration by Lamella")
    cols[1].plotly_chart(fig_duration, use_container_width=True)

    # step breakdown
    # select a stage 
    st.markdown("---")
    _unique_stages = len(df_steps["stage"].unique())
    fig_steps = px.bar(df_steps, x="lamella", y="duration", color="step", title="Step Duration", 
        barmode="stack", facet_col="stage", facet_col_wrap=2, hover_data=df_steps.columns, height=200*_unique_stages )
    st.plotly_chart(fig_steps, use_container_width=True)

# timeline

with tab_telemetry:
    st.subheader("System Telemetry")
    if len(df_stage) > 0:
        # sort by timestamp
        df_stage.sort_values("timestamp", inplace=True)

        # convert timestamp to datetime, aus timezone
        df_stage.timestamp = pd.to_datetime(df_stage.timestamp, unit="s")
        df_stage.timestamp = df_stage.timestamp.dt.tz_localize("UTC").dt.tz_convert("Australia/Sydney")

        # plot as scatter with x = timestamp
        vals = ["x", "y", "z", "r", "t"]
        for val in ["x", "y", "z", "r", "t"]:
            fig = px.scatter(df_stage, x="timestamp", y=val, hover_data=df_stage.columns, color="stage",
                                title=f"Stage Position ({val})")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No telemetry data available")

with tab_automation:
    ## Automation
    st.subheader("Automation Analytics")

    ## CLICKS
    cols= st.columns(2)
    # user interaction (clicks)
    # drop beam_type column
    if len(df_click) > 0:
        # df_click.drop(columns=["beam_type"], inplace=True)

        fig = px.histogram(df_click, x="subtype", color="stage", facet_col="type",
            hover_data=df_click.columns,
            title="User Interaction (Click Count)")
        cols[0].plotly_chart(fig, use_container_width=True)

        # click size
        fig = px.scatter(df_click, x="dm_x", y="dm_y", 
            color="stage", symbol="subtype", facet_col="type", 
            hover_data=df_click.columns,
            title="User Interaction (Click Size)")

        cols[1].plotly_chart(fig, use_container_width=True)

        # # group by lamella
        df_click.sort_values("lamella", inplace=True)
        df_click_lamella = df_click.groupby(["lamella", "stage", "type", ]).count().reset_index()
        df_click_lamella.fillna(0, inplace=True)

        # add total column
        df_click_lamella["total"] = df_click_lamella.groupby(["lamella","stage",  "type"])["timestamp"].transform("sum")


        # drop all other columns except lamella and total, stage
        df_click_lamella = df_click_lamella[["lamella",  "stage", "type","total"]].drop_duplicates()

        # plot bar chart
        fig = px.bar(df_click_lamella, x="lamella", y="total", color="stage",
            hover_data=df_click_lamella.columns,
            title="User Interaction Per Lamella (Click Count)")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No interaction data available")


    ### ML

    # accuracy
    if len(df_det) > 0:
        cols = st.columns(2)
        df_group = df_det.groupby(["feature", "is_correct"]).count().reset_index() 
        df_group = df_group.pivot(index="feature", columns="is_correct", values="lamella")

        # if no false, add false column
        if "False" not in df_group.columns:
            df_group["False"] = 0
        if "True" not in df_group.columns:
            df_group["True"] = 0
        
        # fill missing values with zero
        df_group.fillna(0, inplace=True)

        df_group["total"] = df_group["True"] + df_group["False"]
        df_group["percent_correct"] = df_group["True"] / df_group["total"]
        df_group["percent_correct"] = df_group["percent_correct"].round(2)
        # df_group = df_group.sort_values(by="percent_correct", ascending=False)
        df_group.reset_index(inplace=True)

        # plot
        fig_acc = px.bar(df_group, x="feature", y="percent_correct", color="feature", title="ML Accuracy", hover_data=df_group.columns)
        fig_acc.update_yaxes(range=[0, 1])
        cols[0].plotly_chart(fig_acc, use_container_width=True)

        # precision
        fig_det = px.scatter(df_det, x="dpx_x", y="dpx_y", color="feature", symbol="stage",  hover_data=df_det.columns, title="ML Error Size")
        cols[1].plotly_chart(fig_det, use_container_width=True)


        # calculate accuracy per lamella per features
        df_group = df_det.groupby(["lamella", "feature", "is_correct"]).count().reset_index()
        df_group = df_group.pivot(index=["lamella", "feature"], columns="is_correct", values="stage")
        
        # if no false, add false column
        if "False" not in df_group.columns:
            df_group["False"] = 0
        if "True" not in df_group.columns:
            df_group["True"] = 0
        
        # fill missing values with zero
        df_group.fillna(0, inplace=True)

        df_group["total"] = df_group["True"] + df_group["False"]
        df_group["percent_correct"] = df_group["True"] / df_group["total"]
        df_group["percent_correct"] = df_group["percent_correct"].round(2)
        df_group.reset_index(inplace=True)
        # plot
        fig_acc = px.bar(df_group, x="lamella", y="percent_correct", color="feature", barmode="group", title="ML Accuracy Per Lamella", hover_data=df_group.columns)
        fig_acc.update_yaxes(range=[0, 1])
        st.plotly_chart(fig_acc, use_container_width=True)

        # calculate accuracy per stage per features
        df_group = df_det.groupby(["stage", "feature", "is_correct"]).count().reset_index()
        df_group = df_group.pivot(index=["stage", "feature"], columns="is_correct", values="timestamp")
        
        # if no false, add false column
        if "False" not in df_group.columns:
            df_group["False"] = 0
        if "True" not in df_group.columns:
            df_group["True"] = 0
        
        # fill missing values with zero
        df_group.fillna(0, inplace=True)

        df_group["total"] = df_group["True"] + df_group["False"]
        df_group["percent_correct"] = df_group["True"] / df_group["total"]
        df_group["percent_correct"] = df_group["percent_correct"].round(2)
        df_group.reset_index(inplace=True)

        # plot
        fig_acc = px.bar(df_group, x="feature", y="percent_correct", color="stage", barmode="group", title="ML Accuracy Per Stage", hover_data=df_group.columns)
        fig_acc.update_yaxes(range=[0, 1])
        st.plotly_chart(fig_acc, use_container_width=True)


        cols = st.columns(2)

        df_det_filt = df_det[["lamella", "stage", "feature", "is_correct", "fname"]].sort_values(by="lamella")


        petname = cols[0].selectbox(label="Petname", options=df_det_filt["lamella"].unique())
        feature = cols[0].selectbox(label="Feature", options=df_det_filt["feature"].unique())
        stage = cols[0].selectbox(label="Stage", options=df_det_filt["stage"].unique())

        # glob for all ml images
        ML_IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"**/{petname}/*ml-*.tif"), recursive=True))
        IMAGE_FILENAMES = [os.path.basename(path) for path in ML_IMAGE_PATHS]

        # select image
        IMAGE_FILENAMES = df_det_filt[(df_det_filt["lamella"] == petname) & (df_det_filt["feature"] == feature) & (df_det_filt["stage"] == stage)]["fname"].unique().tolist()
        image_filename = cols[0].selectbox(label="Image", options=IMAGE_FILENAMES)

        # get image path
        image_path = ML_IMAGE_PATHS[IMAGE_FILENAMES.index(image_filename)]

        image = FibsemImage.load(image_path)

        is_correct = df_det_filt[(df_det_filt["lamella"] == petname) & (df_det_filt["feature"] == feature) & (df_det_filt["stage"] == stage) & (df_det_filt["fname"] == image_filename)]["is_correct"].values[0]
        caption = f"Petname: {petname}, Feature: {feature}, Stage: {stage}, Correct: {is_correct}"

        cols[1].image(image.data, caption=caption, use_column_width=True)

        # TODO: get the actuall detection position into log

        # from fibsem import config as fcfg 
        # import tifffile as tff
        # from fibsem.segmentation.utils import decode_segmap
        
        # # join df and df_det_filt on fname / image
        # df = pd.read_csv(os.path.join(fcfg.DATA_ML_PATH, "data.csv"))
        # df.rename(columns={"image": "fname"}, inplace=True)
        # df_det_filt = df_det_filt.merge(df, on="fname", how="left")

        # image = FibsemImage.load(os.path.join(fcfg.DATA_ML_PATH, f"{image_filename}.tif"))
        # mask = tff.imread(os.path.join(fcfg.DATA_ML_PATH, "mask", f"{image_filename}.tif"))
        # mask = decode_segmap(mask, 3)

        # cols = st.columns(2)
        # cols[0].image(image.data, caption=caption, use_column_width=True)
        # cols[1].image(mask, caption=caption, use_column_width=True) # TODO: show overlay

    else:
        st.warning("No machine learning data available")

with tab_stage:
    # Stage Analytics
    st.subheader("Stage Analytics")

    # select stage
    stage = st.selectbox(label="Stage", options=df_history["stage"].unique())

    # plot duration
    fig_duration = px.bar(df_history[df_history["stage"] == stage].sort_values(by="start"), x="petname", y="duration", color="petname", hover_data=df_history.columns)
    st.plotly_chart(fig_duration, use_container_width=True)


    # get all images of this stage
    EB_IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"**/*{stage}_final_high_res_eb.tif"), recursive=True))
    IB_IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"**/*{stage}_final_high_res_ib.tif"), recursive=True))

    if IB_IMAGE_PATHS and EB_IMAGE_PATHS:
        # get petname (directory name) of each image
        petnames = [os.path.basename(os.path.dirname(path)) for path in IB_IMAGE_PATHS]
        # n_cols = max(int(len(IMAGE_PATHS)//2), 2)
        cols = st.columns(2)

        for i, (petname, fname_eb, fname_ib) in enumerate(zip(petnames, EB_IMAGE_PATHS, IB_IMAGE_PATHS)):
            eb_image = FibsemImage.load(fname_eb)
            ib_image = FibsemImage.load(fname_ib)
            cols[0].image(eb_image.data, caption=f"{petname} - {os.path.basename(fname_eb)}")
            cols[1].image(ib_image.data, caption=f"{petname} - {os.path.basename(fname_ib)}")


    if program == "autoliftout":
        from autolamella.liftout.structures import Experiment
        
    exp = Experiment.load(os.path.join(EXPERIMENT_PATH, "experiment.yaml"))

    # overview image
    st.markdown("---")
    st.subheader("Overview Image")

    # TODO: CACHE THIS IMAGE
    SHOW_OVERVIEW = st.checkbox(label="Show Overview Image", value=False)
    OVERVIEW_IMAGE = glob.glob(os.path.join(EXPERIMENT_PATH, "*overview*.tif"))
    if OVERVIEW_IMAGE and SHOW_OVERVIEW:
        cols = st.columns(2)
        image_fname = cols[0].selectbox(label="Overview Image", options=OVERVIEW_IMAGE)
        key2 = cols[0].selectbox(label="Stage Position", options=df_history["stage"].unique())

        @st.cache_data
        def _plot_positions(image_fname, key2, df_history):
            image = FibsemImage.load(image_fname)

            # loop through stages and create empty list
            # dictionary comprehension

            positions = {stage: [] for stage in df_history["stage"].unique()}

            for lamella in exp.positions:
                for state in lamella.history:
                    if state.stage.name in positions.keys():
                        _names = [pos.name for pos in positions[state.stage.name]]
                        if lamella._petname not in _names:
                            positions[state.stage.name].append(state.microscope_state.absolute_position)
                            positions[state.stage.name][-1].name = f"{lamella._petname}"

                        # go to next lamella if added 

            fig = _tile._plot_positions(image, positions[key2], show=True)

            return fig, positions

        fig, positions = _plot_positions(image_fname, key2, df_history)
        cols[0].write(positions[key2])

        cols[1].pyplot(fig)

with tab_lamella:
    st.subheader("Lamella Overview")

    cols = st.columns(2)
    lamella = cols[0].selectbox(label="Lamella", options=df_history["petname"].unique())

    IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"{lamella}/**.tif"), recursive=True))
    IMAGE_FILENAMES = [os.path.basename(path) for path in IMAGE_PATHS]
    IMAGE_FILENAME = cols[0].selectbox(label="Image", options=IMAGE_FILENAMES)

    image = FibsemImage.load(glob.glob(os.path.join(EXPERIMENT_PATH, f"{lamella}/**{IMAGE_FILENAME}"), recursive=True)[0])
    cols[1].image(image.data, caption=os.path.basename(IMAGE_FILENAME), use_column_width=True)

    st.subheader("Lamella History")
    cols = st.columns(2)
    cols[0].dataframe(df_history[df_history["petname"] == lamella])

    # plot duration
    fig_duration = px.bar(df_history[df_history["petname"] == lamella].sort_values(by="start"), x="stage", y="duration", color="stage", hover_data=df_history.columns)
    cols[1].plotly_chart(fig_duration, use_container_width=True)


    # plot steps
    st.subheader("Lamella Steps")

    cols = st.columns(2)
    cols[0].dataframe(df_steps[df_steps["lamella"] == lamella])

    fig_steps = px.bar(df_steps[df_steps["lamella"] == lamella].sort_values(by="timestamp"), x="stage", y="duration", color="step", hover_data=df_steps.columns)
    cols[1].plotly_chart(fig_steps, use_container_width=True)


    # loop through exp.position, return lamella that matches lamella
    st.subheader("Lamella Protocol")
    for lam in exp.positions:
        if lam._petname == lamella:
            cols = st.columns(2)
            k = cols[0].selectbox(label="Protocol Stage", options=lam.protocol.keys())
            cols[1].write(lam.protocol[k])

            # TODO: plot on image

with tab_protocol:
    # full protocol
    st.subheader("Full Protocol")
    from fibsem import utils

    protocol = utils.load_protocol(os.path.join(EXPERIMENT_PATH, "protocol.yaml"))

    st.write(protocol)