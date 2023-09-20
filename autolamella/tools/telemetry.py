import streamlit as st

from autolamella.tools import _parser

import plotly.express as px


st.set_page_config(layout="wide", page_title="AutoLamella Telemetry")
st.title("AutoLamella Telemetry")


DEFAULT_PATH = r"C:\Users\Admin\Github\fibsem\scratch\health-monitor\data2.csv"

PATH = st.text_input("Path to telemetry data", DEFAULT_PATH)

@st.cache_data
def _load_data(PATH):
    return _parser._parse_health_monitor_data(PATH) 

df_data = _load_data(PATH)

# FILTER BY SUBSYSTEM
st.write("### FILTER BY SUBSYSTEM ###")

subsystems = df_data.columns.str.split(".").str[0].unique().tolist()
subsystem = st.selectbox("Select Subsystem", subsystems)
# also keep datetime column
subsystem_cols =  ["datetime"] + [col for col in df_data.columns if subsystem in col]


# TODO: filter once only for all


df_subsystem = df_data[subsystem_cols]
# drop rows with all NaN values excluding datetime column
# drop columns with all NaN values excluding datetime column
df_subsystem = df_subsystem.dropna(axis=0, how="all", subset=df_subsystem.columns[1:])
df_subsystem = df_subsystem.dropna(axis=1, how="all")

# filter by component
components = df_subsystem.columns.str.split(".").str[1].unique().tolist()

component_list = st.multiselect("Select Components", ["ALL"] + components, default=["ALL"])
if "ALL" not in component_list:
    component_cols = ["datetime"]
    for comp in component_list:
        component_cols += [col for col in df_subsystem.columns if comp in col ]
    df_subsystem = df_subsystem[component_cols]


# filter by parameter
parameters = df_subsystem.columns.str.split(".").str[2].unique().tolist()
parameter_list = st.multiselect("Select Parameters", ["ALL"] + parameters, default=["ALL"])
if "ALL" not in parameter_list:
    parameter_cols = ["datetime"]
    for param in parameter_list:
        parameter_cols += [col for col in df_subsystem.columns if param in col ]
    df_subsystem = df_subsystem[parameter_cols]


df_subsystem = df_subsystem.dropna(axis=0, how="all", subset=df_subsystem.columns[1:])
df_subsystem = df_subsystem.dropna(axis=1, how="all")

if len(df_subsystem) == 0:
    st.write("No data to display")
    st.stop()

st.write(subsystem, component_list, parameter_list)
st.write(f"{len(df_subsystem)} rows, {len(df_subsystem.columns)-1} columns ({subsystem})")
st.write(df_subsystem)

fig = px.line(df_subsystem, x="datetime", y=df_subsystem.columns[1:], title=f"Health Monitor Data - {subsystem}")
st.plotly_chart(fig, use_container_width=True)
