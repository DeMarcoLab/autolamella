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

st.set_page_config(layout="wide")
st.title("AutoLamella Analytics")

#################### EXPERIMENT SECTION ####################

# select experiment

path_cols = st.sidebar.columns(2)
LOG_PATH = st.sidebar.text_input("Log Path", cfg.LOG_PATH)
# FILTER_STR = path_cols[1].text_input("Filter", "*/")
paths = glob.glob(os.path.join(LOG_PATH, "*/"))
EXPERIMENT_NAME = st.sidebar.selectbox(label="Experiment ", options=[os.path.basename(os.path.dirname(path)) for path in paths])

EXPERIMENT_PATH = os.path.join(cfg.LOG_PATH, EXPERIMENT_NAME)

(df_experiment, df_history, 
df_beam_shift, 
    df_steps, df_stage, 
    df_det, df_click) = calculate_statistics_dataframe(EXPERIMENT_PATH)

# experiment metrics
n_lamella = len(df_history["petname"].unique())

n_trenches = len(df_history[df_history["stage"] == "MillTrench"]["petname"].unique())
n_undercut = len(df_history[df_history["stage"] == "MillUndercut"]["petname"].unique())
n_polish = len(df_history[df_history["stage"] == "MillPolishingCut"]["petname"].unique())



cols = st.columns(4)
cols[0].metric(label="Lamella", value=n_lamella)
cols[1].metric(label="Trenches", value=n_trenches)
cols[2].metric(label="Undercut", value=n_undercut)
cols[3].metric(label="Polish", value=n_polish)

st.markdown("---")

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
    hover_name="stage", hover_data=["lamella", "step_n", "step"],)
    # size = "duration", size_max=20)
st.plotly_chart(fig_timeline, use_container_width=True)


# Duration
fig_duration = px.bar(df_history, x="stage", y="duration", color="petname", barmode="group", hover_data=df_history.columns, title="Stage Duration")
st.plotly_chart(fig_duration, use_container_width=True)

# step breakdown
# select a stage 
st.markdown("---")
_unique_stages = len(df_steps["stage"].unique())
fig_steps = px.bar(df_steps, x="lamella", y="duration", color="step", title="Step Duration", 
    barmode="stack", facet_col="stage", facet_col_wrap=2, hover_data=df_steps.columns, height=200*_unique_stages )
st.plotly_chart(fig_steps, use_container_width=True)

# timeline

## Automation

st.markdown("---")
st.subheader("Automation Analytics")


## CLICKS
cols= st.columns(2)
# user interaction (clicks)

st.dataframe(df_click)
# drop beam_type column
df_click.drop(columns=["beam_type"], inplace=True)

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


### ML

# accuracy
df_group = df_det.groupby(["feature", "is_correct"]).count().reset_index() 
df_group = df_group.pivot(index="feature", columns="is_correct", values="lamella")
df_group["total"] = df_group["True"] + df_group["False"]
df_group["percent_correct"] = df_group["True"] / df_group["total"]
df_group["percent_correct"] = df_group["percent_correct"].round(2)
df_group = df_group.sort_values(by="percent_correct", ascending=False)
df_group.reset_index(inplace=True)

# plot
fig_acc = px.bar(df_group, x="feature", y="percent_correct", color="feature", title="ML Accuracy", hover_data=df_group.columns)
cols[0].plotly_chart(fig_acc, use_container_width=True)

# precision
fig_det = px.scatter(df_det, x="dpx_x", y="dpx_y", color="stage", symbol="feature",  hover_data=df_det.columns, title="ML Error Size")
cols[1].plotly_chart(fig_det, use_container_width=True)



# Stage Analytics

st.markdown("---")
st.subheader("Stage Analytics")

# select stage
stage = st.selectbox(label="Stage", options=df_history["stage"].unique())

# plot duration
fig_duration = px.bar(df_history[df_history["stage"] == stage].sort_values(by="start"), x="petname", y="duration", color="petname", hover_data=df_history.columns)
st.plotly_chart(fig_duration, use_container_width=True)


# get all images of this stage
IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"**/*{stage}_final_high_res_ib.tif"), recursive=True))

if IMAGE_PATHS:
    # get petname (directory name) of each image
    petnames = [os.path.basename(os.path.dirname(path)) for path in IMAGE_PATHS]
    n_cols = max(int(len(IMAGE_PATHS)//2), 2)
    cols = st.columns(n_cols)

    for i, (petname, fname) in enumerate(zip(petnames, IMAGE_PATHS)):
        image = FibsemImage.load(fname)
        idx = i % n_cols
        cols[idx].image(image.data, caption=f"{os.path.basename(os.path.dirname(fname))} - {os.path.basename(fname)}")


exp = Experiment.load(os.path.join(EXPERIMENT_PATH, "experiment.yaml"))

# overview image
st.markdown("---")
st.subheader("Overview Image")
OVERVIEW_IMAGE = glob.glob(os.path.join(EXPERIMENT_PATH, "*overview*.tif"))
if OVERVIEW_IMAGE:
    image_fname = st.selectbox(label="Overview Image", options=OVERVIEW_IMAGE)
    image = FibsemImage.load(image_fname)

    key2 = st.selectbox(label="Stage Position", options=df_history["stage"].unique())

    # loop through stages and create empty list
    # dictionary comprehension

    positions = {stage: [] for stage in df_history["stage"].unique()}

    for lamella in exp.positions:
        for state in lamella.history:
            
            if state.stage.name in positions.keys():
                positions[state.stage.name].append(state.microscope_state.absolute_position)
                positions[state.stage.name][-1].name = f"{lamella._petname}"


    st.write(positions[key2])

    fig = _tile._plot_positions(image, positions[key2], show=True)
    st.pyplot(fig)


st.markdown("---")
st.subheader("Lamella Overview")
lamella = st.selectbox(label="Lamella", options=df_history["petname"].unique())

cols = st.columns(2)

IMAGE_PATHS = sorted(glob.glob(os.path.join(EXPERIMENT_PATH, f"{lamella}/**.tif"), recursive=True))
IMAGE_FILENAME = cols[0].selectbox(label="Image", options=IMAGE_PATHS)

image = FibsemImage.load(IMAGE_FILENAME)
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

for lam in exp.positions:
    if lam._petname == lamella:
        st.write(lam.protocol)