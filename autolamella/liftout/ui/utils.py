import logging
import os
from pathlib import Path

import numpy as np
import yaml
from fibsem import utils as fibsem_utils
from fibsem.ui import utils as fui
from PyQt5 import QtWidgets

from autolamella.liftout.config import config as cfg
from autolamella.liftout.structures import Experiment, Lamella


def update_stage_label(label: QtWidgets.QLabel, lamella: Lamella):

    stage = lamella.state.stage
    status_colors = {
        "Initialisation": "gray",
        "Setup": "gold",
        "MillTrench": "coral",
        "MillUndercut": "coral",
        "Liftout": "seagreen",
        "Landing": "dodgerblue",
        "MillRoughCut": "mediumpurple",
        "MillPolishingCut": "cyan",
        "Finished": "silver",
        "Failure": "gray",
    }
    label.setText(f"Lamella {lamella._number:02d} \n{stage.name}")
    label.setStyleSheet(
        str(
            f"background-color: {status_colors[stage.name]}; color: white; border-radius: 5px"
        )
    )


def play_audio_alert(freq: int = 1000, duration: int = 500) -> None:
    import winsound

    winsound.Beep(freq, duration)


def setup_experiment_ui_v2(
    parent_ui: QtWidgets.QMainWindow, new_experiment: bool = True
):
    """Setup the experiment by either creating or loading a sample"""

    # new_experiment
    if new_experiment:
        experiment = create_experiment_ui(
            parent_ui
        )
    # load experiment
    else:
        experiment = load_experiment_ui(parent_ui)
        if experiment is not None:
            logging.info(f"Experiment {experiment.name} loaded.")
            logging.info(f"{len(experiment.positions)} lamella loaded from {experiment.path}")

    return experiment


def load_experiment_ui(parent) -> Experiment:
   
    PATH = fui._get_file_ui(
        msg="Select an experiment file", path=cfg.LOG_PATH, parent=parent
    )

    if PATH == "":
        logging.info("No path selected")
        return

    return Experiment.load(PATH)


def create_experiment_ui(parent,
) -> Experiment:

    PATH = fui._get_directory_ui(
        msg="Select a directory to save the experiment",
        path=cfg.LOG_PATH,
        parent=parent,
    )
    if PATH == "":
        logging.info("No path selected")
        return

    # get name

    # get current date
    from datetime import datetime

    now = datetime.now()
    DATE = now.strftime("%Y-%m-%d-%H-%M")
    NAME, okPressed = fui._get_text_ui(
        msg="Enter a name for the experiment", title="Experiment Name", default=f"{cfg.EXPERIMENT_NAME}-{DATE}", parent=parent
    )

    if NAME == "" or not okPressed:
        logging.info("No name selected")
        return

    experiment = Experiment(path=PATH, name=NAME)
    experiment.save()
    return experiment


def update_milling_protocol_ui(
    milling_pattern, milling_stages: list, parent_ui=None
):

    config_filename, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent_ui,
        "Select Protocol File",
        cfg.BASE_PATH,
        "Yaml Files (*.yml, *.yaml)",
    )
    # from fibsem.ui import utils as ui_utils
    # config_filename, _ = ui_utils.open_existing_file_ui(parent = parent_ui,
    #     caption = "Select Protocol File", directory = config.BASE_PATH,
    #     filter_ext:="Yaml Files (*.yml, *.yaml)")

    if config_filename == "":
        raise ValueError("No protocol file was selected.")

    protocol = fibsem_utils.load_protocol(config_filename)

    protocol_key = cfg.PATTERN_PROTOCOL_MAP[milling_pattern]

    if len(milling_stages) == 1:
        stage_settings = list(milling_stages.values())[0]
        protocol[protocol_key].update(stage_settings)

    else:
        stage_settings = list(milling_stages.values())[0]
        protocol[protocol_key].update(stage_settings)
        for i, stage_settings in enumerate(milling_stages.values()):
            protocol[protocol_key]["protocol_stages"][i].update(stage_settings)

    # save yaml file
    with open(config_filename, "w") as f:
        yaml.safe_dump(protocol, f)

    logging.info(f"Updated protocol: {config_filename}")
    # TODO: i dont think this updates the current protocol? need to refresh in that case


def create_overview_image(experiment: Experiment) -> np.ndarray:

    import scipy.ndimage as ndi

    PAD_PX = 10
    BASE_SHAPE = None

    vstack = None
    for i, lamella in enumerate(experiment.positions):

        hstack = None
        for fname in cfg.DISPLAY_REFERENCE_FNAMES:

            path = os.path.join(lamella.path, f"{fname}.tif")

            if os.path.exists(path):
                image = lamella.load_reference_image(fname).thumbnail
            else:
                image = np.zeros(shape=BASE_SHAPE)

            if BASE_SHAPE is None:
                BASE_SHAPE = image.data.shape

            image = np.pad(image.data, pad_width=PAD_PX)

            if hstack is None:
                hstack = image
            else:
                hstack = np.hstack([hstack, image])

        hstack = np.pad(hstack, pad_width=PAD_PX)
        if vstack is None:
            vstack = hstack
        else:
            vstack = np.vstack([vstack, hstack])

    vstack = vstack.astype(np.uint8)
    overview_image = ndi.median_filter(vstack, size=3)

    return overview_image


def get_completion_stats(experiment: Experiment) -> tuple:
    """Get the current completetion stats for lifout"""
    from liftout.structures import AutoLiftoutStage

    n_stages = AutoLiftoutStage.Finished.value  # init and failure dont count

    lam: Lamella
    active_lam = 0
    completed_stages = 0
    for lam in experiment.positions:

        # dont count failure
        if lam.is_failure or lam.state.stage.value == 99:
            continue

        active_lam += 1
        completed_stages += lam.state.stage.value

    total_stages = n_stages * active_lam
    perc_complete = completed_stages / total_stages

    return n_stages, active_lam, completed_stages, total_stages, perc_complete
