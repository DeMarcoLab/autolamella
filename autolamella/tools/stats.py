import glob
import os
from copy import deepcopy

import pandas as pd
import plotly.express as px
import streamlit as st
import autolamella
from autolamella.tools.data import calculate_statistics_dataframe

BASE_PATH = os.path.dirname(autolamella.__file__)
LOG_PATH = os.path.join(BASE_PATH, "log")

st.set_page_config(layout="wide")
st.title("AutoLamella Analytics")

#################### EXPERIMENT SECTION ####################

# select experiment

path_cols = st.columns(2)
LOG_PATH = path_cols[0].text_input("Search Path", LOG_PATH)
FILTER_STR = path_cols[1].text_input("Filter", "*/")
paths = glob.glob(os.path.join(LOG_PATH, FILTER_STR))
EXPERIMENT_PATH = st.selectbox(label="Experiment Path ", options=paths)

df_experiment, df_history, df_beam_shift, df_steps, df_stage = calculate_statistics_dataframe(EXPERIMENT_PATH)

# experiment metrics
n_lamella = len(df_history["petname"])
# n_images =  len(glob.glob(os.path.join(EXPERIMENT_PATH, "**/**.tif"), recursive=True))

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
fig_steps = px.bar(df_steps, x="lamella", y="duration", color="step", title="Step Duration", 
    barmode="stack", facet_col="stage", facet_col_wrap=2, hover_data=df_steps.columns, height=2000 )
st.plotly_chart(fig_steps, use_container_width=True)

# timeline




# overview image
st.markdown("---")

# select box
st.subheader("Overview Image")


from fibsem.structures import FibsemImage
from autolamella.structures import Experiment
from fibsem.imaging import _tile

OVERVIEW_IMAGE = glob.glob(os.path.join(EXPERIMENT_PATH, "*overview*.tif"))
image_fname = st.selectbox(label="Overview Image", options=OVERVIEW_IMAGE)
image = FibsemImage.load(image_fname)

key = st.selectbox(label="Stage", options=df_history["stage"].unique())



# loop through stages and create empty list
# dictionary comprehension

# exp = Experiment.load(os.path.join(EXPERIMENT_PATH, "experiment.yaml"))

# positions = {stage: [] for stage in df_history["stage"].unique()}

# for lamella in exp.positions:
#     for state in lamella.history:
        
#         if state.stage.name in positions.keys():
#             positions[state.stage.name].append(state.microscope_state.absolute_position)
#             positions[state.stage.name][-1].name = f"{lamella._petname}"


# st.write(positions[key])


# fig = _tile._plot_positions(image, positions[key], show=True)
# st.pyplot(fig)


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

