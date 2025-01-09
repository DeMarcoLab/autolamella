import sys

try:
    sys.modules.pop("PySide6.QtCore")
except Exception:
    pass
import logging
import os
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import napari
import napari.utils.notifications
import yaml
from fibsem import constants, utils
from fibsem.microscope import FibsemMicroscope
from fibsem.milling import get_milling_stages, get_protocol_from_stages
from fibsem.structures import (
    BeamType,
    FibsemRectangle,
    FibsemStagePosition,
    MicroscopeSettings,
    Point,
)
from fibsem.ui import (
    DETECTION_AVAILABLE,
    FibsemCryoDepositionWidget,
    FibsemImageSettingsWidget,
    FibsemMillingWidget,
    FibsemMinimapWidget,
    FibsemMovementWidget,
    FibsemSystemSetupWidget,
    stylesheets,
)
from fibsem.ui import (
    utils as fui,
)
from fibsem.ui.napari.patterns import remove_all_napari_shapes_layers
from napari.qt.threading import thread_worker
from PyQt5.QtCore import pyqtSignal
from qtpy import QtWidgets

from autolamella.structures import get_autolamella_method

if DETECTION_AVAILABLE: # ml dependencies are option, so we need to check if they are available
    from fibsem.ui.FibsemEmbeddedDetectionWidget import FibsemEmbeddedDetectionUI

import autolamella
import autolamella.config as cfg
from autolamella.protocol.validation import (
    FIDUCIAL_KEY,
    MICROEXPANSION_KEY,
    MILL_POLISHING_KEY,
    MILL_ROUGH_KEY,
    NOTCH_KEY,
    TRENCH_KEY,
    validate_protocol,
)
from autolamella.structures import (
    AutoLamellaStage,
    Experiment,
    Lamella,
    LamellaState,
    create_new_lamella,
    AutoLamellaMethod,
    AutoLamellaProtocol,
    AutoLamellaProtocolOptions,
)
from autolamella.ui import AutoLamellaMainUI
from autolamella.ui.utils import setup_experiment_ui_v2

try:
    from fibsem.segmentation.utils import list_available_checkpoints
except ImportError as e:
    logging.debug(f"Could not import list_available_checkpoints from fibsem.segmentation.utils: {e}")
    def list_available_checkpoints():
        return []

AUTOLAMELLA_CHECKPOINTS = list_available_checkpoints()

CONFIGURATION = {
    "TABS_ID": {
        0: "Connection",
        1: "Experiment",
        2: "Protocol",
        3: "Image",
        4: "Movement",
        5: "Milling",
        6: "Detection",
        7: "Manipulator",
    },
    "SHOW_INDIVIDUAL_STAGES": True,
}

# invert the dictionary
CONFIGURATION["TABS"] = {v: k for k, v in CONFIGURATION["TABS_ID"].items()}

# instructions
INSTRUCTIONS = {
    "NOT_CONNECTED": "Please connect to the microscope (System -> Connect to Microscope).",
    "NO_EXPERIMENT": "Please create or load an experiment (File -> Create / Load Experiment)",
    "NO_PROTOCOL": "Please load a protocol (File -> Load Protocol).",
    "NO_LAMELLA": "Please Add Lamella Positions (Experiment -> Add Lamella).",
    "TRENCH_READY": "Trench Positions Selected. Ready to Run Waffle Trench.",
    "UNDERCUT_READY": "Undercut Positions Selected. Ready to Run Waffle Undercut.",
    "LAMELLA_READY": "Lamella Positions Selected. Ready to Run Setup AutoLamella.",
    "AUTOLAMELLA_READY": "Lamella Positions Selected. Ready to Run AutoLamella.",
}

ON_GRID_METHODS = ["autolamella-on-grid", "autolamella-waffle"]
TRENCH_METHODS = [
    "autolamella-waffle",
    "autolamella-trench",
    "autolamella-liftout",
    "autolamella-serial-liftout",
]
LIFTOUT_METHODS = ["autolamella-liftout", "autolamella-serial-liftout"]

def _is_method_type(method: str, method_type: str) -> bool:
    if method_type == "trench":
        return method in TRENCH_METHODS
    elif method_type == "liftout":
        return method in LIFTOUT_METHODS
    elif method_type == "on-grid":
        return method in ON_GRID_METHODS
    else:
        return False

def _find_matching_position(position: FibsemStagePosition, experiment: Experiment) -> int:
    """Find the matching position in the experiment."""
    lamella_names = [lamella.name for lamella in experiment.positions]
    idx = lamella_names.index(position.name)
    return idx


# preparation stages
PREPARTION_WORKFLOW_STAGES = [
    AutoLamellaStage.Created,
    AutoLamellaStage.PositionReady,
]

