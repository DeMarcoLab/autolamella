import logging

from fibsem.ui import utils as fui
from PyQt5 import QtWidgets

from autolamella import config as cfg
from autolamella.structures import Experiment


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