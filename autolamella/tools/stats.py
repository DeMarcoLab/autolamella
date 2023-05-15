import glob
import os
from copy import deepcopy

import liftout
import pandas as pd
import plotly.express as px
import streamlit as st
import autolamella
from autolamella.tools import data

BASE_PATH = os.path.dirname(autolamella.__file__)
LOG_PATH = os.path.join(BASE_PATH, "log")

st.set_page_config(layout="wide")
st.title("AutoLamella Statistics")

#################### EXPERIMENT SECTION ####################

# select experiment

path_cols = st.columns(2)
LOG_PATH = path_cols[0].text_input("Search Path", LOG_PATH)
FILTER_STR = path_cols[1].text_input("Filter", "*/")
paths = glob.glob(os.path.join(LOG_PATH, FILTER_STR))
EXPERIMENT_PATH = st.selectbox(label="Experiment Path ", options=paths)
# sample = load_experiment(EXPERIMENT_PATH)

df_sample, df_history, beam_shift_info, df_steps = data.calculate_statistics_dataframe(EXPERIMENT_PATH)

# experiment metrics
n_lamella = len(df_history["petname"])
n_images =  len(glob.glob(os.path.join(EXPERIMENT_PATH, "**/**.tif"), recursive=True))

st.markdown("---")

st.subheader("Timeline")
fig_timeline = px.scatter(df_steps, x="step_n", y="timestamp", color="stage", symbol='lamella')
st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

st.subheader("Stage duration")

# calculate difference in timestamp between rows
df_steps['delta'] = df_steps['timestamp'].diff()
steps_to_drop = ["MILLING_COMPLETED_SUCCESSFULLY", "MOVE_TO_POSITION_SUCCESSFUL", "FIDUCIAL_MILLED_SUCCESSFULLY", "MOVE_SUCCESSFUL"]
df_steps_filtered = df_steps[~df_steps["step"].isin(steps_to_drop)]
df_history_filtered = df_history[~df_history["stage"].isin(steps_to_drop)]

fig_duration1 = px.bar(df_steps_filtered, x="lamella", y="delta", color="step", facet_col="stage")
fig_duration2 = px.bar(df_history_filtered, x="stage", y="duration", color="petname", barmode="group")
st.plotly_chart(fig_duration1, use_container_width=True)
st.plotly_chart(fig_duration2, use_container_width=True)