# TODO: when autolamella is closed, also close the minimap...
class AutoLamellaUI(AutoLamellaMainUI.Ui_MainWindow, QtWidgets.QMainWindow):
    workflow_update_signal = pyqtSignal(dict)
    detection_confirmed_signal = pyqtSignal(bool)
    update_experiment_signal = pyqtSignal(Experiment)
    run_milling_signal = pyqtSignal()
    sync_positions_to_minimap_signal = pyqtSignal(list)
    lamella_created_signal = pyqtSignal(Lamella)

    def __init__(self, viewer: napari.Viewer) -> None:
        super().__init__()

        self.setupUi(self)

        self.label_title.setText(f"AutoLamella v{autolamella.__version__}")

        self.viewer = viewer
        self.viewer.window.main_menu.setVisible(False)
        self.viewer.window.qt_viewer.dockLayerList.setVisible(False)
        self.viewer.window.qt_viewer.dockLayerControls.setVisible(False)

        # @self.viewer.bind_key("Ctrl+M") # TODO: this has weird behaviour for the menu visible / hover
        # def _show_main_menu(viewer: napari.Viewer):
        #     viewer.window.main_menu.setVisible(True)

        self.IS_MICROSCOPE_UI_LOADED: bool = False
        self.is_protocol_loaded: bool = False
        self.UPDATING_PROTOCOL_UI: bool = False

        self.experiment: Experiment = None
        self.worker = None
        self.microscope: FibsemMicroscope = None
        self.settings: MicroscopeSettings = None

        self.system_widget: FibsemSystemSetupWidget = FibsemSystemSetupWidget(
            microscope=self.microscope,
            settings=self.settings,
            viewer=self.viewer,
            parent=self,
        )
        self.tabWidget.insertTab(
            CONFIGURATION["TABS"]["Connection"], self.system_widget, "Connection"
        )

        self.image_widget: FibsemImageSettingsWidget = None
        self.movement_widget: FibsemMovementWidget = None
        self.milling_widget: FibsemMillingWidget = None
        self.minimap_widget: FibsemMinimapWidget = None

        self.WAITING_FOR_USER_INTERACTION: bool = False
        self.USER_RESPONSE: bool = False
        self.WAITING_FOR_UI_UPDATE: bool = False
        self.MILLING_IS_RUNNING: bool = False
        self.WORKFLOW_IS_RUNNING: bool = False
        self.STOP_WORKFLOW: bool = False

        # setup connections
        self.setup_connections()

    def setup_connections(self):

        # lamella controls
        self.pushButton_add_lamella.clicked.connect(
            lambda: self.add_new_lamella(stage_position=None)
        )
        self.pushButton_remove_lamella.clicked.connect(self.remove_lamella_ui)
        self.pushButton_go_to_lamella.clicked.connect(self.move_to_lamella_position)
        self.comboBox_current_lamella.currentIndexChanged.connect(
            self.update_lamella_ui
        )
        self.pushButton_save_position.clicked.connect(self.save_lamella_ui)
        self.pushButton_fail_lamella.clicked.connect(self.fail_lamella_ui)
        self.pushButton_revert_stage.clicked.connect(self.revert_stage)

        # workflow controls
        self.pushButton_run_waffle_trench.clicked.connect(
            lambda: self._run_workflow(workflow="trench")
        )
        self.pushButton_run_waffle_undercut.clicked.connect(
            lambda: self._run_workflow(workflow="undercut")
        )
        self.pushButton_run_setup_autolamella.clicked.connect(
            lambda: self._run_workflow(workflow="autolamella")
        )
        self.pushButton_setup_autoliftout.clicked.connect(
            lambda: self._run_workflow(workflow="setup-liftout")
        )
        self.pushButton_run_autoliftout.clicked.connect(
            lambda: self._run_workflow(workflow="autoliftout")
        )
        self.pushButton_run_serial_liftout_landing.clicked.connect(
            lambda: self._run_workflow(workflow="serial-liftout-landing")
        )

        # workflow button group
        self.workflow_buttons = [
            self.pushButton_run_waffle_trench,
            self.pushButton_run_waffle_undercut,
            self.pushButton_run_setup_autolamella,
            self.pushButton_setup_autoliftout,
            self.pushButton_run_autoliftout,
            self.pushButton_run_serial_liftout_landing,
        ]
        for button in self.workflow_buttons:
            button.setVisible(False)

        self.pushButton_update_protocol.clicked.connect(self.export_protocol_ui)

        # system widget
        self.system_widget.connected_signal.connect(self.connect_to_microscope)
        self.system_widget.disconnected_signal.connect(self.disconnect_from_microscope)

        # file menu
        self.actionNew_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Protocol.triggered.connect(self.load_protocol)
        self.actionSave_Protocol.triggered.connect(self.export_protocol_ui)
        # tool menu
        self.actionCryo_Deposition.triggered.connect(self.cryo_deposition)
        self.actionCryo_Deposition.setEnabled(False) # TMP: disable until tested
        self.actionCryo_Deposition.setToolTip("Cryo Deposition is currently disabled via the UI.")
        self.actionOpen_Minimap.triggered.connect(self.open_minimap_widget)
        # help menu
        self.actionInformation.triggered.connect(
            lambda: fui.open_information_dialog(self.microscope, self)
        )

        # workflow interaction
        self.pushButton_stop_workflow.setVisible(False)
        self.pushButton_stop_workflow.clicked.connect(self._stop_workflow_thread)
        self.pushButton_yes.clicked.connect(self.push_interaction_button)
        self.pushButton_no.clicked.connect(self.push_interaction_button)

        # signals
        self.detection_confirmed_signal.connect(self.handle_confirmed_detection_signal)
        self.update_experiment_signal.connect(self.hande_update_experiment_signal)
        self.workflow_update_signal.connect(self.handle_workflow_update)
        self.run_milling_signal.connect(self.run_milling)

        self.pushButton_stop_workflow.setStyleSheet(stylesheets.RED_PUSHBUTTON_STYLE)
        self.pushButton_add_lamella.setStyleSheet(stylesheets.GREEN_PUSHBUTTON_STYLE)
        self.pushButton_remove_lamella.setStyleSheet(stylesheets.RED_PUSHBUTTON_STYLE)
        self.pushButton_go_to_lamella.setStyleSheet(stylesheets.BLUE_PUSHBUTTON_STYLE)

        # comboboxes
        self.comboBox_method.addItems(cfg.AUTOLAMELLA_METHODS)
        self.comboBox_method.currentIndexChanged.connect(
            lambda: self.update_protocol_ui(False)
        )
        self.comboBox_ml_checkpoint.addItems(AUTOLAMELLA_CHECKPOINTS)

        self.comboBox_options_liftout_joining_method.addItems(cfg.LIFTOUT_JOIN_METHODS)
        self.comboBox_options_landing_joining_method.addItems(cfg.LIFTOUT_LANDING_JOIN_METHODS)

        AVAILABLE_POSITIONS = utils._get_positions()
        self.comboBox_options_trench_start_position.addItems(AVAILABLE_POSITIONS)
        self.comboBox_options_landing_start_position.addItems(AVAILABLE_POSITIONS)

        # workflow info
        self.set_current_workflow_message(msg=None, show=False)

        # refresh ui
        self.update_ui()

    def update_protocol_ui(self, _load: bool = True):
        if not self.is_protocol_loaded or self.UPDATING_PROTOCOL_UI:
            return

        self.UPDATING_PROTOCOL_UI = True

        if _load:
            method = self.settings.protocol["options"]["method"]
            self.comboBox_method.setCurrentIndex(
                cfg.AUTOLAMELLA_METHODS.index(method.lower())
            )  # TODO: coerce this to be a supported method, alert the user if not
        else:
            method = self.comboBox_method.currentText().lower()

        self.lineEdit_name.setText(
            self.settings.protocol["options"].get("name", "autolamella-protocol")
        )

        # options
        self.checkBox_align_use_fiducial.setChecked(
            self.settings.protocol["options"].get("use_fiducial", True)
        )

        self.beamshift_attempts.setValue(
            self.settings.protocol["options"].get("alignment_attempts", 3)
        )
        self.checkBox_align_at_milling_current.setChecked(
            self.settings.protocol["options"].get("alignment_at_milling_current", True)
        )

        self.checkBox_take_final_reference_images.setChecked(
            self.settings.protocol["options"].get("take_final_reference_images", True)
        )
        self.checkBox_take_final_high_quality_reference.setChecked(
            self.settings.protocol["options"]
            .get("high_quality_image", {})
            .get("enabled", False)
        )

        # lamella
        self.doubleSpinBox_lamella_tilt_angle.setValue(
            self.settings.protocol["options"].get("lamella_tilt_angle", 18)
        )
        self.checkBox_use_microexpansion.setChecked(
            self.settings.protocol["options"].get("use_microexpansion", True)
        )
        self.checkBox_use_notch.setChecked(
            self.settings.protocol["options"].get("use_notch", True)
        )

        # supervision
        self.checkBox_setup.setChecked(
            self.settings.protocol["options"]["supervise"].get("setup_lamella", True)
        )
        self.checkBox_supervise_mill_rough.setChecked(
            self.settings.protocol["options"]["supervise"].get("mill_rough", True)
        )
        self.checkBox_supervise_mill_polishing.setChecked(
            self.settings.protocol["options"]["supervise"].get("mill_polishing", True)
        )

        # TRENCH METHOD ONLY (waffle, serial-liftout)
        is_trench_method = _is_method_type(method, "trench")
        if is_trench_method:
            # supervision
            self.checkBox_trench.setChecked(
                self.settings.protocol["options"]["supervise"].get("trench", True)
            )
            self.checkBox_undercut.setChecked(
                self.settings.protocol["options"]["supervise"].get("undercut", True)
            )

            # machine learning
            self.comboBox_ml_checkpoint.setCurrentText(
                self.settings.protocol["options"].get(
                    "checkpoint", cfg.DEFAULT_CHECKPOINT
                )
            )

            # undercut
            self.doubleSpinBox_undercut_tilt.setValue(
                self.settings.protocol["options"].get("undercut_tilt_angle", -5)
            )

        self.checkBox_trench.setVisible(is_trench_method)
        self.checkBox_undercut.setVisible(is_trench_method)

        self.label_ml_header.setVisible(is_trench_method)
        self.label_ml_checkpoint.setVisible(is_trench_method)
        self.comboBox_ml_checkpoint.setVisible(is_trench_method)

        self.doubleSpinBox_undercut_tilt.setVisible(is_trench_method)
        self.label_protocol_undercut_tilt_angle.setVisible(is_trench_method)

        # autoliftout components
        is_liftout_method = _is_method_type(method, "liftout")
        IS_CLASSIC_LIFTOUT_METHOD = method == "autolamella-liftout"
        IS_SERIAL_LIFTOUT_METHOD = method == "autolamella-serial-liftout"
        self.checkBox_options_confirm_next_stage.setVisible(is_liftout_method)
        self.label_options_trench_start_position.setVisible(is_liftout_method)
        self.label_options_liftout_joining_method.setVisible(
            is_liftout_method and IS_CLASSIC_LIFTOUT_METHOD
        )
        self.label_options_landing_start_position.setVisible(is_liftout_method)
        self.label_options_landing_joining_method.setVisible(
            is_liftout_method and IS_CLASSIC_LIFTOUT_METHOD
        )
        self.comboBox_options_trench_start_position.setVisible(is_liftout_method)
        self.comboBox_options_liftout_joining_method.setVisible(
            is_liftout_method and IS_CLASSIC_LIFTOUT_METHOD
        )
        self.comboBox_options_landing_start_position.setVisible(is_liftout_method)
        self.comboBox_options_landing_joining_method.setVisible(
            is_liftout_method and IS_CLASSIC_LIFTOUT_METHOD
        )
        self.label_section_thickness.setVisible(
            is_liftout_method and IS_SERIAL_LIFTOUT_METHOD
        )
        self.doubleSpinBox_section_thickness.setVisible(
            is_liftout_method and IS_SERIAL_LIFTOUT_METHOD
        )
        self.checkBox_supervise_liftout.setVisible(is_liftout_method)
        self.checkBox_supervise_landing.setVisible(is_liftout_method)

        # disable some options for serial liftout
        self.checkBox_use_microexpansion.setVisible(not is_liftout_method)
        self.checkBox_use_notch.setVisible(not is_liftout_method)

        if is_liftout_method:
            self.checkBox_options_confirm_next_stage.setChecked(
                self.settings.protocol["options"].get("confirm_next_stage", True)
            )
            self.comboBox_options_liftout_joining_method.setCurrentText(
                self.settings.protocol["options"].get("liftout_joining_method", "None")
            )
            self.comboBox_options_landing_joining_method.setCurrentText(
                self.settings.protocol["options"].get("landing_joining_method", "Weld")
            )

            self.comboBox_options_trench_start_position.setCurrentText(
                self.settings.protocol["options"]["trench_start_position"]
            )
            self.comboBox_options_landing_start_position.setCurrentText(
                self.settings.protocol["options"]["landing_start_position"]
            )

            self.doubleSpinBox_section_thickness.setValue(
                self.settings.protocol["milling"]["landing-sever"].get(
                    "section_thickness", 4e-6
                )
                * constants.SI_TO_MICRO
            )

            # supervision
            self.checkBox_supervise_liftout.setChecked(
                bool(
                    self.settings.protocol["options"]["supervise"].get("liftout", True)
                )
            )
            self.checkBox_supervise_landing.setChecked(
                bool(
                    self.settings.protocol["options"]["supervise"].get("landing", True)
                )
            )

        self.UPDATING_PROTOCOL_UI = False

    def export_protocol_ui(self):
        if self.is_protocol_loaded is False:
            return
        self.settings.protocol["options"]["name"] = self.lineEdit_name.text()
        self.settings.protocol["options"]["method"] = (
            self.comboBox_method.currentText().lower()
        )

        # options
        self.settings.protocol["options"]["use_fiducial"] = (
            self.checkBox_align_use_fiducial.isChecked()
        )
        self.settings.protocol["options"]["alignment_attempts"] = int(
            self.beamshift_attempts.value()
        )
        self.settings.protocol["options"]["alignment_at_milling_current"] = (
            self.checkBox_align_at_milling_current.isChecked()
        )
        self.settings.protocol["options"]["take_final_reference_images"] = (
            self.checkBox_take_final_reference_images.isChecked()
        )
        self.settings.protocol["options"].get("high_quality_image", {})["enabled"] = (
            self.checkBox_take_final_high_quality_reference.isChecked()
        )

        self.settings.protocol["options"]["lamella_tilt_angle"] = (
            self.doubleSpinBox_lamella_tilt_angle.value()
        )
        self.settings.protocol["options"]["use_microexpansion"] = (
            self.checkBox_use_microexpansion.isChecked()
        )
        self.settings.protocol["options"]["use_notch"] = (
            self.checkBox_use_notch.isChecked()
        )

        # supervision
        self.settings.protocol["options"]["supervise"]["setup_lamella"] = (
            self.checkBox_setup.isChecked()
        )
        self.settings.protocol["options"]["supervise"]["mill_rough"] = (
            self.checkBox_supervise_mill_rough.isChecked()
        )
        self.settings.protocol["options"]["supervise"]["mill_polishing"] = (
            self.checkBox_supervise_mill_polishing.isChecked()
        )

        if _is_method_type(self.settings.protocol["options"]["method"], "trench"):
            # supervision
            self.settings.protocol["options"]["supervise"]["trench"] = (
                self.checkBox_trench.isChecked()
            )
            self.settings.protocol["options"]["supervise"]["undercut"] = (
                self.checkBox_undercut.isChecked()
            )

            # machine learning
            self.settings.protocol["options"]["checkpoint"] = (
                self.comboBox_ml_checkpoint.currentText()
            )

            # undercut
            self.settings.protocol["options"]["undercut_tilt_angle"] = (
                self.doubleSpinBox_undercut_tilt.value()
            )

        if _is_method_type(self.settings.protocol["options"]["method"], "liftout"):
            # supervision
            self.settings.protocol["options"]["confirm_next_stage"] = (
                self.checkBox_options_confirm_next_stage.isChecked()
            )
            self.settings.protocol["options"]["supervise"]["liftout"] = (
                self.checkBox_supervise_liftout.isChecked()
            )
            self.settings.protocol["options"]["supervise"]["landing"] = (
                self.checkBox_supervise_landing.isChecked()
            )

            # joining methods
            self.settings.protocol["options"]["liftout_joining_method"] = (
                self.comboBox_options_liftout_joining_method.currentText()
            )
            self.settings.protocol["options"]["landing_joining_method"] = (
                self.comboBox_options_landing_joining_method.currentText()
            )

            # start positions
            self.settings.protocol["options"]["trench_start_position"] = (
                self.comboBox_options_trench_start_position.currentText()
            )
            self.settings.protocol["options"]["landing_start_position"] = (
                self.comboBox_options_landing_start_position.currentText()
            )

            self.settings.protocol["milling"]["landing-sever"]["section_thickness"] = (
                self.doubleSpinBox_section_thickness.value() * constants.MICRO_TO_SI
            )

        if self.sender() == self.actionSave_Protocol:
            path = fui.open_save_file_dialog(
                msg="Save protocol",
                path=cfg.PROTOCOL_PATH,
                _filter="*yaml",
                parent=self,
            )
            utils.save_yaml(path, self.settings.protocol)

            logging.info("Protocol saved to file")
        elif self.sender() == self.pushButton_update_protocol:
            logging.info("Protocol updated")

        # auto save copy to experiment folder
        if self.experiment:
            utils.save_yaml(
                os.path.join(self.experiment.path, "protocol.yaml"),
                self.settings.protocol,
            )  # Q: do we really wanna overwrite this file?

        napari.utils.notifications.show_info("Protocol updated.")
        self.update_ui()

    def setup_experiment(self):
        new_experiment = bool(self.sender() is self.actionNew_Experiment)
        experiment = setup_experiment_ui_v2(self, new_experiment=new_experiment)

        if experiment is None:
            napari.utils.notifications.show_info("Experiment not loaded.")
            return

        self.experiment = experiment
        napari.utils.notifications.show_info(
            f"Experiment {self.experiment.name} loaded."
        )
        if self.settings is not None:
            self.settings.image.path = self.experiment.path

        # register metadata
        if cfg._REGISTER_METADATA:
            import autolamella  # NB: microscope needs to be connected beforehand

            utils._register_metadata(
                microscope=self.microscope,
                application_software="autolamella",
                application_software_version=autolamella.__version__,
                experiment_name=self.experiment.name,
                experiment_method="null",
            )  # TODO: add method to experiment

        # automatically re-load protocol if available
        if not new_experiment and self.settings is not None:
            # try to load protocol from file
            PROTOCOL_PATH = os.path.join(self.experiment.path, "protocol.yaml")
            if os.path.exists(PROTOCOL_PATH):
                self.settings.protocol = utils.load_protocol(
                    protocol_path=PROTOCOL_PATH
                )
                self.is_protocol_loaded = True
                self.update_protocol_ui(_load=True)

        self.update_lamella_combobox()
        self.update_ui()

    ##################################################################

    # TODO: move this to system wideget??
    # TODO: create a dialog to get the user to connect to microscope and create load experiment before continuing
    # then remove the system widget entirely... you will always be connected once you start
    def connect_to_microscope(self):
        self.microscope = self.system_widget.microscope
        self.settings = self.system_widget.settings
        if self.experiment is not None:
            self.settings.image.path = self.experiment.path
        self.update_microscope_ui()
        self.update_ui()

    def disconnect_from_microscope(self):
        self.microscope = None
        self.settings = None
        self.update_microscope_ui()
        self.update_ui()

    def update_microscope_ui(self):
        """Update the ui based on the current state of the microscope."""

        if self.microscope is not None and not self.IS_MICROSCOPE_UI_LOADED:
            # reusable components
            self.image_widget = FibsemImageSettingsWidget(
                microscope=self.microscope,
                image_settings=self.settings.image,
                viewer=self.viewer,
                parent=self,
            )
            self.movement_widget = FibsemMovementWidget(
                microscope=self.microscope,
                viewer=self.viewer,
                parent=self,
            )
            self.milling_widget = FibsemMillingWidget(
                microscope=self.microscope,
                viewer=self.viewer,
                parent=self,
            )

            # add widgets to tabs
            self.tabWidget.insertTab(
                CONFIGURATION["TABS"]["Image"], self.image_widget, "Image"
            )
            self.tabWidget.insertTab(
                CONFIGURATION["TABS"]["Movement"], self.movement_widget, "Movement"
            )
            self.tabWidget.insertTab(
                CONFIGURATION["TABS"]["Milling"], self.milling_widget, "Milling"
            )

            # add the detection widget if ml dependencies are available
            self.det_widget = None
            if DETECTION_AVAILABLE:
                self.det_widget = FibsemEmbeddedDetectionUI(
                    viewer=self.viewer,
                    model=None,
                )
                self.tabWidget.insertTab(
                    CONFIGURATION["TABS"]["Detection"], self.det_widget, "Detection"
                )

            self.IS_MICROSCOPE_UI_LOADED = True
            self.milling_widget.milling_position_changed.connect(
                self._update_milling_position
            )
            self.milling_widget.milling_progress_signal.connect(self.handle_milling_update)
            self.image_widget.acquisition_progress_signal.connect(self.handle_acquisition_update)
        else:
            if self.image_widget is None:
                return

            # remove tabs
            self.tabWidget.removeTab(CONFIGURATION["TABS"]["Detection"])
            self.tabWidget.removeTab(CONFIGURATION["TABS"]["Milling"])
            self.tabWidget.removeTab(CONFIGURATION["TABS"]["Movement"])
            self.tabWidget.removeTab(CONFIGURATION["TABS"]["Image"])
            self.tabWidget.removeTab(CONFIGURATION["TABS"]["Protocol"])

            self.image_widget.clear_viewer()
            self.image_widget.deleteLater()
            self.movement_widget.deleteLater()
            self.milling_widget.deleteLater()
            if self.det_widget is not None:
                self.det_widget.deleteLater()

            self.IS_MICROSCOPE_UI_LOADED = False

