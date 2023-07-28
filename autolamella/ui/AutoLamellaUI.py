import logging
import os
import re
import sys
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import napari
import yaml
from fibsem import acquire, gis, milling, utils
from fibsem import patterning
from fibsem.microscope import FibsemMicroscope
from fibsem.patterning import FibsemMillingStage
from fibsem.structures import (
    ImageSettings,
    MicroscopeSettings,
    FibsemStagePosition,
)
from fibsem.ui.FibsemImageSettingsWidget import FibsemImageSettingsWidget
from fibsem.ui.FibsemMovementWidget import FibsemMovementWidget
from fibsem.ui.FibsemSystemSetupWidget import FibsemSystemSetupWidget
from fibsem.ui.FibsemMillingWidget import FibsemMillingWidget
from fibsem.ui.FibsemEmbeddedDetectionWidget import FibsemEmbeddedDetectionUI
from fibsem.ui.FibsemCryoSputterWidget import FibsemCryoSputterWidget
from fibsem.ui.utils import (
    _draw_patterns_in_napari,
    _get_directory_ui,
    _get_save_file_ui,
    _get_file_ui,
    convert_pattern_to_napari_rect,
    message_box_ui,
    validate_pattern_placement,
)
from fibsem.ui import utils as fui
from qtpy import QtWidgets

from autolamella.ui import utils as aui_utils
import autolamella.config as cfg
from autolamella import waffle as wfl
from autolamella.structures import (
    AutoLamellaWaffleStage,
    Experiment,
    Lamella,
    LamellaState,
)
from autolamella.ui.qt import AutoLamellaUI
from autolamella.utils import INSTRUCTION_MESSAGES, check_loaded_protocol
from PyQt5.QtCore import pyqtSignal

from napari.qt.threading import thread_worker
from fibsem.ui.FibsemMinimapWidget import FibsemMinimapWidget



_DEV_MODE = False
DEV_EXP_PATH = r"/home/patrick/github/autolamella/autolamella/log/TEST_PROTOCOLv2/experiment.yaml"
DEV_PROTOCOL_PATH = cfg.PROTOCOL_PATH

_AUTO_SYNC_MINIMAP = False

def log_status_message(lamella: Lamella, step: str):
    logging.debug(f"STATUS | {lamella._petname} | {lamella.state.stage.name} | {step}")

