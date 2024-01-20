import logging
import os
from copy import deepcopy
from pprint import pprint
from collections import Counter
import napari
from fibsem import utils as futils
from fibsem.microscope import FibsemMicroscope
from fibsem.structures import MicroscopeSettings
from fibsem.ui import utils as fui
from fibsem.ui.FibsemEmbeddedDetectionWidget import FibsemEmbeddedDetectionUI
from fibsem.ui.FibsemImageSettingsWidget import FibsemImageSettingsWidget
from fibsem.ui.FibsemManipulatorWidget import FibsemManipulatorWidget
from fibsem.ui.FibsemMillingWidget import FibsemMillingWidget
from fibsem.ui.FibsemMovementWidget import FibsemMovementWidget
from fibsem.ui.FibsemSystemSetupWidget import FibsemSystemSetupWidget
from fibsem.ui.FibsemCryoDepositionWidget import FibsemCryoDepositionWidget
from napari.qt.threading import thread_worker
from napari.utils import notifications
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal

import autolamella
from autolamella import config as cfg
from autolamella.structures import AutoLamellaWaffleStage, Experiment, Lamella
from autolamella.ui import utils as ui_utils
from autolamella.ui.qt import AutoLiftoutUIv2

from datetime import datetime
from fibsem.ui import _stylesheets

_DEV_MODE = False
DEV_MICROSCOPE = "Demo"
DEV_EXP_PATH = r"C:\Users\pcle0002\Documents\repos\autoliftout\liftout\log\DEV-TEST-SERIAL-01\experiment.yaml"
DEV_PROTOCOL_PATH = os.path.join(cfg.BASE_PATH, "protocol", "protocol_serial.yaml")