#### MINIMAP

    def open_minimap_widget(self):
        if self.microscope is None:
            napari.utils.notifications.show_warning(
                "Please connect to a microscope first... [No Microscope Connected]"
            )
            return

        if self.movement_widget is None:
            napari.utils.notifications.show_warning(
                "Please connect to a microscope first... [No Movement Widget]"
            )
            return

        if self.experiment is None:
            napari.utils.notifications.show_warning(
                "Please load an experiment first... [No Experiment Loaded]"
            )
            return
        
        # update image path
        self.settings.image.path = self.experiment.path
        self.image_widget.image_settings.path = self.experiment.path

        self.viewer_minimap = napari.Viewer(ndisplay=2)
        self.minimap_widget = FibsemMinimapWidget(
            viewer=self.viewer_minimap,
            parent=self
        )
        self.viewer_minimap.window.add_dock_widget(
            widget=self.minimap_widget,
            area="right",
            add_vertical_stretch=True,
            name="AutoLamella Minimap",
        )

        self.sync_experiment_positions_to_minimap()

        self.minimap_widget.stage_position_added_signal.connect(
            self.add_position_from_minimap
        )
        self.minimap_widget.stage_position_updated_signal.connect(
            self.update_position_from_minimap
        )
        self.minimap_widget.stage_position_removed_signal.connect(
            self.remove_position_from_minimap
        )
        napari.run(max_loop_level=2)

    def add_position_from_minimap(self, position: FibsemStagePosition):
        """Add the position to the experiment when added in the minimap."""
        lamella = self.add_new_lamella(position)
        self.lamella_created_signal.emit(lamella)

    def update_position_from_minimap(self, position: FibsemStagePosition):
        """Update the position in the experiment when updated in the minimap."""
        idx = _find_matching_position(position, self.experiment)
        if idx == -1:
            logging.warning(f"Position {position.name} not found in experiment.")
            return

        self.experiment.positions[idx].state.microscope_state.stage_position = position
        self.experiment.save()
        self.update_ui() # TODO: convert to signals

    def remove_position_from_minimap(self, position: FibsemStagePosition):
        """Remove the corresponding position from the experiment when removed from the minimap."""
        idx = _find_matching_position(position, self.experiment)
        
        # check if not found
        if idx == -1:
            logging.warning(f"Position {position.name} not found in experiment.")
            return

        self.experiment.positions.pop(idx)
        self.experiment.save()
        self.update_lamella_combobox()
        self.update_ui() # TODO: convert to signals

    def sync_experiment_positions_to_minimap(self):
        """Sync the current experiment positions to the minimap."""

        # TODO: replace this manual syncing with a shared data model
        if self.minimap_widget is None:
            logging.debug("Minimap widget not loaded.")
            return

        if self.experiment is None:
            logging.warning("No experiment loaded")
            return
        
        # get the updated positions
        positions = [
            lamella.state.microscope_state.stage_position
            for lamella in self.experiment.positions
        ]

        self.sync_positions_to_minimap_signal.emit(positions)


