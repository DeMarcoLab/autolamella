

import random
import sys
from copy import deepcopy
from pprint import pprint
from typing import Dict, Tuple

import numpy as np
from napari.qt.threading import thread_worker
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
)

from autolamella.structures import AutoLamellaStage, Experiment, Lamella, AutoLamellaOnGridMethod, AutoLamellaProtocol
from autolamella.ui.qt import AutoLamellaWorkflowDialog as AutoLamellaWorkflowDialogUI
from autolamella.workflows.core import supervise_map

PATH = "/home/patrick/github/autolamella/autolamella/log/AutoLamella-2025-01-09-12-34/experiment.yaml"

exp = Experiment.load(PATH)
pos = exp.positions[0]

for i in range(3):
    exp.positions.append(deepcopy(pos))
    exp.positions[-1].petname = f"Position {i+1}"

    # randomly select a state from states, and assign it to state
    current_stage = random.choice(list(pos.states.keys()))
    exp.positions[-1].state = deepcopy(pos.states[current_stage])

# pprint(pos.states)

START_FROM_MAP: Dict[AutoLamellaStage, AutoLamellaStage] = {
    AutoLamellaStage.SetupLamella: AutoLamellaStage.Created,
    AutoLamellaStage.MillRough: AutoLamellaStage.SetupLamella,
    AutoLamellaStage.MillPolishing: AutoLamellaStage.MillRough,
    AutoLamellaStage.MillTrench: AutoLamellaStage.ReadyTrench,
    AutoLamellaStage.MillUndercut: AutoLamellaStage.MillTrench,
    AutoLamellaStage.Finished: AutoLamellaStage.Finished,
}
START_STATES = [k for k in START_FROM_MAP.keys()]

# invert the START_FROM_MAP
NEXT_WORKFLOW_STAGE: Dict[AutoLamellaStage, AutoLamellaStage] = {
    AutoLamellaStage.Created: AutoLamellaStage.SetupLamella,
    AutoLamellaStage.SetupLamella: AutoLamellaStage.MillRough,
    # AutoLamellaStage.ReadyLamella: AutoLamellaStage.MillRough,
    AutoLamellaStage.MillRough: AutoLamellaStage.MillPolishing,
    AutoLamellaStage.MillPolishing: AutoLamellaStage.Finished,
    AutoLamellaStage.ReadyTrench: AutoLamellaStage.MillUndercut,
    AutoLamellaStage.MillTrench: AutoLamellaStage.MillUndercut,
    AutoLamellaStage.Finished: AutoLamellaStage.Finished,
} 

print(START_STATES)

def get_start_state(self, start_from: AutoLamellaStage) -> AutoLamellaStage:
    return START_FROM_MAP.get(start_from, None)

Lamella.get_start_state = get_start_state

class AutoLamellaWorkflowDialog(QDialog, AutoLamellaWorkflowDialogUI.Ui_Dialog):

    def __init__(self, experiment: Experiment, protocol: AutoLamellaProtocol, parent=None):
        super().__init__(parent=parent)
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())
        self.setupUi(self)
        self.parent = parent



        # print("ON GRID WORKFLOW: ", AutoLamellaOnGridMethod.workflow)
        self.method = AutoLamellaOnGridMethod

        self.experiment = exp

        self.setup_connections()

    def setup_connections(self):

        self.label_method.setText(f"Method: {self.method.name}")

        self.buttonBox.button(QDialogButtonBox.Ok).setText("Start")

        # connect buttonBox events
        self.buttonBox.accepted.connect(self.on_start)
        self.buttonBox.rejected.connect(self.on_exit)

        # self.groupBox_lamella.setVisible(False)

        pos: Lamella       
        self.gridLayout_lamella.addWidget(QLabel("Name"), 0, 0)
        self.gridLayout_lamella.addWidget(QLabel("Last Completed"), 0, 1)
        # self.gridLayout_lamella.addWidget(QLabel("Start From"), 0, 2)

        for i, pos in enumerate(self.experiment.positions, 1):
            name_label = QLabel(pos.name)
            status_label = QLabel(pos.status)
            control_widget = QComboBox()
            control_widget.addItems([s.name for s in START_STATES])
            # print(f"Next stage: {NEXT_WORKFLOW_STAGE[pos.stage].name}")
            control_widget.setCurrentText(NEXT_WORKFLOW_STAGE[pos.workflow].name)

            self.gridLayout_lamella.addWidget(name_label, i, 0)
            self.gridLayout_lamella.addWidget(status_label, i, 1)
            # self.gridLayout_lamella.addWidget(control_widget, i, 2)

        self.workflow_widgets: Dict[AutoLamellaStage, Tuple[QCheckBox, QCheckBox]] = {}

        METHOD_WORKFLOW = [s for s in START_STATES if s in self.method.workflow]

        for i, state in enumerate(METHOD_WORKFLOW):
            label = QLabel(state.name)
            enable_checkbox = QCheckBox()
            enable_checkbox.setChecked(True)
            enable_checkbox.setText("Enable")

            supervised_checkbox = QCheckBox()
            supervised_checkbox.setChecked(True)
            supervised_checkbox.setText("Supervised")

            self.gridLayout_workflow.addWidget(label, i, 0)
            self.gridLayout_workflow.addWidget(enable_checkbox, i, 1)
            self.gridLayout_workflow.addWidget(supervised_checkbox, i, 2)

            self.workflow_widgets[state] = (enable_checkbox, supervised_checkbox)


    def get_workflow_settings(self) -> Dict[AutoLamellaStage, Tuple[bool, bool]]:
        return {state: (enable.isChecked(), supervised.isChecked()) for state, (enable, supervised) in self.workflow_widgets.items()}

    def on_start(self):
        print("Start")

        wf = self.get_workflow_settings()

        # v = complete stage, supervise stage
        stages_to_complete = [k for k, v in wf.items() if v[0]]
        print(f"Stages to complete: {stages_to_complete}")

        # supervision
        for stage, (enable, supervised) in wf.items():
            print(supervise_map[stage.name], supervised)

        self.accept()

    def on_exit(self):
        print("Exit")
        self.reject()


def main():
    app = QApplication(sys.argv)
    dialog = AutoLamellaWorkflowDialog(experiment=exp, protocol=None)
    _ = dialog.exec_()


if __name__ == "__main__":
    main()