class AutoLiftoutUIv2(AutoLiftoutUIv2.Ui_MainWindow, QtWidgets.QMainWindow):

    ui_signal = pyqtSignal(dict)
    det_confirm_signal = pyqtSignal(bool)
    update_experiment_signal = pyqtSignal(Experiment)
    _run_milling_signal = pyqtSignal()
    
    def __init__(self, viewer: napari.Viewer = None):
        super(AutoLiftoutUIv2, self).__init__()

        # setup ui
        self.setupUi(self)

        self.viewer = viewer
        self.viewer.window._qt_viewer.dockLayerList.setVisible(False)
        self.viewer.window._qt_viewer.dockLayerControls.setVisible(False)

        self._PROTOCOL_LOADED = False
        self._microscope_ui_loaded = False

        self.experiment: Experiment = None
        self.worker = None
        self.microscope: FibsemMicroscope = None
        self.settings: MicroscopeSettings = None

        self.system_widget = FibsemSystemSetupWidget(
            microscope=self.microscope,
            settings=self.settings,
            viewer=self.viewer,
            config_path=cfg.SYSTEM_PATH,
        )
        self.tabWidget.addTab(self.system_widget, "Connection")

        self.image_widget: FibsemImageSettingsWidget = None
        self.movement_widget: FibsemMovementWidget = None
        self.milling_widget: FibsemMillingWidget = None
        self.manipulator_widget: FibsemManipulatorWidget = None

        self.WAITING_FOR_USER_INTERACTION: bool = False
        self.USER_RESPONSE: bool = False
        self.WAITING_FOR_UI_UPDATE: bool = False
        self._WORKFLOW_RUNNING: bool = False
        self._ABORT_THREAD: bool = False

        # setup connections
        self.setup_connections()

        self.update_ui()

        if _DEV_MODE:
            self._auto_load()

    def setup_connections(self):
        # system widget
        self.system_widget.connected_signal.connect(self.connect_to_microscope)
        self.system_widget.disconnected_signal.connect(self.disconnect_from_microscope)

        # file menu
        self.actionNew_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Protocol.triggered.connect(self.load_protocol)
        self.actionSave_Protocol.triggered.connect(self.update_protocol_from_ui)
        self.actionCryo_Deposition.triggered.connect(self.cryo_deposition)
        self.actionCalibrate_Manipulator.triggered.connect(lambda: self._run_workflow(workflow="calibrate-manipulator"))
        self.actionPrepare_Manipulator.triggered.connect(lambda: self._run_workflow(workflow="prepare-manipulator"))

        # protocol
        self.pushButton_update_protocol.clicked.connect(self.update_protocol_from_ui)
        self.comboBox_protocol_method.addItems(cfg.__AUTOLIFTOUT_METHODS__)
        self.comboBox_options_liftout_joining_method.addItems(cfg.__AUTOLIFTOUT_LIFTOUT_JOIN_METHODS__)
        self.comboBox_options_landing_joining_method.addItems(cfg.__AUTOLIFTOUT_LANDING_JOIN_METHODS__)

        _AVAILABLE_POSITIONS_ = futils._get_positions()
        self.comboBox_options_lamella_start_position.addItems(_AVAILABLE_POSITIONS_)
        self.comboBox_options_landing_start_position.addItems(_AVAILABLE_POSITIONS_)

        # workflow buttons
        self.pushButton_setup_autoliftout.clicked.connect(lambda: self._run_workflow(workflow="setup"))
        self.pushButton_run_autoliftout.clicked.connect(lambda: self._run_workflow(workflow="autoliftout"))
        self.pushButton_run_serial_liftout_landing.clicked.connect(lambda: self._run_workflow(workflow="serial-liftout-landing"))
        self.pushButton_run_polishing.clicked.connect(lambda: self._run_workflow(workflow="autolamella"))

        # interaction buttons
        self.pushButton_yes.clicked.connect(self.push_interaction_button)
        self.pushButton_no.clicked.connect(self.push_interaction_button)

        # signals
        self.det_confirm_signal.connect(self._confirm_det)
        self.update_experiment_signal.connect(self._update_experiment)
        self.ui_signal.connect(self._ui_signal)
        self._run_milling_signal.connect(self._run_milling)

        # ui
        self.comboBox_current_lamella.currentIndexChanged.connect(self._update_lamella_ui)
        self.checkBox_current_lamella_landing_selected.stateChanged.connect(self._update_lamella_info)
        self.checkBox_current_lamella_failure.stateChanged.connect(self._update_lamella_info)
        self.pushButton_revert_stage.clicked.connect(self.revert_stage)

    # TODO: move this to system wideget??
    def connect_to_microscope(self):
        self.microscope = self.system_widget.microscope
        self.settings = self.system_widget.settings
        self.update_microscope_ui()
        self.update_ui()

    def disconnect_from_microscope(self):
        self.microscope = None
        self.settings = None
        self.update_microscope_ui()
        self.update_ui()

    def update_ui(self):
        """Update the ui based on the current state of the application."""

        _experiment_loaded = bool(self.experiment is not None)
        _microscope_connected = bool(self.microscope is not None)
        _protocol_loaded = bool(self.settings is not None) and self._PROTOCOL_LOADED
        _LAMELLA_SELECTED = bool(self.experiment.positions) if _experiment_loaded else False
        _LAMELLA_SETUP,_LAMELLA_TRENCH, _LAMELLA_UNDERCUT, _LIFTOUT_FINISHED, _LAMELLA_LANDED = False, False, False, False, False  # ready for stages
        _AUTOLAMELLA_PROGRESS = False
        if self.experiment is not None:
            _counter = Counter([p.state.stage.name for p in self.experiment.positions])
            _LAMELLA_SETUP = _counter[AutoLamellaWaffleStage.ReadyTrench.name] > 0
            _LAMELLA_TRENCH = _counter[AutoLamellaWaffleStage.MillTrench.name] > 0
            _LAMELLA_UNDERCUT = _counter[AutoLamellaWaffleStage.MillUndercut.name] > 0
            _LIFTOUT_FINISHED = _counter[AutoLamellaWaffleStage.LiftoutLamella.name] > 0
            _LAMELLA_LANDED = _counter[AutoLamellaWaffleStage.LandLamella.name] > 0
            _AUTOLAMELLA_PROGRESS = (_counter[AutoLamellaWaffleStage.SetupLamella.name]>0
                or _counter[AutoLamellaWaffleStage.MillRoughCut.name] > 0 
                or _counter[AutoLamellaWaffleStage.MillPolishingCut.name] > 0)

        # setup experiment -> connect to microscope -> select lamella -> run autoliftout -> run polishing

        # METHOD 
        _METHOD = self.settings.protocol.get("method", "autoliftout-default") if _protocol_loaded else "autoliftout-default"

        # experiment loaded
        self.actionConnect_Microscope.setVisible(_experiment_loaded)
        self.actionLoad_Protocol.setVisible(_experiment_loaded)
        self.actionSave_Protocol.setVisible(_protocol_loaded)
        self.actionCryo_Deposition.setVisible(_protocol_loaded)
        self.actionCalibrate_Manipulator.setVisible(_protocol_loaded)
        self.actionPrepare_Manipulator.setVisible(_protocol_loaded)

        # workflow buttons
        _SETUP_ENABLED = _microscope_connected and _protocol_loaded
        _AUTOLIFTOUT_ENABLED = (_LAMELLA_SETUP or _LAMELLA_TRENCH or _LAMELLA_UNDERCUT or (_LIFTOUT_FINISHED and _METHOD=="autoliftout-default")) and _microscope_connected and _protocol_loaded
        _SERIAL_LIFTOUT_LANDING_ENABLED = _LIFTOUT_FINISHED and _microscope_connected and _protocol_loaded
        _AUTOLAMELLA_ENABLED = (_LAMELLA_LANDED or _AUTOLAMELLA_PROGRESS) and _microscope_connected and _protocol_loaded

        self.pushButton_setup_autoliftout.setEnabled(_SETUP_ENABLED)
        self.pushButton_run_autoliftout.setEnabled(_AUTOLIFTOUT_ENABLED)
        self.pushButton_run_serial_liftout_landing.setEnabled(_SERIAL_LIFTOUT_LANDING_ENABLED)
        self.pushButton_run_serial_liftout_landing.setVisible(_METHOD=="autoliftout-serial-liftout")
        self.pushButton_run_polishing.setEnabled(_AUTOLAMELLA_ENABLED)

        # set stylesheets
        self.pushButton_setup_autoliftout.setStyleSheet(_stylesheets._GREEN_PUSHBUTTON_STYLE if _SETUP_ENABLED  else _stylesheets._DISABLED_PUSHBUTTON_STYLE)
        self.pushButton_run_autoliftout.setStyleSheet(_stylesheets._GREEN_PUSHBUTTON_STYLE if _AUTOLIFTOUT_ENABLED else _stylesheets._DISABLED_PUSHBUTTON_STYLE)
        self.pushButton_run_serial_liftout_landing.setStyleSheet(_stylesheets._GREEN_PUSHBUTTON_STYLE if _SERIAL_LIFTOUT_LANDING_ENABLED else _stylesheets._DISABLED_PUSHBUTTON_STYLE)
        self.pushButton_run_polishing.setStyleSheet(_stylesheets._GREEN_PUSHBUTTON_STYLE if _AUTOLAMELLA_ENABLED else _stylesheets._DISABLED_PUSHBUTTON_STYLE)


        # labels
        if _experiment_loaded:
            self.label_experiment_name.setText(f"Experiment: {self.experiment.name}")

            msg = "\nLamella Info:\n"
            for lamella in self.experiment.positions:
                failure_msg = f" (Failure)" if lamella._is_failure else f" (Active)"
                msg += f"Lamella {lamella._petname} \t\t {lamella.state.stage.name} \t{failure_msg} \n"
            self.label_info.setText(msg)

            # detail combobox
            self.comboBox_current_lamella.clear()
            self.comboBox_current_lamella.addItems([lamella.info for lamella in self.experiment.positions])

        # lamella details
        self.comboBox_current_lamella.setVisible(_LAMELLA_SELECTED)
        self.label_current_lamella.setVisible(_LAMELLA_SELECTED)
        self.label_lamella_detail.setVisible(_LAMELLA_SELECTED)
        self.checkBox_current_lamella_landing_selected.setVisible(_LAMELLA_SELECTED)
        self.checkBox_current_lamella_failure.setVisible(_LAMELLA_SELECTED)
        self.comboBox_lamella_history.setVisible(_LAMELLA_SELECTED)
        self.pushButton_revert_stage.setVisible(_LAMELLA_SELECTED)



        if _protocol_loaded:
            self.label_protocol_name.setText(
                f"Protocol: {self.settings.protocol.get('name', 'protocol')}"
            )


        # instructions
        INSTRUCTIONS = {"NOT_CONNECTED": "Please connect to the microscope.",
                        "NO_EXPERIMENT": "Please create or load an experiment.",
                        "NO_PROTOCOL": "Please load a protocol.",
                        "NO_LAMELLA": "Please Run Setup to select Lamella Positions.",
                        "LAMELLA_READY": "Lamella Positions Selected. Ready to Run Autoliftout.",
                        "POLISHING_READY": "Autoliftout Complete. Ready to Run AutoLamella.",
                        }

        if not _microscope_connected:
            self._set_instructions(INSTRUCTIONS["NOT_CONNECTED"])
        elif not _experiment_loaded:
            self._set_instructions(INSTRUCTIONS["NO_EXPERIMENT"])
        elif not _protocol_loaded:
            self._set_instructions(INSTRUCTIONS["NO_PROTOCOL"])
        elif not _LAMELLA_SELECTED:
            self._set_instructions(INSTRUCTIONS["NO_LAMELLA"])
        elif _LAMELLA_SELECTED and _LAMELLA_LANDED:
            self._set_instructions(INSTRUCTIONS["POLISHING_READY"])
        elif _LAMELLA_SELECTED:

            self._set_instructions(INSTRUCTIONS["LAMELLA_READY"])
    
    def _update_lamella_ui(self):

        if self.experiment is None :
            return
        
        if self.experiment.positions == []:
            return

        lamella = self.experiment.positions[self.comboBox_current_lamella.currentIndex()]
        
        msg = ""
        msg += f"{lamella.info}"
        msg += f" (Failure)" if lamella._is_failure else f" (Active)"
        self.label_lamella_detail.setText(msg)
        self.checkBox_current_lamella_landing_selected.setChecked(lamella.landing_selected)
        self.checkBox_current_lamella_failure.setChecked(lamella._is_failure)

        def _to_str(state):
            return f"{state.stage.name} ({datetime.fromtimestamp(state.end_timestamp).strftime('%I:%M%p')})"
        
        self.comboBox_lamella_history.clear()
        _lamella_history = bool(lamella.history)
        self.comboBox_lamella_history.setVisible(_lamella_history)
        self.pushButton_revert_stage.setVisible(_lamella_history)
        self.comboBox_lamella_history.addItems([_to_str(state) for state in lamella.history])
    
    def _update_lamella_info(self):

        # TODO: add a failure note here
        lamella = self.experiment.positions[self.comboBox_current_lamella.currentIndex()]
        lamella.landing_selected = self.checkBox_current_lamella_landing_selected.isChecked()
        lamella._is_failure = self.checkBox_current_lamella_failure.isChecked()

        self.experiment.save()
        self._update_lamella_ui()

    def revert_stage(self):
        '''time travel'''
        idx = self.comboBox_current_lamella.currentIndex()
        hidx = self.comboBox_lamella_history.currentIndex()
        self.experiment.positions[idx].state = deepcopy(self.experiment.positions[idx].history[hidx])
        self.experiment.save()
        self.update_ui()

    def update_microscope_ui(self):
        """Update the ui based on the current state of the microscope."""

        if self.microscope is not None and not self._microscope_ui_loaded:
            # reusable components
            self.image_widget = FibsemImageSettingsWidget(
                microscope=self.microscope,
                image_settings=self.settings.image,
                viewer=self.viewer,
                parent=self,

            )
            self.movement_widget = FibsemMovementWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                image_widget=self.image_widget,
                parent=self,

            )
            self.milling_widget = FibsemMillingWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                image_widget=self.image_widget,
                parent=self,

            )

            self.manipulator_widget = FibsemManipulatorWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                image_widget=self.image_widget,
                parent=self,

            )

            self.det_widget = FibsemEmbeddedDetectionUI(
                viewer=self.viewer, 
                model=None,
                parent=self,

                )

            # add widgets to tabs
            self.tabWidget.addTab(self.image_widget, "Image")
            self.tabWidget.addTab(self.movement_widget, "Movement")
            self.tabWidget.addTab(self.milling_widget, "Milling")
            self.tabWidget.addTab(self.manipulator_widget, "Manipulator")
            self.tabWidget.addTab(self.det_widget, "Detection")

            self.milling_widget._milling_finished.connect(self._milling_finished)

            self._microscope_ui_loaded = True
        else:
            if self.image_widget is None:
                return

            # remove tabs
            self.tabWidget.removeTab(7)
            self.tabWidget.removeTab(6)
            self.tabWidget.removeTab(5)
            self.tabWidget.removeTab(4)
            self.tabWidget.removeTab(3)


            self.image_widget.clear_viewer()
            self.image_widget.deleteLater()
            self.movement_widget.deleteLater()
            self.milling_widget.deleteLater()
            self.det_widget.deleteLater()
            self.manipulator_widget.deleteLater()

            self._microscope_ui_loaded = False

    def update_ui_from_protocol(self, protocol: dict):

        self.settings.protocol = protocol

        # meta
        self.lineEdit_protocol_name.setText(self.settings.protocol.get("name", "autoliftout"))
        self.comboBox_protocol_method.setCurrentText(self.settings.protocol.get("method", "autoliftout-default"))

        
        # options
        options = self.settings.protocol["options"]
        self.checkBox_options_batch_mode.setChecked(bool(options["batch_mode"]))
        self.checkBox_options_confirm_next_stage.setChecked(bool(options["confirm_next_stage"]))
        self.comboBox_options_liftout_joining_method.setCurrentText(options.get("liftout_joining_method", "None"))
        self.comboBox_options_landing_joining_method.setCurrentText(options.get("landing_joining_method", "Weld"))

        self.comboBox_options_lamella_start_position.setCurrentText(options["lamella_start_position"])
        self.comboBox_options_landing_start_position.setCurrentText(options["landing_start_position"])

        # supervision
        self.checkBox_supervise_mill_trench.setChecked(bool(options["supervise"]["trench"]))
        self.checkBox_supervise_mill_undercut.setChecked(bool(options["supervise"]["undercut"]))
        self.checkBox_supervise_liftout.setChecked(bool(options["supervise"]["liftout"]))
        self.checkBox_supervise_landing.setChecked(bool(options["supervise"]["landing"]))
        self.checkBox_supervise_setup_lamella.setChecked(bool(options["supervise"]["setup_lamella"]))
        self.checkBox_supervise_mill_rough.setChecked(bool(options["supervise"]["mill_rough"]))
        self.checkBox_supervise_mill_polishing.setChecked(bool(options["supervise"]["mill_polishing"]))

        # ml
        self.lineEdit_protocol_ml_checkpoint.setText(self.settings.protocol["ml"]["checkpoint"])

        # TODO: initial positions


    def update_protocol_from_ui(self):

        self.settings.protocol["name"] = self.lineEdit_protocol_name.text()
        self.settings.protocol["method"] = self.comboBox_protocol_method.currentText()

        # TODO: fix this for both methods
        self.settings.protocol["options"].update({
            "batch_mode": self.checkBox_options_batch_mode.isChecked(),
            "confirm_next_stage": self.checkBox_options_confirm_next_stage.isChecked(),
            "liftout_joining_method": self.comboBox_options_liftout_joining_method.currentText(),
            "landing_joining_method": self.comboBox_options_landing_joining_method.currentText(),
            "lamella_start_position": self.comboBox_options_lamella_start_position.currentText(),
            "landing_start_position": self.comboBox_options_landing_start_position.currentText(),
            "supervise": {
                "trench": self.checkBox_supervise_mill_trench.isChecked(),
                "undercut": self.checkBox_supervise_mill_undercut.isChecked(),
                "liftout": self.checkBox_supervise_liftout.isChecked(),
                "landing": self.checkBox_supervise_landing.isChecked(),
                "setup_lamella": self.checkBox_supervise_setup_lamella.isChecked(),
                "mill_rough": self.checkBox_supervise_mill_rough.isChecked(),
                "mill_polishing": self.checkBox_supervise_mill_polishing.isChecked()
            }}
        )

        self.settings.protocol["ml"] = {
            "checkpoint": self.lineEdit_protocol_ml_checkpoint.text(),
        }

        if self.sender() == self.actionSave_Protocol:

            # convert exp.settings to dict, save to yaml
            PATH = fui._get_save_file_ui(
                msg="Select a protocol file", path=cfg.PROTOCOL_PATH, parent=self
            )

            if PATH == "":
                logging.info("No path selected")
                return

            futils.save_yaml(path=PATH, data=self.settings.protocol)
            napari.utils.notifications.show_info(
                f"Saved Protocol to {os.path.basename(PATH)}"

            )
        else:
            napari.utils.notifications.show_info("Updated Protocol")

        # save a copy of the protocol to the experiment.path
        if self.experiment:
            futils.save_yaml(os.path.join(self.experiment.path, "protocol.yaml"), self.settings.protocol)


    def _auto_load(self):

        # connect to microscope
        self.system_widget.connect_to_microscope()

        # load experiment
        self.experiment = Experiment.load(DEV_EXP_PATH)

        # load protocol
        self.settings.protocol = futils.load_protocol(protocol_path=DEV_PROTOCOL_PATH)
        self.update_ui_from_protocol(self.settings.protocol)
        self._PROTOCOL_LOADED = True

        self.update_ui()
        return 

    def setup_experiment(self) -> None:
        new_experiment = bool(self.sender() is self.actionNew_Experiment)
        experiment = ui_utils.setup_experiment_ui_v2(
            self, new_experiment=new_experiment
        )

        if experiment is None:
            napari.utils.notifications.show_info(f"Experiment not loaded.")
            return

        self.experiment = experiment
        napari.utils.notifications.show_info(
            f"Experiment {self.experiment.name} loaded."
        )

        # TODO: enable this
        # register metadata
        if cfg._REGISTER_METADATA:
             #NB: microscope needs to be connected beforehand
            futils._register_metadata(
                microscope=self.microscope, 
                application_software="autolamella",
                application_software_version=autolamella.__version__,
                experiment_name=self.experiment.name,
                experiment_method = "autoliftout") # TODO: add method to experiment

        # # automatically re-load protocol if available
        if not new_experiment and self.settings is not None:
            # try to load protocol from file
            PROTOCOL_PATH = os.path.join(self.experiment.path, "protocol.yaml")
            if os.path.exists(PROTOCOL_PATH):
                self.settings.protocol = futils.load_protocol(protocol_path=PROTOCOL_PATH)
                self._PROTOCOL_LOADED = True
                self.update_ui_from_protocol(self.settings.protocol)


        self.update_ui()

    def load_protocol(self):
        """Load a protocol from file."""

        if self.settings is None:
            napari.utils.notifications.show_info(
                f"Please connect to the microscope first."
            )
            return

        PATH = fui._get_file_ui(
            msg="Select a protocol file", path=cfg.PROTOCOL_PATH, parent=self
        )

        if PATH == "":
            napari.utils.notifications.show_info(f"No path selected")
            logging.info("No path selected")
            return

        self.settings.protocol = futils.load_protocol(protocol_path=PATH)
        self.update_ui_from_protocol(self.settings.protocol)
        self._PROTOCOL_LOADED = True
        napari.utils.notifications.show_info(
            f"Loaded Protocol from {os.path.basename(PATH)}"
        )

        # save a copy of the protocol to the experiment.path
        if self.experiment:
            futils.save_yaml(os.path.join(self.experiment.path, "protocol.yaml"), self.settings.protocol)

        self.update_ui()

    def save_protocol(self):
        logging.info(f"SAVE | PROTOCOL | STARTED")

        # convert exp.settings to dict, save to yaml
        PATH = fui._get_save_file_ui(
            msg="Select a protocol file", path=cfg.PROTOCOL_PATH, parent=self
        )

        if PATH == "":
            logging.info("No path selected")
            return

        futils.save_yaml(path=PATH, data=self.settings.protocol)
        napari.utils.notifications.show_info(
            f"Saved Protocol to {os.path.basename(PATH)}"
        )
    
    def cryo_deposition(self):

        cryo_deposition_widget = FibsemCryoDepositionWidget(self.microscope, self.settings)
        cryo_deposition_widget.exec_()


    def closeEvent(self, event):
        """Close the microscope connection on window close."""
        logging.info("CLOSE | WINDOW | STARTED")

        if self.worker:
            if self.worker.is_running:
                self.worker.stop()

        if self.microscope:
            self.microscope.disconnect()

        event.accept()
    ########################## AUTOLIFTOUT ##########################
    
    def _set_instructions(
        self, msg: str = "", pos: str = None, neg: str = None,
    ):

        self.label_instructions.setText(msg)
        self.pushButton_yes.setText(pos)
        self.pushButton_no.setText(neg)
        
        # enable buttons
        self.pushButton_yes.setEnabled(pos is not None)
        self.pushButton_no.setEnabled(neg is not None)
        self.pushButton_yes.setVisible(pos is not None)
        self.pushButton_no.setVisible(neg is not None)

    def push_interaction_button(self):
        logging.info("Sender: {}".format(self.sender().objectName()))

        # positve / negative response
        self.USER_RESPONSE = bool(self.sender() == self.pushButton_yes)
        self.WAITING_FOR_USER_INTERACTION = False
    
    def _run_milling(self):
        self._MILLING_RUNNING = True
        self.milling_widget.run_milling()

    def _milling_finished(self):
        self._MILLING_RUNNING = False
    
    # TODO: just make this a signal??
    def _confirm_det(self):
        if self.det_widget is not None:
            self.det_widget.confirm_button_clicked()

    def _run_workflow(self, workflow: str):
        self.worker = self._threaded_worker(
            microscope=self.microscope, settings=self.settings, experiment=self.experiment, workflow=workflow,
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.start()

    def _workflow_finished(self):
        logging.info(f"Workflow Finished.")
        self._WORKFLOW_RUNNING = False
        self.tabWidget.setCurrentIndex(0)
        napari.utils.notifications.show_info(f"Workflow Finished.")

    def _ui_signal(self, info:dict) -> None:
        """Update the UI with the given information, ready for user interaction"""
        
        _mill = bool(info["mill"] is not None) if info["mill"] is None else info["mill"]
        _det = bool(info["det"] is not None)
        stages = info.get("stages", None)

        if _det:
            self.det_widget.set_detected_features(info["det"])
            self.tabWidget.setCurrentIndex(7)
        
        if _mill:
            self.tabWidget.setCurrentIndex(5)

        if info["eb_image"] is not None:
            eb_image = info["eb_image"]
            self.image_widget.eb_image = eb_image
            self.image_widget.update_viewer(eb_image.data, "ELECTRON", _set_ui=True)
        if info["ib_image"] is not None:
            ib_image = info["ib_image"]
            self.image_widget.ib_image = ib_image
            self.image_widget.update_viewer(ib_image.data, "ION", _set_ui=True)


        if isinstance(stages, list):
            self.milling_widget.set_milling_stages(stages)
        if stages == "clear":
            self.milling_widget._remove_all_stages()

        # ui interaction
        self.milling_widget.pushButton_run_milling.setEnabled(_mill)
        self.milling_widget.pushButton_run_milling.setVisible(_mill)

        # instruction message
        self._set_instructions(info["msg"], info["pos"], info["neg"])

        self.WAITING_FOR_UI_UPDATE = False

    def _update_experiment(self, experiment: Experiment):
        self.experiment = experiment
        self.update_ui()

    @thread_worker
    def _threaded_worker(self, microscope, settings, experiment, workflow="setup"):
        
        self._WORKFLOW_RUNNING = True
        self.milling_widget._remove_all_stages()
        self.WAITING_FOR_USER_INTERACTION = False
        self._set_instructions(f"Running {workflow.title()} workflow...", None, None)
        logging.info(f"RUNNING {workflow.upper()} WORKFLOW")

        from autolamella.workflows import autoliftout

        if workflow == "setup":
            self.experiment = autoliftout.run_setup_autoliftout(
                microscope=microscope,
                settings=settings,
                experiment=experiment,
                parent_ui=self,
            )
        elif workflow == "autoliftout":

            _METHOD = self.settings.protocol.get("method", "autoliftout-default")
            
            if _METHOD == "autoliftout-default":
                settings.image.autogamma = True
                self.experiment = autoliftout.run_autoliftout_workflow(
                    microscope=microscope,
                    settings=settings,
                    experiment=experiment,
                    parent_ui=self,
                )
            if _METHOD == "autoliftout-serial-liftout":
                from autolamella.workflows import serial as serial_workflow
                self.experiment = serial_workflow.run_serial_liftout_workflow(
                    microscope=microscope,
                    settings=settings,
                    experiment=experiment,
                    parent_ui=self,
                )
        elif workflow == "serial-liftout-landing":

            from autolamella.workflows import serial as serial_workflow
            self.experiment = serial_workflow.run_serial_liftout_landing(

                microscope=microscope,
                settings=settings,
                experiment=experiment,
                parent_ui=self,
            )
        elif workflow == "autolamella":

            self.experiment = autoliftout.run_thinning_workflow(
                microscope=microscope,
                settings=settings,
                experiment=experiment,
                parent_ui=self,
            )
        elif workflow == "calibrate-manipulator":
            from fibsem import calibration
            calibration._calibrate_manipulator_thermo(microscope = microscope, settings = settings, parent_ui = self)

            napari.utils.notification.show_info(f"Calibrated Manipulator")

        elif workflow == "prepare-manipulator":

            _METHOD = self.settings.protocol.get("method", "autoliftout-default")
            if _METHOD == "autoliftout-serial-liftout":
                autoliftout.PREPARE_MANIPULATOR_WORKFLOW["serial-liftout"](microscope=microscope, 
                                                                  settings= settings, 
                                                                  parent_ui=self,
                                                                  experiment=experiment)
            else:
                napari.utils.notification.show_warning(f"Prepare Manipulator ({_METHOD}) is Not Yet Implemented")

        else:
            raise ValueError(f"Unknown workflow: {workflow}")
        
        self.update_experiment_signal.emit(self.experiment)

def main():
    import autolamella
    """Launch autoliftout ui"""
    viewer = napari.Viewer()
    autoliftout_ui = AutoLiftoutUIv2(viewer=viewer)
    viewer.window.add_dock_widget(
        autoliftout_ui, area="right", add_vertical_stretch=True, name=f"AutoLamella v{autolamella.__version__}"
    )
    napari.run()


if __name__ == "__main__":
    main()