##### LAMELLA CONTROLS

    def update_ui(self):
        """Update the ui based on the current state of the application."""

        # state flags
        is_experiment_loaded = bool(self.experiment is not None)
        is_microscope_connected = bool(self.microscope is not None)
        is_protocol_loaded = bool(self.settings is not None) and self.is_protocol_loaded
        has_lamella = bool(self.experiment.positions) if is_experiment_loaded else False
        is_experiment_ready = is_experiment_loaded and is_protocol_loaded

        # force order: connect -> experiment -> protocol
        self.tabWidget.setTabVisible(
            CONFIGURATION["TABS"]["Experiment"], is_microscope_connected
        )
        self.tabWidget.setTabVisible(
            CONFIGURATION["TABS"]["Protocol"], is_protocol_loaded
        )
        self.actionNew_Experiment.setVisible(is_microscope_connected)
        self.actionLoad_Experiment.setVisible(is_microscope_connected)
        self.actionInformation.setVisible(is_microscope_connected)

        # workflow

        # setup experiment -> connect to microscope -> select lamella -> run autolamella
        self.pushButton_fail_lamella.setVisible(has_lamella)
        self.pushButton_revert_stage.setVisible(has_lamella)
        self.comboBox_lamella_history.setVisible(has_lamella)
        self.pushButton_lamella_landing_selected.setVisible(has_lamella)

        # experiment loaded
        # file menu
        self.actionLoad_Protocol.setVisible(is_experiment_loaded)
        self.actionSave_Protocol.setVisible(is_protocol_loaded)
        # tool menu
        self.menuTools.setVisible(is_protocol_loaded)
        self.actionCryo_Deposition.setVisible(is_protocol_loaded)
        self.actionOpen_Minimap.setVisible(is_protocol_loaded)
        self.actionLoad_Minimap_Image.setVisible(is_protocol_loaded)
        self.actionLoad_Positions.setVisible(is_protocol_loaded)
        # help menu

        # labels
        if is_experiment_loaded:
            self.label_experiment_name.setText(f"Experiment: {self.experiment.name}")

            # TODO: migrate to list view + interactive buttons / checkboxes
            # Lamella Name: Status (Failure Note)
            msg = "\nLamella Info:\n"
            for lamella in self.experiment.positions:
                fnote = f"{lamella.failure_note[:10]}"
                fmsg = f"\t FAILED ({fnote})" if lamella.is_failure else ""
                msg += f"Lamella {lamella.name} \t\t {lamella.status} {fmsg} \n"
            self.label_info.setText(msg)

            self.comboBox_current_lamella.setVisible(has_lamella)

        if is_protocol_loaded:
            method = self.settings.protocol["options"].get("method", "NULL")
            self.label_protocol_name.setText(
                f"Protocol: {self.settings.protocol['options'].get('name', 'protocol')} ({method.title()} Method)"
            )

        # buttons
        self.pushButton_add_lamella.setEnabled(is_experiment_ready)
        self.pushButton_remove_lamella.setEnabled(has_lamella)
        self.pushButton_save_position.setEnabled(has_lamella)
        self.pushButton_go_to_lamella.setEnabled(has_lamella)

        # set visible if protocol loaded
        self.pushButton_add_lamella.setVisible(is_experiment_ready)
        self.pushButton_remove_lamella.setVisible(is_experiment_ready)
        self.pushButton_save_position.setVisible(is_experiment_ready)
        self.pushButton_go_to_lamella.setVisible(is_experiment_ready)
        self.label_current_lamella_header.setVisible(is_experiment_ready)
        self.comboBox_current_lamella.setVisible(is_experiment_ready)
        self.label_info.setVisible(is_experiment_ready)
        self.label_setup_header.setVisible(is_experiment_ready)

        # workflow buttons
        if is_experiment_ready:
            method = self.settings.protocol["options"].get("method", None)
            is_trench_method = _is_method_type(method, "trench")
            is_liftout_method = _is_method_type(method, "liftout")
            is_serial_liftout_method = method == "autolamella-serial-liftout"


            # check the status of each lamella
            workflow_state_counter = Counter([p.state.stage.name for p in self.experiment.positions])
            ready_for_trench = workflow_state_counter[AutoLamellaStage.PositionReady.name] > 0
            ready_for_undercut = workflow_state_counter[AutoLamellaStage.MillTrench.name] > 0
            ready_for_liftout = workflow_state_counter[AutoLamellaStage.MillUndercut.name] > 0
            ready_for_landing = workflow_state_counter[AutoLamellaStage.LiftoutLamella.name] > 0
            has_landed = workflow_state_counter[AutoLamellaStage.LandLamella.name] > 0
            ready_for_setup_lamella = workflow_state_counter[AutoLamellaStage.PositionReady.name] > 0
            ready_for_rough = (workflow_state_counter[AutoLamellaStage.SetupLamella.name] > 0)
            ready_for_polish = workflow_state_counter[AutoLamellaStage.MillRough.name] > 0
            ready_for_autolamella = ready_for_rough or ready_for_polish or has_landed

            # flags to show buttons
            show_undercut = is_trench_method and method != "autolamella-trench"

            # flags to enable workflows
            enable_trench = is_trench_method and ready_for_trench
            enable_undercut = is_trench_method and ready_for_undercut
            enable_liftout = is_liftout_method and (
                ready_for_trench 
                or ready_for_undercut 
                or ready_for_liftout
            )
            enable_landing = is_liftout_method and ready_for_landing
            enable_lamella = ready_for_setup_lamella
            enable_autolamella = ready_for_autolamella

            # if any of the stages are ready, enable the autolamella button
            enable_full_autolamella = (
                enable_lamella
                or enable_autolamella
                or enable_trench
                or enable_undercut
            )

            # trench
            self.pushButton_run_waffle_trench.setVisible(is_trench_method)
            self.pushButton_run_waffle_trench.setEnabled(enable_trench)
            self.pushButton_run_waffle_undercut.setVisible(show_undercut)
            self.pushButton_run_waffle_undercut.setEnabled(enable_undercut)
            # liftout
            self.pushButton_setup_autoliftout.setVisible(is_liftout_method)
            self.pushButton_run_autoliftout.setVisible(is_liftout_method)
            self.pushButton_run_serial_liftout_landing.setVisible(is_serial_liftout_method)
            self.pushButton_run_autoliftout.setEnabled(enable_liftout)
            self.pushButton_run_serial_liftout_landing.setEnabled(enable_landing)
            # autolamella
            self.pushButton_run_setup_autolamella.setVisible(True)
            self.pushButton_run_setup_autolamella.setEnabled(enable_full_autolamella)
            self.label_run_autolamella_info.setVisible(enable_full_autolamella)

            self.pushButton_run_waffle_trench.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if enable_trench
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )
            self.pushButton_run_waffle_undercut.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if enable_undercut
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )
            self.pushButton_run_setup_autolamella.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if enable_full_autolamella
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )
            # liftout
            self.pushButton_setup_autoliftout.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if is_liftout_method
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )
            self.pushButton_run_autoliftout.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if enable_liftout
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )
            self.pushButton_run_serial_liftout_landing.setStyleSheet(
                stylesheets.GREEN_PUSHBUTTON_STYLE
                if enable_landing
                else stylesheets.DISABLED_PUSHBUTTON_STYLE
            )

            # global button visibility configuration
            show_individual_workflows = CONFIGURATION["SHOW_INDIVIDUAL_STAGES"]
            self.pushButton_run_waffle_trench.setVisible(show_individual_workflows and is_trench_method)
            self.pushButton_run_waffle_undercut.setVisible(show_individual_workflows and show_undercut)

            # tab visibity / enabled
            # self.tabWidget.setTabVisible(CONFIGURATION["TABS"]["Detection"], self.WORKFLOW_IS_RUNNING and not _ON_GRID_METHOD)
            # self.tabWidget.setTabEnabled(CONFIGURATION["TABS"]["Connection"], not self.WORKFLOW_IS_RUNNING)
            # self.tabWidget.setTabEnabled(CONFIGURATION["TABS"]["Experiment"], not self.WORKFLOW_IS_RUNNING)
            # self.tabWidget.setTabEnabled(CONFIGURATION["TABS"]["Protocol"], not self.WORKFLOW_IS_RUNNING)

            if self.WORKFLOW_IS_RUNNING:
                self.pushButton_run_waffle_trench.setEnabled(False)
                self.pushButton_run_waffle_undercut.setEnabled(False)
                self.pushButton_run_setup_autolamella.setEnabled(False)
                self.pushButton_run_waffle_trench.setStyleSheet(
                    stylesheets.DISABLED_PUSHBUTTON_STYLE
                )
                self.pushButton_run_waffle_undercut.setStyleSheet(
                    stylesheets.DISABLED_PUSHBUTTON_STYLE
                )
                self.pushButton_run_setup_autolamella.setStyleSheet(
                    stylesheets.DISABLED_PUSHBUTTON_STYLE
                )

        # Current Lamella Status
        if has_lamella:
            self.update_lamella_ui()

        if not is_microscope_connected:
            self.set_instructions_msg(INSTRUCTIONS["NOT_CONNECTED"])
        elif not is_experiment_loaded:
            self.set_instructions_msg(INSTRUCTIONS["NO_EXPERIMENT"])
        elif not is_protocol_loaded:
            self.set_instructions_msg(INSTRUCTIONS["NO_PROTOCOL"])
        elif not has_lamella:
            self.set_instructions_msg(INSTRUCTIONS["NO_LAMELLA"])
        elif has_lamella:
            self.set_instructions_msg(INSTRUCTIONS["AUTOLAMELLA_READY"])

    def update_lamella_combobox(self, latest: bool = False):
        # detail combobox
        idx = self.comboBox_current_lamella.currentIndex()
        self.comboBox_current_lamella.currentIndexChanged.disconnect()
        self.comboBox_current_lamella.clear()
        self.comboBox_current_lamella.addItems(
            [lamella.info for lamella in self.experiment.positions]
        )
        if idx != -1 and self.experiment.positions:
            self.comboBox_current_lamella.setCurrentIndex(idx)
        if latest and self.experiment.positions:
            self.comboBox_current_lamella.setCurrentIndex(
                len(self.experiment.positions) - 1
            )
        self.comboBox_current_lamella.currentIndexChanged.connect(
            self.update_lamella_ui
        )

    def update_lamella_ui(self):
        # set the info for the current selected lamella
        if self.experiment is None:
            return

        if self.experiment.positions == []:
            return

        if self.WORKFLOW_IS_RUNNING:
            return

        idx = self.comboBox_current_lamella.currentIndex()
        if idx == -1:
            return

        lamella: Lamella = self.experiment.positions[idx]
        logging.info(f"Updating Lamella UI for {lamella.info}")

        # buttons
        if self.is_protocol_loaded:
            
            method = self.settings.protocol["options"].get("method", None)
            setup_state, ready_state = AutoLamellaStage.Created, AutoLamellaStage.PositionReady

            if lamella.workflow is setup_state:
                self.pushButton_save_position.setText("Save Position")
                self.pushButton_save_position.setStyleSheet(
                    stylesheets.ORANGE_PUSHBUTTON_STYLE
                )
                self.pushButton_save_position.setEnabled(True)
                self.milling_widget.CAN_MOVE_PATTERN = True
            elif lamella.workflow is ready_state:
                self.pushButton_save_position.setText("Position Ready")
                self.pushButton_save_position.setStyleSheet(
                    stylesheets.GREEN_PUSHBUTTON_STYLE
                )
                self.pushButton_save_position.setEnabled(True)
                self.milling_widget.CAN_MOVE_PATTERN = False
            else:
                self.pushButton_save_position.setText("")
                self.pushButton_save_position.setStyleSheet(
                    stylesheets.DISABLED_PUSHBUTTON_STYLE
                )
                self.pushButton_save_position.setEnabled(False)
                self.milling_widget.CAN_MOVE_PATTERN = True

            # landing grid selected
            if _is_method_type(method, "liftout"): 
                # TODO: refactor how this is handled, only select it during workflow...
                self.pushButton_lamella_landing_selected.setVisible(True)
                if lamella.landing_selected:
                    self.pushButton_lamella_landing_selected.setText(
                        "Landing Position Selected"
                    )
                    self.pushButton_lamella_landing_selected.setStyleSheet(
                        stylesheets.GREEN_PUSHBUTTON_STYLE
                    )
                    self.pushButton_lamella_landing_selected.setEnabled(True)
                else:
                    self.pushButton_lamella_landing_selected.setEnabled(False)
                    self.pushButton_lamella_landing_selected.setText(
                        "No Landing Position"
                    )
                    self.pushButton_lamella_landing_selected.setStyleSheet(
                        stylesheets.ORANGE_PUSHBUTTON_STYLE
                    )
                    self.pushButton_lamella_landing_selected.setToolTip(
                        "Run Setup Liftout to select a Landing Position"
                    )
            else:
                self.pushButton_lamella_landing_selected.setVisible(False)

        # update the milling widget
        if self.WORKFLOW_IS_RUNNING:
            self.milling_widget.CAN_MOVE_PATTERN = True

        if lamella.workflow in PREPARTION_WORKFLOW_STAGES:
            if not self.is_protocol_loaded:
                raise ValueError("I SHOULDNT BE ABLE TO GET HERE")
            
            method = self.settings.protocol["options"].get("method", None)
            display_trench = _is_method_type(method, "trench")
            display_lamella = not _is_method_type(method, "trench")

            if display_trench:
                stages = get_milling_stages(TRENCH_KEY, lamella.protocol)

            # TODO: convert to using .stages directly on lamella, rather than always reading from protocol

            if display_lamella:
                mill_rough_stages = get_milling_stages(MILL_ROUGH_KEY, lamella.protocol)
                mill_polishing_stages = get_milling_stages(MILL_POLISHING_KEY, lamella.protocol)
                stages = mill_rough_stages + mill_polishing_stages

                if self.settings.protocol["options"].get("use_notch", True):
                    stages.extend(get_milling_stages(NOTCH_KEY, lamella.protocol))

                # microexpansion
                if self.settings.protocol["options"].get("use_microexpansion", True):
                    stages.extend(get_milling_stages(MICROEXPANSION_KEY, lamella.protocol))

                # fiducial
                if self.settings.protocol["options"].get("use_fiducial", True):
                    stages.extend(get_milling_stages(FIDUCIAL_KEY, lamella.protocol))

            self.milling_widget.set_milling_stages(stages)

            # TODO: migrate to this structure instead of the above
            # milling_workflows: Dict[str, List[FibsemMillingStage]]: 
            #     # MILL_ROUGH_KEY: [FibsemMillingStage, FibsemMillingStage]
            #     # MILL_POLISHING_KEY: [FibsemMillingStage, FibsemMillingStage]
            #     # NOTCH_KEY: [FibsemMillingStage]
            #     # MICROEXPANSION_KEY: [FibsemMilling
            #     # FIDUCIAL_KEY: [FibsemMillingStage]

            # milling widget?
            # add / remove workflow?
            # when used independently, only single workflow?
            # when used in autolamella, multiple workflows?
        
        # failure button
        msg = "Mark Lamella as Active" if lamella.is_failure else "Mark Lamella As Failed"
        self.pushButton_fail_lamella.setText(msg)
        
        # time travel controls
        def to_state_str(state: LamellaState):
            return f"{state.stage.name} ({datetime.fromtimestamp(state.end_timestamp).strftime('%I:%M%p')})"

        has_history = bool(lamella.history)
        self.comboBox_lamella_history.setVisible(has_history)
        self.pushButton_revert_stage.setVisible(has_history)
        if has_history:
            self.comboBox_lamella_history.clear()
            self.comboBox_lamella_history.addItems([to_state_str(state) for state in lamella.history])

    def _update_milling_position(self):
        # triggered when milling position is moved
        if self.experiment is None:
            return

        if self.experiment.positions == []:
            return

        idx = self.comboBox_current_lamella.currentIndex()
        lamella: Lamella = self.experiment.positions[idx]

        if lamella.workflow not in PREPARTION_WORKFLOW_STAGES:
            return

        logging.info(f"Updating Lamella Pattern for {lamella.info}")

        # update the trench point
        method = self.settings.protocol["options"].get("method", None)
        self._update_milling_protocol(idx=idx, method=method, stage=lamella.workflow)

        self.experiment.save()

    def load_protocol(self):
        """Load a protocol from file."""

        if self.settings is None:
            napari.utils.notifications.show_info(
                "Please connect to the microscope first."
            )
            return

        PROTOCOL_PATH = fui.open_existing_file_dialog(
            msg="Select a protocol file", path=cfg.PROTOCOL_PATH, parent=self
        )

        if PROTOCOL_PATH == "":
            napari.utils.notifications.show_info("No path selected")
            return

        protocol = validate_protocol(utils.load_protocol(protocol_path=PROTOCOL_PATH))

        self.settings.protocol = protocol
        self.is_protocol_loaded = True
        self.update_protocol_ui(_load=True)
        napari.utils.notifications.show_info(
            f"Loaded Protocol from {os.path.basename(PROTOCOL_PATH)}"
        )

        # save a copy of the protocol to the experiment.path
        if self.experiment:
            utils.save_yaml(
                os.path.join(self.experiment.path, "protocol.yaml"),
                self.settings.protocol,
            )

        self.update_ui()

    def cryo_deposition(self):
        cryo_deposition_widget = FibsemCryoDepositionWidget(
            self.microscope, self.settings
        )
        cryo_deposition_widget.exec_()

    def set_instructions_msg(
        self,
        msg: str = "",
        pos: Optional[str] = None,
        neg: Optional[str] = None,
    ) -> None:
        """Set the instructions message, and user interaction buttons.
        Args:
            msg: The message to display.
            pos: The positive button text.
            neg: The negative button text.
        """
        self.label_instructions.setText(msg)
        self.pushButton_yes.setText(pos)
        self.pushButton_no.setText(neg)

        # enable buttons
        self.pushButton_yes.setEnabled(pos is not None)
        self.pushButton_yes.setVisible(pos is not None)
        self.pushButton_no.setEnabled(neg is not None)
        self.pushButton_no.setVisible(neg is not None)

        if pos == "Run Milling":
            self.pushButton_yes.setStyleSheet(stylesheets.GREEN_PUSHBUTTON_STYLE)
        else:
            self.pushButton_yes.setStyleSheet(stylesheets.BLUE_PUSHBUTTON_STYLE)

    def set_current_workflow_message(self, msg: Optional[str] = None, show: bool = True):
        """Set the current workflow information message"""
        if msg is not None:
            self.label_workflow_information.setText(msg)
        self.label_workflow_information.setVisible(show)

    def push_interaction_button(self):
        """Handle the user interaction with the workflow."""
        logging.debug("Sender: {}".format(self.sender().objectName()))

        # positve / negative response
        self.USER_RESPONSE = bool(self.sender() == self.pushButton_yes)
        self.WAITING_FOR_USER_INTERACTION = False

    def move_to_lamella_position(self):
        """Move the stage to the position of the selected lamella."""

        idx = self.comboBox_current_lamella.currentIndex()
        if idx == -1:
            return
        lamella: Lamella = self.experiment.positions[idx]
        stage_position = lamella.state.microscope_state.stage_position

        logging.info(f"Moving to position of {lamella.name}.")
        self.movement_widget.move_to_position(stage_position)

    def add_new_lamella(self, stage_position: Optional[FibsemStagePosition] = None) -> Lamella:
        """Add a lamella to the experiment.
        Args:
            pos: The stage position of the lamella. If None, the current stage position is used.
        Returns:
            lamella: The created lamella.
        """
        # get microscope state
        microscope_state = self.microscope.get_microscope_state()  
        if stage_position is not None: 
            microscope_state.stage_position = deepcopy(stage_position)

        # create the lamella
        state = LamellaState(stage=AutoLamellaStage.Created, microscope_state=microscope_state)
        lamella = create_new_lamella(experiment_path=self.experiment.path, 
                                     number=len(self.experiment.positions) + 1, 
                                     state=state, 
                                     protocol=self.settings.protocol["milling"])

        from autolamella.workflows.core import log_status_message
        log_status_message(lamella, "STARTED")
        self.experiment.positions.append(deepcopy(lamella))
        
        # if created from minimap, automatically mark as ready
        if stage_position is not None:

            # TODO: this is excessive, we need a cleaner way to do this

            from autolamella.workflows.core import (
                end_of_stage_update,
                start_of_stage_update,
            )
            self.experiment = end_of_stage_update(
                microscope=self.microscope,
                experiment=self.experiment,
                lamella=lamella,
                parent_ui=self,
                save_state=False,
                update_ui=False
            )

            # start ready stage
            self.experiment.positions[-1] = start_of_stage_update(
                microscope=self.microscope,
                lamella=lamella,
                next_stage=AutoLamellaStage.PositionReady,
                parent_ui=self,
                restore_state=False,
            )

            # end the stage
            self.experiment = end_of_stage_update(
                microscope=self.microscope,
                experiment=self.experiment,
                lamella=lamella,
                parent_ui=self,
                save_state=False,
                update_ui=False,
            )

        self.experiment.save()
        self.update_lamella_combobox(latest=True)
        self.update_ui()

        return lamella

    def remove_lamella_ui(self):
        idx = self.comboBox_current_lamella.currentIndex()
        self.experiment.positions.pop(idx)
        self.experiment.save()

        logging.info("Lamella removed from experiment")
        self.update_lamella_combobox()
        self.update_ui()

        self.sync_experiment_positions_to_minimap()  # update the minimap

        # clear milling widget if no lamella
        if self.experiment.positions == []:
            self.milling_widget.clear_all_milling_stages()
            remove_all_napari_shapes_layers(
                self.viewer, layer_type=napari.layers.points.points.Points
            )

    def fail_lamella_ui(self):
        idx = self.comboBox_current_lamella.currentIndex()
        if idx == -1:
            return

        # get the current state
        is_failure = self.experiment.positions[idx].is_failure
        name = self.experiment.positions[idx].name

        # if marking as failure, get user reason for failure
        if not is_failure:
            msg, ret = fui.open_text_input_dialog(
                msg="Enter failure reason:",
                title=f"Mark Lamella {name} as failure?",
                default="",
                parent=self,
            )

            if ret is False:
                logging.debug(f"User cancelled marking lamella {name} as failure.")
                return

            self.experiment.positions[idx].is_failure = True
            self.experiment.positions[idx].failure_note = msg
            self.experiment.positions[idx].failure_timestamp = datetime.timestamp(
                datetime.now()
            )
        else:
            self.experiment.positions[idx].is_failure = False
            self.experiment.positions[idx].failure_note = ""
            self.experiment.positions[idx].failure_timestamp = None

        self.experiment.save()
        self.update_ui()

    def revert_stage(self):
        idx = self.comboBox_current_lamella.currentIndex()
        hidx = self.comboBox_lamella_history.currentIndex()

        self.experiment.positions[idx].state = deepcopy(
            self.experiment.positions[idx].history[hidx]
        )
        self.experiment.positions[idx].state.start_timestamp = datetime.timestamp(
            datetime.now()
        )
        from autolamella.workflows.core import log_status_message

        log_status_message(self.experiment.positions[idx], "STARTED")
        # TODO: use start of stage update to restore the state properly

        self.update_ui()

    def save_lamella_ui(self):
        # triggered when save button is pressed

        if self.experiment.positions == []:
            return

        idx = self.comboBox_current_lamella.currentIndex()
        # TOGGLE BETWEEN READY AND SETUP

        method = self.settings.protocol["options"].get("method", None)

        lamella: Lamella = self.experiment.positions[idx]
        from autolamella.workflows.core import (
            end_of_stage_update,
            start_of_stage_update,
        )

        if lamella.workflow not in PREPARTION_WORKFLOW_STAGES:
            return

        # we need to be at the lamella position to save, check we are...
        # usually this is required when selected positions from minimap.
        # TODO: change how we do this, so that this is not required
        current_position = self.microscope.get_stage_position()

        if (
            not lamella.state.microscope_state.stage_position.is_close(
                current_position, 1e-6
            )
            and lamella.workflow is AutoLamellaStage.Created
        ):
            ret = fui.message_box_ui(
                title="Far away from lamella position",
                text="The current position is far away from the initial lamella position. Move to initial lamella position? (Press No to save at current position)",
            )

            # TODO: handle the case when user exits dialog box
            # TODO: only do this check if position created by minimap?

            if ret is True:
                # move to lamella position
                self.movement_widget.move_to_position(
                    lamella.state.microscope_state.stage_position
                )

        # end of stage update
        self.experiment = end_of_stage_update(
            microscope=self.microscope,
            experiment=self.experiment,
            lamella=lamella,
            parent_ui=self,
            save_state=True,
            update_ui=False
        )

        if lamella.workflow is AutoLamellaStage.Created:
            # start of stage update
            self.experiment.positions[idx] = start_of_stage_update(
                microscope=self.microscope,
                lamella=lamella,
                next_stage=AutoLamellaStage.PositionReady,
                parent_ui=self,
                restore_state=False,
            )

            # update the protocol / point
            self._update_milling_protocol(idx, method, AutoLamellaStage.PositionReady)

            # get current ib image, save as reference
            fname = os.path.join(
                self.experiment.positions[idx].path,
                f"ref_{self.experiment.positions[idx].state.stage.name}",
            )
            self.image_widget.ib_image.save(fname)
            self.milling_widget.CAN_MOVE_PATTERN = False

            self.experiment = end_of_stage_update(
                microscope=self.microscope,
                experiment=self.experiment,
                lamella=lamella,
                parent_ui=self,
                save_state=True,
                update_ui=False
            )

        elif lamella.workflow is AutoLamellaStage.PositionReady:
            self.experiment.positions[idx] = start_of_stage_update(
                self.microscope,
                lamella,
                AutoLamellaStage.Created,
                parent_ui=self,
                restore_state=False,
            )

            self.milling_widget.CAN_MOVE_PATTERN = True

        lamella.state.microscope_state.stage_position.name = lamella.petname

        self.sync_experiment_positions_to_minimap()
        self.update_lamella_combobox()
        self.update_ui()
        self.experiment.save()

    def _update_milling_protocol(
        self, idx: int, method: str, stage: AutoLamellaStage
    ):

        if stage not in PREPARTION_WORKFLOW_STAGES:
            return
        
        stages = deepcopy(self.milling_widget.get_milling_stages())
        
        # TRENCH SETUP
        if _is_method_type(method, "trench"):
            self.experiment.positions[idx].protocol[TRENCH_KEY] = get_protocol_from_stages(stages)
            return 

        # ON-GRID SETUP
        # TODO: allow the user to select the number of rough and polishing stages?, and re-assign?
        n_mill_rough = len(self.settings.protocol["milling"][MILL_ROUGH_KEY])
        n_mill_polishing = len(self.settings.protocol["milling"][MILL_POLISHING_KEY])

        # rough milling
        self.experiment.positions[idx].protocol[MILL_ROUGH_KEY] = get_protocol_from_stages(stages[:n_mill_rough])

        # polishing
        self.experiment.positions[idx].protocol[MILL_POLISHING_KEY] = get_protocol_from_stages(stages[n_mill_rough:n_mill_rough+n_mill_polishing])
        
        # total number of stages in lamella
        n_lamella = n_mill_rough + n_mill_polishing

        # stress relief features
        use_notch = self.settings.protocol["options"].get("use_notch", True)
        use_microexpansion = self.settings.protocol["options"].get(
            "use_microexpansion", True
        )

        if use_notch:
            self.experiment.positions[idx].protocol[NOTCH_KEY] = get_protocol_from_stages(stages[n_lamella])

        if use_microexpansion:
            self.experiment.positions[idx].protocol[MICROEXPANSION_KEY] = get_protocol_from_stages(stages[n_lamella + use_notch])

        # fiducial (optional)
        if self.settings.protocol["options"].get("use_fiducial", True):
            self.experiment.positions[idx].protocol[FIDUCIAL_KEY] = get_protocol_from_stages(stages[-1])

    def run_milling(self):
        self.MILLING_IS_RUNNING = True
        self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Milling"])
        self.milling_widget.run_milling()

    def handle_milling_update(self, ddict: dict) -> None:

        is_finished = ddict.get("finished", False)
        if is_finished:
            self.MILLING_IS_RUNNING = False

    def handle_acquisition_update(self, ddict: dict) -> None:
        if ddict.get("finished", False):
            self.update_lamella_ui()

    def handle_confirmed_detection_signal(self):
        # TODO: this seem very redundant if we just use the signal directly
        if self.det_widget is not None:
            self.det_widget.confirm_button_clicked()

    def _stop_workflow_thread(self):
        self.STOP_WORKFLOW = True
        napari.utils.notifications.show_error("Abort requested by user.")

    def _run_workflow(self, workflow: str) -> None:
        """Run the specified workflow."""
        try:
            self.milling_widget.milling_position_changed.disconnect()
        except Exception:
            pass

        self.worker = self._threaded_worker(
            microscope=self.microscope,
            settings=self.settings,
            experiment=self.experiment,
            workflow=workflow,
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.errored.connect(self._workflow_aborted)
        self.worker.start()

    def _workflow_aborted(self):
        """Handle the abortion of the workflow."""
        logging.info("Workflow aborted.")

        for lamella in self.experiment.positions:
            if lamella.workflow is not lamella.history[-1].stage:
                lamella.state = deepcopy(lamella.history[-1])
                logging.info("restoring state for {}".format(lamella.info))

        self._workflow_finished()

    def _workflow_finished(self):
        """Handle the completion of the workflow."""
        logging.info("Workflow finished.")
        self.WORKFLOW_IS_RUNNING = False
        self.milling_widget.milling_position_changed.connect(
            self._update_milling_position
        )
        self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Experiment"])
        self.pushButton_stop_workflow.setVisible(False)

        # clear the image settings save settings etc
        self.image_widget.checkBox_image_save_image.setChecked(False)
        self.image_widget.lineEdit_image_path.setText(self.experiment.path)
        self.image_widget.lineEdit_image_label.setText("default-image")
        self.update_ui()

        # optionally turn off the beams when finished
        turn_off_beams = self.settings.protocol["options"].get("turn_off_beams", False)
        if turn_off_beams:
            self.microscope.turn_off(BeamType.ELECTRON)
            self.microscope.turn_off(BeamType.ION)

        # set electron image as active layer
        self.image_widget.restore_active_layer_for_movement()

        self.set_current_workflow_message(msg=None, show=False)

    def handle_workflow_update(self, info: dict) -> None:
        """Update the UI with the given information, ready for user interaction"""

        # update the image viewer
        sem_image = info.get("sem_image", None)
        if sem_image is not None:
            self.image_widget.eb_image = sem_image
            self.image_widget.update_viewer(arr=sem_image.data, 
                                            beam_type=BeamType.ELECTRON, 
                                            set_ui_from_image=True)
        
        fib_image = info.get("fib_image", None)
        if fib_image is not None:
            self.image_widget.ib_image = fib_image
            self.image_widget.update_viewer(arr=fib_image.data, 
                                            beam_type=BeamType.ION, 
                                            set_ui_from_image=True)

        # what?
        enable_milling = info.get("milling_enabled", None)
        if enable_milling is not None:
            self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Milling"])

        # update milling stages
        milling_stages = info.get("stages", None)
        if isinstance(milling_stages, list):
            self.milling_widget.set_milling_stages(milling_stages)
        if milling_stages == "clear":
            self.milling_widget.clear_all_milling_stages()
        detections = info.get("det", None)
        if self.det_widget is not None and detections is not None:
            self.det_widget.set_detected_features(detections)
            self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Detection"])

        # update the alignment area
        alignment_area = info.get("alignment_area", None)
        if isinstance(alignment_area, FibsemRectangle):
            self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Image"])
            self.image_widget.toggle_alignment_area(alignment_area)
        if alignment_area == "clear":
            self.image_widget.clear_alignment_area()
        
        # no specific interaction, just update the ui
        if detections is None and enable_milling is None and alignment_area is None:
            self.tabWidget.setCurrentIndex(CONFIGURATION["TABS"]["Experiment"])

        # ui interaction
        self.milling_widget.pushButton_run_milling.setEnabled(False)
        self.milling_widget.pushButton_run_milling.setVisible(False) # TODO: re-enable??

        # instruction message
        self.set_instructions_msg(info["msg"], info.get("pos", None), info.get("neg", None))
        self.set_current_workflow_message(info.get("workflow_info", None))

        self.WAITING_FOR_UI_UPDATE = False

    def hande_update_experiment_signal(self, experiment: Experiment):
        """Callback for updating the experiment object."""
        self.experiment = experiment
        self.update_lamella_combobox()
        self.update_ui()

    @thread_worker
    def _threaded_worker(
        self,
        microscope: FibsemMicroscope,
        settings: MicroscopeSettings,
        experiment: Experiment,
        workflow: str = "trench",
    ):
        self.STOP_WORKFLOW = False
        self.WORKFLOW_IS_RUNNING = True
        self.milling_widget.CAN_MOVE_PATTERN = True
        self.milling_widget.clear_all_milling_stages()
        self.WAITING_FOR_USER_INTERACTION = False
        remove_all_napari_shapes_layers(
            self.viewer, layer_type=napari.layers.points.points.Points
        )
        self.pushButton_run_waffle_trench.setEnabled(False)
        self.pushButton_run_waffle_undercut.setEnabled(False)
        self.pushButton_run_setup_autolamella.setEnabled(False)
        self.pushButton_run_waffle_trench.setStyleSheet(
            stylesheets.DISABLED_PUSHBUTTON_STYLE
        )
        self.pushButton_run_waffle_undercut.setStyleSheet(
            stylesheets.DISABLED_PUSHBUTTON_STYLE
        )
        self.pushButton_run_setup_autolamella.setStyleSheet(
            stylesheets.DISABLED_PUSHBUTTON_STYLE
        )
        self.pushButton_stop_workflow.setVisible(True)
        self.set_instructions_msg(f"Running {workflow.title()} workflow...")
        method = settings.protocol["options"].get("method", None)
        method = get_autolamella_method(method)

        # turn on the beams, if not already on
        if not self.microscope.get("on", BeamType.ELECTRON):
            self.microscope.turn_on(BeamType.ELECTRON)
        if not self.microscope.get("on", BeamType.ION):
            self.microscope.turn_on(BeamType.ION)

        logging.info(f"Started {workflow.title()} Workflow...")
        # TODO: everything above here should happen outside the thread

        from autolamella.workflows import runners as wfl  # avoiding circular import
        if method in [AutoLamellaMethod.LIFTOUT, AutoLamellaMethod.SERIAL_LIFTOUT]:
            from autolamella.workflows import autoliftout

        if workflow == "trench":
            wfl.run_trench_milling(microscope, settings, experiment, parent_ui=self)

        if workflow == "undercut":
            wfl.run_undercut_milling(microscope, settings, experiment, parent_ui=self)

        if workflow == "autolamella":

            if method in wfl.METHOD_WORKFLOWS_FN:
                wfl.METHOD_WORKFLOWS_FN[method](microscope, settings, experiment, parent_ui=self)
            
            if method is AutoLamellaMethod.SERIAL_LIFTOUT:
                autoliftout.run_thinning_workflow(
                    microscope=microscope,
                    settings=settings,
                    experiment=experiment,
                    parent_ui=self,
                )

        # liftout workflows
        # from autolamella.workflows import autoliftout

        if workflow == "setup-liftout":
            self.experiment = autoliftout.run_setup_autoliftout(
                microscope=microscope,
                settings=settings,
                experiment=experiment,
                parent_ui=self,
            )
        if workflow == "autoliftout":
            if method is AutoLamellaMethod.LIFTOUT:
                settings.image.autogamma = True
                self.experiment = autoliftout.run_autoliftout_workflow(
                    microscope=microscope,
                    settings=settings,
                    experiment=experiment,
                    parent_ui=self,
                )
            if method is AutoLamellaMethod.SERIAL_LIFTOUT:
                from autolamella.workflows import serial as serial_workflow

                self.experiment = serial_workflow.run_serial_liftout_workflow(
                    microscope=microscope,
                    settings=settings,
                    experiment=experiment,
                    parent_ui=self,
                )
        if workflow == "serial-liftout-landing":
            from autolamella.workflows import serial as serial_workflow

            self.experiment = serial_workflow.run_serial_liftout_landing(
                microscope=microscope,
                settings=settings,
                experiment=experiment,
                parent_ui=self,
            )

        self.update_experiment_signal.emit(self.experiment)

def main():
    autolamella_ui = AutoLamellaUI(viewer=napari.Viewer())
    autolamella_ui.viewer.window.add_dock_widget(
        widget=autolamella_ui,
        area="right",
        add_vertical_stretch=True,
        name=f"AutoLamella v{autolamella.__version__}",
    )
    napari.run()

if __name__ == "__main__":
    main()