class AutoLamellaUI(QtWidgets.QMainWindow, AutoLamellaUI.Ui_MainWindow):
    ui_signal = pyqtSignal(dict)
    det_confirm_signal = pyqtSignal(bool)
    update_experiment_signal = pyqtSignal(Experiment)
    _run_milling_signal = pyqtSignal()
    
    def __init__(self, viewer: napari.Viewer) -> None:
        super(AutoLamellaUI, self).__init__()
        
        self.setupUi(self)

        self.viewer = viewer
        self.viewer.window._qt_viewer.dockLayerList.setVisible(False)
        self.viewer.window._qt_viewer.dockLayerControls.setVisible(False)

        logging.info(f"INIT | INITIALISATION | STARTED")

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
        self.tabWidget.addTab(self.system_widget, "System")

        self.image_widget: FibsemImageSettingsWidget = None
        self.movement_widget: FibsemMovementWidget = None
        self.milling_widget: FibsemMillingWidget = None

        self.WAITING_FOR_USER_INTERACTION: bool = False
        self.USER_RESPONSE: bool = False
        self.WAITING_FOR_UI_UPDATE: bool = False
        self._MILLING_RUNNING: bool = False



        # setup connections
        self.setup_connections()

        self.update_ui()

        if _DEV_MODE:
            self._auto_load()

        logging.info(f"INIT | INITIALISATION | FINISHED")


    def setup_connections(self):
        self.pushButton_add_lamella.clicked.connect(lambda: self.add_lamella_ui(pos=None))
        self.pushButton_add_lamella.setEnabled(False)
        self.pushButton_remove_lamella.clicked.connect(self.remove_lamella_ui)
        self.pushButton_remove_lamella.setEnabled(False)
        self.pushButton_go_to_lamella.clicked.connect(self.go_to_lamella_ui)
        self.pushButton_go_to_lamella.setEnabled(False)
        self.comboBox_current_lamella.currentIndexChanged.connect(self.update_lamella_ui)
        self.pushButton_save_position.clicked.connect(self.save_lamella_ui)
        self.pushButton_fail_lamella.clicked.connect(self.fail_lamella_ui)
        self.pushButton_revert_stage.clicked.connect(self.revert_stage)

        self.pushButton_run_waffle_trench.clicked.connect(self._run_trench_workflow)
        self.pushButton_run_autolamella.clicked.connect(self._run_lamella_workflow)
        self.pushButton_run_waffle_undercut.clicked.connect(self._run_undercut_workflow)
        self.pushButton_run_setup_autolamella.clicked.connect(self._run_setup_lamella_workflow)
  
        # system widget
        self.system_widget.set_stage_signal.connect(self.set_stage_parameters)
        self.system_widget.connected_signal.connect(self.connect_to_microscope)
        self.system_widget.disconnected_signal.connect(self.disconnect_from_microscope)

        # file menu
        self.actionNew_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Experiment.triggered.connect(self.setup_experiment)
        self.actionLoad_Protocol.triggered.connect(self.load_protocol)
        self.actionCryo_Sputter.triggered.connect(self._cryo_sputter)
        self.actionLoad_Positions.triggered.connect(self._load_positions)
        self.actionOpen_Minimap.triggered.connect(self._open_minimap)


        self.pushButton_yes.clicked.connect(self.push_interaction_button)
        self.pushButton_no.clicked.connect(self.push_interaction_button)

        # signals
        self.det_confirm_signal.connect(self._confirm_det)
        self.update_experiment_signal.connect(self._update_experiment)
        self.ui_signal.connect(self._ui_signal)
        self._run_milling_signal.connect(self._run_milling)

        self.pushButton_add_lamella.setStyleSheet("background-color: green")
        self.pushButton_remove_lamella.setStyleSheet("background-color: red")


    def setup_experiment(self):
        new_experiment = bool(self.sender() is self.actionNew_Experiment)
        experiment = aui_utils.setup_experiment_ui_v2(
            self, new_experiment=new_experiment
        )

        if experiment is None:
            napari.utils.notifications.show_info(f"Experiment not loaded.")
            return

        self.experiment = experiment
        napari.utils.notifications.show_info(
            f"Experiment {self.experiment.name} loaded."
        )
        if self.settings is not None:
            self.settings.image.save_path = self.experiment.path

        self._update_lamella_combobox()
        self.update_ui()


    ##################################################################

    # TODO: move this to system wideget??
    def connect_to_microscope(self):
        self.microscope = self.system_widget.microscope
        self.settings = self.system_widget.settings
        if self.experiment is not None:
            self.settings.image.save_path = self.experiment.path
        self.update_microscope_ui()
        self.update_ui()

    def disconnect_from_microscope(self):
        self.microscope = None
        self.settings = None
        self.update_microscope_ui()
        self.update_ui()

    def set_stage_parameters(self):
        if self.microscope is None:
            return
        self.settings.system.stage = (
            self.system_widget.settings.system.stage
        )  # TODO: this doesnt actually update the movement widget
        logging.debug(f"Stage parameters set to {self.settings.system.stage}")
        logging.info("Stage parameters set")

    def update_microscope_ui(self):
        """Update the ui based on the current state of the microscope."""

        if self.microscope is not None and not self._microscope_ui_loaded:
            # reusable components
            self.image_widget = FibsemImageSettingsWidget(
                microscope=self.microscope,
                image_settings=self.settings.image,
                viewer=self.viewer,
            )
            self.movement_widget = FibsemMovementWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                image_widget=self.image_widget,
            )
            self.milling_widget = FibsemMillingWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                image_widget=self.image_widget,
            )

            self.det_widget = FibsemEmbeddedDetectionUI(
                viewer=self.viewer, 
                model=None,
                )

            # add widgets to tabs
            self.tabWidget.addTab(self.image_widget, "Image")
            self.tabWidget.addTab(self.movement_widget, "Movement")
            self.tabWidget.addTab(self.milling_widget, "Milling")
            self.tabWidget.addTab(self.det_widget, "Detection")

            self._microscope_ui_loaded = True
            self.milling_widget.milling_position_changed.connect(self._update_milling_position)
            self.milling_widget._milling_finished.connect(self._milling_finished)

        else:
            if self.image_widget is None:
                return

            # remove tabs
            self.tabWidget.removeTab(6)
            self.tabWidget.removeTab(5)
            self.tabWidget.removeTab(4)
            self.tabWidget.removeTab(3)
            self.tabWidget.removeTab(3)

            self.image_widget.clear_viewer()
            self.image_widget.deleteLater()
            self.movement_widget.deleteLater()
            self.milling_widget.deleteLater()
            self.det_widget.deleteLater()

            self._microscope_ui_loaded = False

    def _open_minimap(self):
        if self.microscope is None:
            napari.utils.notifications.show_warning(f"Please connect to a microscope first... [No Microscope Connected]")
            return

        if self.movement_widget is None:
            napari.utils.notifications.show_warning(f"Please connect to a microscope first... [No Movement Widget]")
            return


        # TODO: should make this more generic i guess, but this is fine for now
        self.viewer2 = napari.Viewer(ndisplay=2)
        self.minimap_widget = FibsemMinimapWidget(self.microscope, self.settings, viewer=self.viewer2, parent=self)
        self.viewer2.window.add_dock_widget(
            self.minimap_widget, area="right", add_vertical_stretch=False, name="OpenFIBSEM Minimap"
        )
        self.minimap_widget._stage_position_moved.connect(self.movement_widget._stage_position_moved)
        if _AUTO_SYNC_MINIMAP:
            self.minimap_widget._stage_position_added.connect(self._update_stage_positions)
        napari.run(max_loop_level=2)


    def _update_stage_positions(self, position: FibsemStagePosition):
        # add lamella to experiment from tile manager
        if self.experiment is None:
            logging.warning("No experiment loaded")
            return

        self.add_lamella_ui(position)

    def _load_positions(self):
        
        
        path = _get_file_ui( msg="Select a position file to load", 
            path=self.experiment.path, 
            _filter= "*yaml", 
            parent=self)

        if path == "":
            napari.utils.notifications.show_info(f"No file selected..")
            return

        pdict = utils.load_yaml(path)
        
        positions = [FibsemStagePosition.__from_dict__(p) for p in pdict]

        for pos in positions:
            self.add_lamella_ui(pos)

    def update_ui(self):
        """Update the ui based on the current state of the application."""

        _experiment_loaded = bool(self.experiment is not None)
        _microscope_connected = bool(self.microscope is not None)
        _protocol_loaded = bool(self.settings is not None) and self._PROTOCOL_LOADED
        _lamella_selected = bool(self.experiment.positions) if _experiment_loaded else False

        # setup experiment -> connect to microscope -> select lamella -> run autolamella
        self.pushButton_fail_lamella.setVisible(_lamella_selected)
        self.pushButton_revert_stage.setVisible(_lamella_selected)
        self.comboBox_lamella_history.setVisible(_lamella_selected)
        
        # experiment loaded
        self.actionLoad_Protocol.setVisible(_experiment_loaded)
        self.actionCryo_Sputter.setVisible(_protocol_loaded)

        self.actionLoad_Positions.setVisible(_experiment_loaded and _microscope_connected)

        # labels
        if _experiment_loaded:
            self.label_experiment_name.setText(f"Experiment: {self.experiment.name}")

            msg = "\nLamella Info:\n"
            for lamella in self.experiment.positions:
                if lamella._is_failure:
                    msg += f"Lamella {lamella._petname} \t\t {lamella.state.stage.name} \t\t FAILED \n"
                else:
                    msg += f"Lamella {lamella._petname} \t\t {lamella.state.stage.name} \n"
            self.label_info.setText(msg)

            self.comboBox_current_lamella.setVisible(_lamella_selected)

        if _protocol_loaded:
            method = self.settings.protocol.get("method", "waffle")
            self.label_protocol_name.setText(
                f"Protocol: {self.settings.protocol.get('name', 'protocol')} ({method.title()} Method)"
            )

        # buttons
        self.pushButton_add_lamella.setEnabled(_protocol_loaded and _experiment_loaded)
        self.pushButton_remove_lamella.setEnabled(_lamella_selected)
        self.pushButton_save_position.setEnabled(_lamella_selected)
        self.pushButton_go_to_lamella.setEnabled(_lamella_selected)


        # Current Lamella Status
        if _lamella_selected:
            self.update_lamella_ui()

        # instructions# TODO: update with autolamella instructions
        INSTRUCTIONS = {"NOT_CONNECTED": "Please connect to the microscope.",
                        "NO_EXPERIMENT": "Please create or load an experiment.",
                        "NO_PROTOCOL": "Please load a protocol.",
                        "NO_LAMELLA": "Please Run Setup to select Lamella Positions.",
                        "LAMELLA_READY": "Lamella Positions Selected. Ready to Run AutoLamella.",
                        }

        if not _microscope_connected:
            self._set_instructions(INSTRUCTIONS["NOT_CONNECTED"])
        elif not _experiment_loaded:
            self._set_instructions(INSTRUCTIONS["NO_EXPERIMENT"])
        elif not _protocol_loaded:
            self._set_instructions(INSTRUCTIONS["NO_PROTOCOL"])
        elif not _lamella_selected:
            self._set_instructions(INSTRUCTIONS["NO_LAMELLA"])
        elif _lamella_selected:
            self._set_instructions(INSTRUCTIONS["LAMELLA_READY"])

    def _update_lamella_combobox(self):
        # detail combobox
        idx = self.comboBox_current_lamella.currentIndex()
        self.comboBox_current_lamella.currentIndexChanged.disconnect()
        self.comboBox_current_lamella.clear()
        self.comboBox_current_lamella.addItems([lamella.info for lamella in self.experiment.positions])
        if idx != -1 and self.experiment.positions:
            self.comboBox_current_lamella.setCurrentIndex(idx)
        self.comboBox_current_lamella.currentIndexChanged.connect(self.update_lamella_ui)

    def update_lamella_ui(self):

        # set the info for the current selected lamella
        if self.experiment is None:
            return
        
        if self.experiment.positions == []:
            return      

        idx = self.comboBox_current_lamella.currentIndex()
        lamella: Lamella = self.experiment.positions[idx]

        logging.info(f"Updating Lamella UI for {lamella.info}")

        # buttons
        SETUP_STAGES =  [AutoLamellaWaffleStage.Setup, AutoLamellaWaffleStage.MillTrench]
        READY_STAGES = [AutoLamellaWaffleStage.ReadyTrench, AutoLamellaWaffleStage.ReadyLamella]
        if lamella.state.stage in SETUP_STAGES:
            self.pushButton_save_position.setText(f"Save Position")
            self.pushButton_save_position.setStyleSheet("background-color: darkgray; color: white;")
            self.pushButton_save_position.setEnabled(True)
            self.milling_widget._PATTERN_IS_MOVEABLE = True
        elif lamella.state.stage in READY_STAGES:
            self.pushButton_save_position.setText(f"Position Ready")
            self.pushButton_save_position.setStyleSheet(
                "color: white; background-color: green"
            )
            self.pushButton_save_position.setEnabled(True)
            self.milling_widget._PATTERN_IS_MOVEABLE = False

        if lamella.state.stage in [AutoLamellaWaffleStage.Setup, AutoLamellaWaffleStage.ReadyTrench, AutoLamellaWaffleStage.ReadyLamella]:
            
            if self._PROTOCOL_LOADED:
                
                method = self.settings.protocol.get("method", "waffle")
                pattern = "trench" if  method == "waffle" else "lamella"
                position = lamella.trench_position if method == "waffle" else lamella.lamella_position

                # load the default protocol unless in lamella protocol
                protocol = lamella.protocol if pattern in lamella.protocol else self.settings.protocol
                stages = patterning._get_milling_stages(pattern, protocol, position)

                # feature (or at SetupLamella)
                if method == "default":
                    _feature_name = "notch" if self.settings.protocol["notch"]["enabled"]  else "microexpansion"
                    protocol = lamella.protocol if _feature_name in lamella.protocol else self.settings.protocol
                    feature_stage = patterning._get_milling_stages(_feature_name, protocol, lamella.feature_position)
                    stages += feature_stage

                    # fiducial
                    if self.settings.protocol["fiducial"]["enabled"]:
                        protocol = lamella.protocol if "fiducial" in lamella.protocol else self.settings.protocol
                        fiducial_stage = patterning._get_milling_stages("fiducial", protocol, lamella.fiducial_centre)
                        stages += fiducial_stage

                self.milling_widget.set_milling_stages(stages)

        if lamella._is_failure:
            self.pushButton_fail_lamella.setText("Unfail Lamella")
        else:
            self.pushButton_fail_lamella.setText("Mark Lamella As Failed")

        def _to_str(state: LamellaState):
            return f"{state.stage.name} ({datetime.fromtimestamp(state.end_timestamp).strftime('%I:%M%p')})"
        self.comboBox_lamella_history.clear()
        self.comboBox_lamella_history.addItems([_to_str(state) for state in lamella.history])

    def _update_milling_position(self):
        # triggered when milling position is moved
        if self.experiment is None:
            return
        
        if self.experiment.positions == []:
            return

        idx = self.comboBox_current_lamella.currentIndex()
        lamella: Lamella = self.experiment.positions[idx]

        if lamella.state.stage != AutoLamellaWaffleStage.Setup:
            return

        logging.info(f"Updating Lamella Pattern for {lamella.info}")

        # update the trench point
        method = self.settings.protocol.get("method", "waffle")
        self._update_milling_protocol(idx=idx, method=method)

        self.experiment.save() 


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

        self.settings.protocol = utils.load_protocol(protocol_path=PATH)
        self._PROTOCOL_LOADED = True
        napari.utils.notifications.show_info(
            f"Loaded Protocol from {os.path.basename(PATH)}"
        )
        self.update_ui()

    def _cryo_sputter(self):

        cryo_sputter_widget = FibsemCryoSputterWidget(self.microscope, self.settings)
        cryo_sputter_widget.exec_()

    def save_protocol(self):
        fname = _get_save_file_ui(msg="Select protocol file", path=cfg.LOG_PATH)
        if fname == "":
            return

        # give protocol path as suffix .yaml if not
        fname = Path(fname).with_suffix(".yaml")

        with open(os.path.join(fname), "w") as f:
            yaml.safe_dump(self.settings.protocol, f, indent=4)

        logging.info("Protocol saved to file")


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


    def _auto_load(self):

        # connect to microscope
        self.system_widget.connect_to_microscope()

        # load experiment
        self.experiment = Experiment.load(DEV_EXP_PATH)
        self.settings.image.save_path = self.experiment.path
        self._update_lamella_combobox()

        # load protocol
        self.settings.protocol = utils.load_protocol(protocol_path=DEV_PROTOCOL_PATH)
        self._PROTOCOL_LOADED = True

        self.update_ui()
        return 

    ###################################### Imaging ##########################################

    def enable_buttons(
        self,
        add: bool = False,
        remove: bool = False,
        fiducial: bool = False,
        go_to: bool = False,
    ):
        self.add_button.setEnabled(add)
        self.remove_button.setEnabled(remove)
        self.save_button.setEnabled(fiducial)
        self.save_button.setText("Mill Fiducial for current lamella")
        self.save_button.setStyleSheet("color: white")
        self.go_to_lamella.setEnabled(go_to)
        self.run_button.setEnabled(self.can_run_milling())
        self.run_button.setText("Run AutoLamella")
        self.run_button.setStyleSheet("color: white; background-color: green")

    def go_to_lamella_ui(self):
        print("go to lamella ui")
        
        idx = self.comboBox_current_lamella.currentIndex()
        lamella: Lamella = self.experiment.positions[idx]
        position = lamella.state.microscope_state.absolute_position
        self.microscope._safe_absolute_stage_movement(position)
        logging.info(f"Moved to position of {lamella.info}.")
        self.movement_widget.update_ui_after_movement()

    def add_lamella_ui(self, pos:FibsemStagePosition=None):

        lamella = Lamella(
            path=self.experiment.path,
            _number=len(self.experiment.positions) + 1,
        )
        lamella.state.microscope_state = self.microscope.get_current_microscope_state()

        if pos is not None:
            lamella.state.microscope_state.absolute_position = deepcopy(pos)

        self.experiment.positions.append(deepcopy(lamella))
        
        self.experiment.save()

        logging.info(f"Added lamella {lamella._petname} to experiment {self.experiment.name}.")

        self._update_lamella_combobox()
        self.update_ui()
    
    def remove_lamella_ui(self):

        idx = self.comboBox_current_lamella.currentIndex()
        self.experiment.positions.pop(idx)
        self.experiment.save()

        logging.info("Lamella removed from experiment")
        self._update_lamella_combobox()
        self.update_ui()

    def fail_lamella_ui(self):
        idx = self.comboBox_current_lamella.currentIndex()
        self.experiment.positions[idx]._is_failure = True if not self.experiment.positions[idx]._is_failure else False
        self.update_ui()

    def revert_stage(self):
        idx = self.comboBox_current_lamella.currentIndex()
        hidx = self.comboBox_lamella_history.currentIndex()
        self.experiment.positions[idx].state = deepcopy(self.experiment.positions[idx].history[hidx])
        self.update_ui()

    def save_lamella_ui(self):
        # triggered when save button is pressed

        if self.experiment.positions == []:
            return

        idx = self.comboBox_current_lamella.currentIndex()
        # TOGGLE BETWEEN READY AND SETUP

        method = self.settings.protocol.get("method", "waffle")
        READY_STATE = AutoLamellaWaffleStage.ReadyTrench if method == "waffle" else AutoLamellaWaffleStage.ReadyLamella
        
        lamella: Lamella = self.experiment.positions[idx]

        if self.experiment.positions[idx].state.stage is AutoLamellaWaffleStage.Setup:
            self.experiment.positions[idx].state.microscope_state = deepcopy(
                self.microscope.get_current_microscope_state()
            )
            self.experiment.positions[idx].state.stage = READY_STATE

            # update the protocol / point
            self._update_milling_protocol(idx, method)

            # get current ib image, save as reference
            fname = os.path.join(
                self.experiment.positions[idx].path, "ref_position_ib"
            )
            self.image_widget.ib_image.save(fname)
            self.milling_widget._PATTERN_IS_MOVEABLE = False

            wfl.log_status_message(self.experiment.positions[idx], "STARTED")

        elif (self.experiment.positions[idx].state.stage is READY_STATE):
            self.experiment.positions[idx].state.stage = AutoLamellaWaffleStage.Setup
            self.milling_widget._PATTERN_IS_MOVEABLE = True

        self._update_lamella_combobox()
        self.update_ui()
        self.experiment.save()

    def _update_milling_protocol(self, idx: int, method: str):

        # TODO: add fiducial for lamella
        # TODO: add feature for lamella

        stages = deepcopy(self.milling_widget.get_milling_stages())
        if method == "waffle":
            self.experiment.positions[idx].trench_position = stages[0].pattern.point
            self.experiment.positions[idx].protocol["trench"] = deepcopy(patterning._get_protocol_from_stages(stages))
        else:
            n_lamella = len(self.settings.protocol["lamella"]["stages"])

            # lamella
            self.experiment.positions[idx].lamella_position = stages[0].pattern.point
            self.experiment.positions[idx].protocol["lamella"] = deepcopy(patterning._get_protocol_from_stages(stages[:n_lamella]))

            # feature
            _feature_name = "notch" if self.settings.protocol["notch"]["enabled"] else "microexpansion"
            self.experiment.positions[idx].feature_position = stages[n_lamella].pattern.point
            self.experiment.positions[idx].protocol[_feature_name] = deepcopy(patterning._get_protocol_from_stages(stages[n_lamella]))
            
            # fiducial (optional)
            if self.settings.protocol["fiducial"]["enabled"]:
                self.experiment.positions[idx].fiducial_centre = stages[-1].pattern.point
                self.experiment.positions[idx].protocol["fiducial"] = deepcopy(patterning._get_protocol_from_stages(stages[-1]))



    def _run_milling(self):
        self._MILLING_RUNNING = True
        self.milling_widget.run_milling()

    def _milling_finished(self):
        self._MILLING_RUNNING = False

    def _confirm_det(self):
        if self.det_widget is not None:
            self.det_widget.confirm_button_clicked()

    def _run_trench_workflow(self):
        self.milling_widget.milling_position_changed.disconnect()

        self.worker = self._threaded_worker(
            microscope=self.microscope, settings=self.settings, experiment=self.experiment, workflow="trench",
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.start()

    def _run_undercut_workflow(self):
        self.milling_widget.milling_position_changed.disconnect()

        self.worker = self._threaded_worker(
            microscope=self.microscope, settings=self.settings, experiment=self.experiment, workflow="undercut",
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.start()
    
    def _run_setup_lamella_workflow(self):
        self.milling_widget.milling_position_changed.disconnect()

        self.worker = self._threaded_worker(
            microscope=self.microscope, settings=self.settings, experiment=self.experiment, workflow="setup-lamella",
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.start()

    def _run_lamella_workflow(self):
        self.milling_widget.milling_position_changed.disconnect()

        self.worker = self._threaded_worker(
            microscope=self.microscope, settings=self.settings, experiment=self.experiment, workflow="lamella",
        )
        self.worker.finished.connect(self._workflow_finished)
        self.worker.start()


    def _workflow_finished(self):
        logging.info(f'Workflow finished.')
        self.milling_widget.milling_position_changed.connect(self._update_milling_position)

    def _ui_signal(self, info:dict) -> None:
        """Update the UI with the given information, ready for user interaction"""
        
        _mill = bool(info["mill"] is not None)
        _det = bool(info["det"] is not None)
        stages = info.get("stages", None)

        if _det:
            self.det_widget.set_detected_features(info["det"])
            self.tabWidget.setCurrentIndex(6)
        
        if _mill:
            self.tabWidget.setCurrentIndex(5)

        if info["eb_image"] is not None:
            eb_image = info["eb_image"]
            self.image_widget.update_viewer(eb_image.data, "ELECTRON")
            self.image_widget.eb_image = eb_image
        if info["ib_image"] is not None:
            ib_image = info["ib_image"]
            self.image_widget.update_viewer(ib_image.data, "ION")
            self.image_widget.ib_image = ib_image


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
        self._update_lamella_combobox()
        self.update_ui()

    @thread_worker
    def _threaded_worker(self, microscope: FibsemMicroscope, settings: MicroscopeSettings, experiment: Experiment, workflow: str="trench"):
        
        self.milling_widget._PATTERN_IS_MOVEABLE = True
        self.WAITING_FOR_USER_INTERACTION = False
        self._set_instructions(f"Running {workflow.title()} workflow...", None, None)
        logging.info(f"RUNNING {workflow.upper()} WORKFLOW")

        if workflow == "trench":
            wfl.run_trench_milling(microscope, settings, experiment, parent_ui=self )

        if workflow == "undercut":
            wfl.run_undercut_milling(microscope, settings, experiment, parent_ui=self )

        if workflow == "setup-lamella":
            wfl.run_setup_lamella(microscope, settings, experiment, parent_ui=self )

        if workflow == "lamella":
            wfl.run_lamella_milling(microscope, settings, experiment, parent_ui=self )

        self.update_experiment_signal.emit(self.experiment)



def main():
    autolamella_ui = AutoLamellaUI(viewer=napari.Viewer())
    autolamella_ui.viewer.window.add_dock_widget(
        autolamella_ui, area="right", 
        add_vertical_stretch=True, name="AutoLamella"
    )
    napari.run()


if __name__ == "__main__":
    main()
