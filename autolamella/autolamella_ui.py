import logging
import os
import re
import sys
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from time import sleep
from collections import Counter

import napari
import numpy as np
import yaml
from fibsem import acquire, constants, conversions, gis, milling, utils
from fibsem import patterning
from fibsem.alignment import beam_shift_alignment
from fibsem.microscope import (DemoMicroscope, FibsemMicroscope,
                               TescanMicroscope, ThermoMicroscope)
from fibsem.patterning import (FibsemMillingStage, FiducialPattern,
                               MicroExpansionPattern, TrenchPattern)
from fibsem.structures import (BeamType, FibsemImage, FibsemMillingSettings,
                               FibsemPatternSettings, FibsemRectangle,
                               ImageSettings, MicroscopeSettings, Point)
from fibsem.ui.FibsemImageSettingsWidget import FibsemImageSettingsWidget
from fibsem.ui.FibsemMovementWidget import FibsemMovementWidget
from fibsem.ui.FibsemSystemSetupWidget import FibsemSystemSetupWidget
from fibsem.ui.utils import (_draw_patterns_in_napari, _get_directory_ui, _get_save_file_ui,
                             _get_file_ui, convert_pattern_to_napari_rect,
                             message_box_ui, validate_pattern_placement)
from napari.utils.notifications import show_error, show_info
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QInputDialog, QMessageBox
from qtpy import QtWidgets

import autolamella.config as cfg
from autolamella import waffle as wfl
from autolamella.structures import (AutoLamellaStage, AutoLamellaWaffleStage,
                                    Experiment, Lamella, LamellaState)
from autolamella.ui import UI as UI
from autolamella.utils import INSTRUCTION_MESSAGES, check_loaded_protocol


def log_status_message(lamella: Lamella, step: str):
    logging.debug(
        f"STATUS | {lamella._name} | {lamella.state.stage.name} | {step}"
    )

class UiInterface(QtWidgets.QMainWindow, UI.Ui_MainWindow):
    def __init__(self, viewer, *args, obj=None, **kwargs) -> None:
        super(UiInterface, self).__init__(*args, **kwargs)
        self.viewer = viewer
        self.setupUi(self)
        
        # setting up ui
        self.setup_connections()
        self.lines = 0

        self.viewer.window.qt_viewer.dockLayerList.hide()
        self.viewer.window.qt_viewer.dockLayerControls.hide()

        self.pattern_settings = []
        self.save_path = None
        self.log_txt.setPlainText(
            "Welcome to OpenFIBSEM AutoLamella! Begin by Connecting to a Microscope. \n"
        )
        # Initialise microscope object
        self.microscope = None
        self.settings = None
        self.viewer.grid.enabled = False

        # Initialise experiment object
        self.experiment: Experiment = None
        self.protocol_loaded = False
        self.fiducial_position = None
        self.lamella_position = None
        self.moving_fiducial = False   
        CONFIG_PATH = os.path.join(os.path.dirname(__file__))
        self.system_widget = FibsemSystemSetupWidget(
                microscope=self.microscope,
                settings=self.settings,
                viewer=self.viewer,
                config_path = CONFIG_PATH,
            )
        
        self.tabWidget.addTab(self.system_widget, "System")
        self.tabWidget.setTabVisible(0, False)
        self.tabWidget.setTabVisible(1, False)

        self.system_widget.set_stage_signal.connect(self.set_stage_parameters)
        self.system_widget.connected_signal.connect(self.connect_to_microscope)
        self.system_widget.disconnected_signal.connect(self.disconnect_from_microscope)

        self.instructions_textEdit.setReadOnly(True)
        self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["welcome_message"])
        self.initial_setup_stage = False
        self.image_widget = None
        self.movement_widget = None

    def setup_connections(self):
        self.show_lamella.stateChanged.connect(self.update_displays)
        self.show_lamella.setEnabled(False)
        self.checkBox_show_trench.stateChanged.connect(self.update_displays)
        self.checkBox_show_trench.setEnabled(False)
        self.checkBox_show_notch.stateChanged.connect(self.update_displays)
        self.microexpansionCheckBox.stateChanged.connect(self.draw_patterns)
        self.add_button.clicked.connect(self.add_lamella_ui)
        self.add_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_lamella_ui)
        self.remove_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_autolamella_v2)
        self.platinum.triggered.connect(self.splutter_platinum)
        self.create_exp.triggered.connect(self.create_experiment)
        self.load_exp.triggered.connect(self.load_experiment)
        self.action_load_protocol.triggered.connect(self.load_protocol)
        self.save_button.clicked.connect(self.save_lamella_ui)
        self.save_button.setEnabled(False)
        self.go_to_lamella.clicked.connect(self.go_to_lamella_ui)
        self.go_to_lamella.setEnabled(False)
        self.lamella_index.currentIndexChanged.connect(self.update_ui)
        self.pushButton_run_waffle_trench.clicked.connect(self.run_waffle_trench)
        self.pushButton_run_waffle_notch.clicked.connect(self.run_waffle_notch)
        self.pushButton_save_position.clicked.connect(self.save_current_position)
        self.comboBox_moving_pattern.clear()
        self.comboBox_moving_pattern.addItems(["Trench", "Notch", "Fiducial", "Lamella"])

    def connect_protocol_signals(self):
        self.beamshift_attempts.editingFinished.connect(self.get_protocol_from_ui)
        self.fiducial_length.editingFinished.connect(self.get_protocol_from_ui)
        self.width_fiducial.editingFinished.connect(self.get_protocol_from_ui)
        self.depth_fiducial.editingFinished.connect(self.get_protocol_from_ui)
        self.current_fiducial.editingFinished.connect(self.get_protocol_from_ui)
        self.stage_lamella.currentTextChanged.connect(self.select_stage)
        self.lamella_width.editingFinished.connect(self.get_protocol_from_ui)
        self.lamella_height.editingFinished.connect(self.get_protocol_from_ui)
        self.trench_height.editingFinished.connect(self.get_protocol_from_ui)
        self.depth_trench.editingFinished.connect(self.get_protocol_from_ui)
        self.offset.editingFinished.connect(self.get_protocol_from_ui)
        self.current_lamella.editingFinished.connect(self.get_protocol_from_ui)
        self.size_ratio.editingFinished.connect(self.get_protocol_from_ui)
        self.export_protocol.clicked.connect(self.save_protocol)
        self.micro_exp_distance.editingFinished.connect(self.get_protocol_from_ui)
        self.micro_exp_height.editingFinished.connect(self.get_protocol_from_ui)
        self.micro_exp_width.editingFinished.connect(self.get_protocol_from_ui)
        self.comboBoxapplication_file.currentTextChanged.connect(self.get_protocol_from_ui)

        # trench
        self.doubleSpinBox_trench_lamella_height.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_lamella_width.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_milling_depth.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_trench_height.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_offset.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_size_ratio.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_trench_milling_current.editingFinished.connect(self.get_protocol_from_ui)

        # notch
        self.doubleSpinBox_notch_hheight.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_hwidth.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_vheight.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_vwidth.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_depth.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_distance.editingFinished.connect(self.get_protocol_from_ui)
        self.doubleSpinBox_notch_milling_current.editingFinished.connect(self.get_protocol_from_ui)
        self.checkBox_notch_flip.stateChanged.connect(self.get_protocol_from_ui)


    def get_milling_settings(self, protocol):
        mill_settings = FibsemMillingSettings(
                patterning_mode="Serial",
                application_file=self.settings.protocol["application_file"],
                milling_current=protocol["milling_current"],
                hfw = self.image_widget.image_settings.hfw,
                preset = protocol.get("preset", None),
            )
        return mill_settings


    def draw_patterns(self):
        if self.settings.protocol is None:
            logging.info("No protocol loaded")
            return
        # Initialise the Lamella and Fiducial Settings
        self.patterns_protocol = []
        pixelsize = self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]
        self.lamella_stages = []
        self.fiducial_stage = None

        ############### Lamella Pattern ################
        # TODO: we shouldnt let the user do this until they add a lamella... it would resolve a lot of problems
        default_position_lamella = self.lamella_position if self.lamella_position is not None else Point(0.0, 0.0) # has the user defined a position manually? If not use 0,0
        self.lamella_position = default_position_lamella
        index = self.lamella_index.currentIndex()
        if self.experiment is not None and len(self.experiment.positions) > 0: # do we have an experiment with at least one lamella
                lamella_position = self.experiment.positions[index].lamella_centre
        else:
            lamella_position = default_position_lamella  

        ##### MicroExpansion #####
        if self.microexpansionCheckBox.isChecked():
            pattern = MicroExpansionPattern()
            protocol = self.settings.protocol["microexpansion"]
            protocol["depth"] = self.settings.protocol["lamella"]["stages"][0]["depth"]
            protocol["milling_current"] = self.settings.protocol["lamella"]["stages"][0]["milling_current"]
            protocol["lamella_width"] = self.settings.protocol["lamella"]["lamella_width"]
            protocol["application_file"] = self.settings.protocol["application_file"]
            mill_settings = self.get_milling_settings(protocol)

            pattern.define(
                    protocol = protocol,
                    point = lamella_position
                )
            mill_stage = FibsemMillingStage(
                name = "MicroExpansion",
                num = 0,
                milling = mill_settings,
                pattern = pattern,
            )
            self.lamella_stages.append(mill_stage)

        ###### Lamella ######

        from fibsem import patterning
        self.settings.protocol["lamella"]["stages"][0]["hfw"] = self.image_widget.image_settings.hfw
        self.settings.protocol["lamella"]["stages"][1]["hfw"] = self.image_widget.image_settings.hfw
        self.settings.protocol["lamella"]["stages"][2]["hfw"] = self.image_widget.image_settings.hfw
        self.lamella_stages =  patterning._get_milling_stages("lamella", self.settings.protocol, point=lamella_position)

        ############### Fiducial Pattern ################

        protocol = self.settings.protocol["fiducial"]

        default_position_fiducial = self.fiducial_position if self.fiducial_position is not None else Point(-self.image_widget.image_settings.resolution[0]/3 * pixelsize, 0.0) # has the user defined a fiducial position?
        self.fiducial_position = default_position_fiducial
        if self.experiment is not None and len(self.experiment.positions) > 0:
                    fiducial_position = self.experiment.positions[index].fiducial_centre
        else:
            fiducial_position = default_position_fiducial
        fiducial_milling = self.get_milling_settings(protocol)
        fiducial = FiducialPattern()
        fiducial.define(
            protocol = protocol,
            point = fiducial_position,
        )
        stage = FibsemMillingStage(
            name = "fiducial",
            num = 0,
            milling = fiducial_milling,
            pattern = fiducial,
        )

        self.fiducial_stage = stage

        # TRENCH
        from fibsem import patterning
        if self.experiment is not None and len(self.experiment.positions) > 0:
            trench_centre = self.experiment.positions[index].trench_centre
        else:
            trench_centre = Point(0.0, 0.0)
        self.settings.protocol["trench"]["hfw"] = self.image_widget.image_settings.hfw
        self.trench_stages = patterning._get_milling_stages("trench", self.settings.protocol, point = trench_centre)

        # NOTCH
        if self.experiment is not None and len(self.experiment.positions) > 0:
            notch_centre = self.experiment.positions[index].notch_centre
        else:
            notch_centre = Point(0.0, 0.0)
        self.notch_stages = patterning._get_milling_stages("notch", self.settings.protocol, point = notch_centre)

        self.update_displays()

    def create_experiment(self):
        if self.experiment is not None:
            self.timer.stop()
        self.experiment = None

        folder_path = _get_directory_ui(msg="Select experiment directory",path=cfg.LOG_PATH) 
        self.save_path = folder_path if folder_path != "" else None

        if folder_path == '':
            logging.info("No path selected, experiment not created")
            return
        
        now = datetime.now()
        DATE = now.strftime("%Y-%m-%d-%H-%M")
        name, ok = QInputDialog.getText(self, "Experiment name", "Please enter experiment name", text=f"Autolamella-{DATE}")

        if name is None or not ok:
            logging.info("No name entered, experiment not created")
            return
        
        self.experiment_name = name
        self.experiment = Experiment(path=self.save_path, name=self.experiment_name)
        self.log_path = os.path.join(self.save_path, self.experiment_name, "logfile.log")
        self.lines = 0

        if self.microscope is not None:
            self.timer.start(1000)
            self.experiment_created_and_microscope_connected()
        else:
            self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["connect_message"])
            _ = message_box_ui(
                title="Next step:",
                text="Please connect to a microscope.",
                buttons=QMessageBox.Ok,
            )
        self.experiment.save()
        logging.info("Experiment created")
        self.update_ui()

    def load_experiment(self):
        if self.microscope is not None:
            self.timer.stop()
            self.show_lamella.setEnabled(False)
            if self.image_widget is not None:
                self.image_widget.deleteLater()
                self.image_widget = None
                self.movement_widget.deleteLater()
                self.movement_widget = None
            self.tabWidget.setTabVisible(4, False)
            self.tabWidget.setTabVisible(3, False)
            self.tabWidget.setTabVisible(0, False)

        self.experiment = None
        self.lamella_count_txt.setPlainText("")

        file_path = _get_file_ui(msg="Select experiment yaml file",path=cfg.LOG_PATH)
        self.experiment = Experiment.load(file_path) if file_path != '' else self.experiment
        if file_path == '':
            return

        # add lamella to combobox
        self.lamella_index.clear()
        names = [lamella._name for lamella in self.experiment.positions]
        self.lamella_index.addItems(names)
        
        folder_path = os.path.dirname(file_path)
        self.log_path = os.path.join(folder_path, "logfile.log")
        self.save_path = folder_path
        self.lines = 0
        
        _ = message_box_ui(
                title="Please take images.",
                text="Please take images with both beams before proceeding further.",
                buttons=QMessageBox.Ok,
            )
        if self.microscope is not None:
            self.timer.start(1000)
            self.experiment_created_and_microscope_connected()
        else:
            _ = message_box_ui(
                title="Next step:",
                text="Please connect to a microscope.",
                buttons=QMessageBox.Ok,
            )
        self.update_ui()
        logging.info("Experiment loaded")

    ##################################################################

    def update_log(self):
        try:
            with open(self.log_path, "r") as f:
                lines = f.read().splitlines()
                lin_len = len(lines)

            if self.lines != lin_len:
                for i in reversed(range(lin_len - self.lines)):
                    line_display = lines[-1 - i]
                    if re.search("DEBUG", line_display) or re.search("vispy", line_display) or re.search("Unknown key", line_display) or re.search("STATUS", line_display):
                        self.lines = lin_len
                        continue
                    line_divided = line_display.split(",")
                    time = line_divided[0]
                    message = line_display.split("—")
                    disp_str = f"{time} | {message[-1]}"

                    disp_paragraph = self.log_txt.toPlainText() + disp_str + "\n"

                    self.lines = lin_len
                    self.log_txt.setPlainText(disp_paragraph)

                    cursor = self.log_txt.textCursor()
                    cursor.movePosition(QTextCursor.End)
                    self.log_txt.setTextCursor(cursor)
        except:
            pass

    def connect_to_microscope(self):

        self.microscope = self.system_widget.microscope
        self.settings = self.system_widget.settings
        self.log_path = os.path.join(
            self.settings.image.save_path, "logfile.log"
        )
        self.lines = 0
        
        direction_list = self.microscope.get_scan_directions()
        for i in range(len(direction_list)-1):
            self.scanDirectionComboBox.addItem(direction_list[i-1])

        if self.experiment is not None:
            self.experiment_created_and_microscope_connected()
        else:
            self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["create_experiment_message"])
            _ = message_box_ui(
                title="Next step:",
                text="Please create an experiment (file menu).",
                buttons=QMessageBox.Ok,
            )
            
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_log)
        self.timer.start(1000)


    def experiment_created_and_microscope_connected(self):
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
        self.image_widget.picture_signal.connect(self.draw_patterns)
        
        self.tabWidget.addTab(self.image_widget, "Image")
        self.tabWidget.addTab(self.movement_widget, "Movement")
        self.tabWidget.setTabVisible(0, True)
        self.tabWidget.setTabVisible(1, True)

        self.system_widget.get_stage_settings_from_ui()
        if self.protocol_loaded is False:
            self.load_protocol()
        
        self.draw_patterns()
        self.update_ui()
        self.image_widget.eb_layer.mouse_drag_callbacks.append(self._clickback)
        self.image_widget.picture_signal.connect(self.update_ui)
        self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["take_images_message"])

    def update_image_message(self,add=False):

        if self.initial_setup_stage is False:

            self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["add_lamella_message"])

        if add is True or len(self.experiment.positions) > 0:
            
            stages = [lamella.state.stage for lamella in self.experiment.positions]

            from collections import Counter
            stages = Counter(stages)
            self.lamella_finished = stages[AutoLamellaWaffleStage.Finished] 
            self.lamella_saved = stages[AutoLamellaWaffleStage.MillFeatures]
            self.lamella_added = len(self.experiment.positions) - self.lamella_finished
            self.lamella_total = len(self.experiment.positions)


            create_lamella_text = INSTRUCTION_MESSAGES["mod_lamella_message"].format(self.lamella_added,
                                                                                     self.lamella_saved,
                                                                                     self.lamella_added,
                                                                                     self.lamella_finished,
                                                                                     self.lamella_total)

            self.instructions_textEdit.setPlainText(create_lamella_text)

    def disconnect_from_microscope(self):

        if self.microscope is not None:
            self.microscope = None
            self.settings = None
            self.protocol_loaded = False
            self.tabWidget.setTabVisible(4, False)
            self.tabWidget.setTabVisible(3, False)
            self.tabWidget.setTabVisible(0, False)
            self.show_lamella.setEnabled(False)
            self.show_lamella.setChecked(False)
            self.viewer.layers.clear()
            self.instructions_textEdit.setPlainText("Connect to a microscope")
            self.initial_setup_stage = False
            self.lamella_saved = 0

    def set_stage_parameters(self):
        self.settings.system.stage = self.system_widget.settings.system.stage   
        logging.info("Stage parameters set")  

    def load_protocol(self): 

        protocol_path = _get_file_ui(path=cfg.BASE_PATH, msg="Select protocol file",_filter="*yaml")

        if protocol_path == '':
             _ = message_box_ui(
                title="Protocol error",
                text="No Protocol Selected: Please select a protocol file",
                buttons=QMessageBox.Ok,
            )
             self.protocol_loaded = False
             self.load_protocol()
            
        
        self.settings.protocol = utils.load_protocol(
            protocol_path=protocol_path
        ) 

        _THERMO = isinstance(self.microscope, (ThermoMicroscope))
        _TESCAN = isinstance(self.microscope, (TescanMicroscope))
        _DEMO = isinstance(self.microscope, (DemoMicroscope))

        error_returned = check_loaded_protocol(self.settings.protocol, _THERMO, _TESCAN, _DEMO)

        if error_returned is not None:
            _ = message_box_ui(
                title="Protocol error",
                text=error_returned,
                buttons=QMessageBox.Ok,
            )
            self.protocol_loaded = False
            self.load_protocol()

        if isinstance(self.microscope, TescanMicroscope):
            presets = self.microscope.get('presets')
            self.presetComboBox.addItems(presets)
            self.presetComboBox_fiducial.addItems(presets)
            self.application_file_label.hide()
            self.comboBoxapplication_file.hide()
            self.presetComboBox.setEnabled(True)
            self.presetComboBox.show()
            self.presetComboBox_fiducial.setEnabled(True)
            self.presetComboBox_fiducial.show()
            self.presetLabel.show()
            self.presetLabel_2.show()
        elif isinstance(self.microscope, ThermoMicroscope):
            self.application_file_label.show()
            self.comboBoxapplication_file.show()
            self.presetComboBox.setEnabled(False)
            self.presetComboBox.hide()
            self.presetComboBox_fiducial.setEnabled(False)
            self.presetComboBox_fiducial.hide()
            self.presetLabel.hide()
            self.presetLabel_2.hide()
            application_files = self.microscope.get_available_values('application_file')
            self.comboBoxapplication_file.addItems(application_files)
        self.set_ui_from_protocol() 
        self.connect_protocol_signals()
        self.show_lamella.setEnabled(True)
        self.checkBox_show_trench.setEnabled(True)
        return True

    def set_ui_from_protocol(self):

        self.protocol_txt.setText(self.settings.protocol["name"])
        self.protocol_loaded = True

        ## Loading protocol tab 
        self.beamshift_attempts.setValue((self.settings.protocol["lamella"]["beam_shift_attempts"]))
        self.fiducial_length.setValue((self.settings.protocol["fiducial"]["height"]*constants.SI_TO_MICRO))
        self.width_fiducial.setValue((self.settings.protocol["fiducial"]["width"]*constants.SI_TO_MICRO))
        self.depth_fiducial.setValue((self.settings.protocol["fiducial"]["depth"]*constants.SI_TO_MICRO))
        self.current_fiducial.setValue((self.settings.protocol["fiducial"]["milling_current"]*constants.SI_TO_NANO))
        self.presetComboBox_fiducial.setCurrentText(self.settings.protocol["fiducial"].get("preset", None))
        self.stage_lamella.setCurrentText("1. Rough Cut")
        self.select_stage()
        self.micro_exp_width.setValue((self.settings.protocol["microexpansion"]["width"]*constants.SI_TO_MICRO))
        self.micro_exp_height.setValue((self.settings.protocol["microexpansion"]["height"]*constants.SI_TO_MICRO))
        self.micro_exp_distance.setValue((self.settings.protocol["microexpansion"]["distance"]*constants.SI_TO_MICRO))

        if isinstance(self.microscope, ThermoMicroscope):
            if self.comboBoxapplication_file.findText(self.settings.protocol["application_file"]) == -1:
                napari.utils.notifications.show_warning("Application file not available, setting to Si instead")
                self.settings.protocol["application_file"] = "Si"
            self.comboBoxapplication_file.setCurrentText(self.settings.protocol["application_file"])

        if self.comboBox_current_alignment.count() == 0:
            self.comboBox_current_alignment.addItems(["Imaging Current","Milling Current"])

        protocol_alignment_current = self.settings.protocol["lamella"]["alignment_current"]

        if protocol_alignment_current.lower() in ["imaging","imaging current","imagingcurrent"]:
            self.comboBox_current_alignment.setCurrentText("Imaging Current")
        elif protocol_alignment_current.lower() in ["milling","milling current","millingcurrent"]:
            self.comboBox_current_alignment.setCurrentText("Milling Current")
        else:
            self.comboBox_current_alignment.setCurrentText("Imaging Current")
        
        # trench
        self.doubleSpinBox_trench_lamella_height.setValue((self.settings.protocol["trench"]["lamella_height"]*constants.SI_TO_MICRO))
        self.doubleSpinBox_trench_lamella_width.setValue((self.settings.protocol["trench"]["lamella_width"]*constants.SI_TO_MICRO))
        self.doubleSpinBox_trench_milling_depth.setValue((self.settings.protocol["trench"]["depth"]*constants.SI_TO_MICRO))
        self.doubleSpinBox_trench_trench_height.setValue((self.settings.protocol["trench"]["trench_height"]*constants.SI_TO_MICRO))
        self.doubleSpinBox_trench_offset.setValue((self.settings.protocol["trench"]["offset"]*constants.SI_TO_MICRO))
        self.doubleSpinBox_trench_size_ratio.setValue((self.settings.protocol["trench"]["size_ratio"]))
        self.doubleSpinBox_trench_milling_current.setValue((self.settings.protocol["trench"]["milling_current"]*constants.SI_TO_NANO))

        # notch
        self.doubleSpinBox_notch_hheight.setValue(self.settings.protocol["notch"]["hheight"] * constants.SI_TO_MICRO)
        self.doubleSpinBox_notch_hwidth.setValue(self.settings.protocol["notch"]["hwidth"] * constants.SI_TO_MICRO)
        self.doubleSpinBox_notch_vheight.setValue(self.settings.protocol["notch"]["vheight"] * constants.SI_TO_MICRO)
        self.doubleSpinBox_notch_vwidth.setValue(self.settings.protocol["notch"]["vwidth"] * constants.SI_TO_MICRO)
        self.doubleSpinBox_notch_depth.setValue(self.settings.protocol["notch"]["depth"] * constants.SI_TO_MICRO)
        self.doubleSpinBox_notch_milling_current.setValue(self.settings.protocol["notch"]["milling_current"] * constants.SI_TO_NANO)
        self.doubleSpinBox_notch_distance.setValue(self.settings.protocol["notch"]["distance"] * constants.SI_TO_MICRO)
        self.checkBox_notch_flip.setChecked(bool(self.settings.protocol["notch"]["flip"]))

        self.draw_patterns()

    def select_stage(self):
        index = self.stage_lamella.currentIndex()
        self.lamella_width.setValue((self.settings.protocol["lamella"]["stages"][index]["lamella_width"]*constants.SI_TO_MICRO))
        self.lamella_height.setValue((self.settings.protocol["lamella"]["stages"][index]["lamella_height"]*constants.SI_TO_MICRO))
        self.trench_height.setValue((self.settings.protocol["lamella"]["stages"][index]["trench_height"]*constants.SI_TO_MICRO))
        self.depth_trench.setValue((self.settings.protocol["lamella"]["stages"][index]["depth"]*constants.SI_TO_MICRO))
        self.offset.setValue((self.settings.protocol["lamella"]["stages"][index]["offset"]*constants.SI_TO_MICRO))
        self.current_lamella.setValue((self.settings.protocol["lamella"]["stages"][index]["milling_current"]*constants.SI_TO_NANO))
        self.size_ratio.setValue((self.settings.protocol["lamella"]["stages"][index]["size_ratio"]))
        self.presetComboBox.setCurrentText(self.settings.protocol["lamella"]["stages"][index].get("preset", None))

    def get_protocol_from_ui(self):
        self.settings.protocol["application_file"] = self.comboBoxapplication_file.currentText()
        self.settings.protocol["lamella"]["beam_shift_attempts"] = float(self.beamshift_attempts.value())
        self.settings.protocol["fiducial"]["height"] = float(self.fiducial_length.value()*constants.MICRO_TO_SI)
        self.settings.protocol["fiducial"]["width"] = float(self.width_fiducial.value()*constants.MICRO_TO_SI)
        self.settings.protocol["fiducial"]["depth"] = float(self.depth_fiducial.value()*constants.MICRO_TO_SI)
        self.settings.protocol["fiducial"]["milling_current"] = float(self.current_fiducial.value()*constants.NANO_TO_SI)
        self.settings.protocol["fiducial"]["preset"] = self.presetComboBox_fiducial.currentText()
        self.settings.protocol["application_file"] = self.comboBoxapplication_file.currentText()

        # TODO: have a toggle to link the lamella width and height for each stages

        self.settings.protocol["lamella"]["lamella_width"] = float(self.lamella_width.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["lamella_height"] = float(self.lamella_height.value()*constants.MICRO_TO_SI)
        
        index = self.stage_lamella.currentIndex()
        
        self.settings.protocol["lamella"]["stages"][index]["lamella_width"] = float(self.lamella_width.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["lamella_height"] = float(self.lamella_height.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["trench_height"] = float(self.trench_height.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["depth"] = float(self.depth_trench.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["offset"] = float(self.offset.value()*constants.MICRO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["milling_current"] = float(self.current_lamella.value()*constants.NANO_TO_SI)
        self.settings.protocol["lamella"]["stages"][index]["size_ratio"] = float(self.size_ratio.value())
        self.settings.protocol["lamella"]["stages"][index]["preset"] = self.presetComboBox.currentText()
        self.settings.protocol["microexpansion"]["width"] = float(self.micro_exp_width.value()*constants.MICRO_TO_SI)
        self.settings.protocol["microexpansion"]["height"] = float(self.micro_exp_height.value()*constants.MICRO_TO_SI)
        self.settings.protocol["microexpansion"]["distance"] = float(self.micro_exp_distance.value()*constants.MICRO_TO_SI)

        self.settings.protocol["lamella"]["alignment_current"] = self.comboBox_current_alignment.currentText().lower()
        

        # trench
        self.settings.protocol["trench"]["lamella_width"] = float(self.doubleSpinBox_trench_lamella_width.value()*constants.MICRO_TO_SI)
        self.settings.protocol["trench"]["lamella_height"] = float(self.doubleSpinBox_trench_lamella_height.value()*constants.MICRO_TO_SI)
        self.settings.protocol["trench"]["trench_height"] = float(self.doubleSpinBox_trench_trench_height.value()*constants.MICRO_TO_SI)
        self.settings.protocol["trench"]["depth"] = float(self.doubleSpinBox_trench_milling_depth.value()*constants.MICRO_TO_SI)
        self.settings.protocol["trench"]["offset"] = float(self.doubleSpinBox_trench_offset.value()*constants.MICRO_TO_SI)
        self.settings.protocol["trench"]["size_ratio"] = float(self.doubleSpinBox_trench_size_ratio.value())
        self.settings.protocol["trench"]["milling_current"] = float(self.doubleSpinBox_trench_milling_current.value()*constants.NANO_TO_SI)
        self.settings.protocol["trench"]["hfw"] = self.image_widget.image_settings.hfw

        # notch
        self.settings.protocol["notch"]["hheight"] =  float(self.doubleSpinBox_notch_hheight.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["hwidth"] =  float(self.doubleSpinBox_notch_hwidth.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["vheight"] =  float(self.doubleSpinBox_notch_vheight.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["vwidth"] =  float(self.doubleSpinBox_notch_vwidth.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["depth"] =  float(self.doubleSpinBox_notch_depth.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["distance"] = float(self.doubleSpinBox_notch_distance.value()*constants.MICRO_TO_SI)
        self.settings.protocol["notch"]["milling_current"] = float(self.doubleSpinBox_notch_milling_current.value()*constants.NANO_TO_SI)
        self.settings.protocol["notch"]["hfw"] = float(self.image_widget.image_settings.hfw)
        self.settings.protocol["notch"]["flip"] = self.checkBox_notch_flip.isChecked()

        self.draw_patterns()
   
    def save_protocol(self):

        fname = _get_save_file_ui(msg="Select protocol file", path=cfg.LOG_PATH)
        if fname == '':
            return
        
        # give protocol path as suffix .yaml if not
        fname = Path(fname).with_suffix(".yaml")

        with open(os.path.join(fname), "w") as f:
            yaml.safe_dump(self.settings.protocol, f, indent=4)

        logging.info("Protocol saved to file")

    ###################################### Imaging ##########################################

    def update_displays(self):

        if self.sender() == self.show_lamella:
            self.checkBox_show_trench.setChecked(False)
        elif self.sender() == self.checkBox_show_trench:
            self.show_lamella.setChecked(False)
       
        if self.show_lamella.isChecked():
            if self.settings.protocol is None:
                logging.info("No protocol loaded")
                return
            patterns: list[list[FibsemPatternSettings]] = [stage.pattern.patterns for stage in self.lamella_stages if stage.pattern is not None]
            patterns.append(self.fiducial_stage.pattern.patterns)
            _draw_patterns_in_napari(
                 self.viewer, self.image_widget.ib_image, self.image_widget.eb_image, patterns
            )

        elif self.checkBox_show_trench.isChecked():
            patterns: list[list[FibsemPatternSettings]] = [stage.pattern.patterns for stage in self.trench_stages if stage.pattern is not None]
            _draw_patterns_in_napari(
                 self.viewer, self.image_widget.ib_image, self.image_widget.eb_image, patterns
            )
        elif self.checkBox_show_notch.isChecked():
            patterns: list[list[FibsemPatternSettings]] = [stage.pattern.patterns for stage in self.notch_stages if stage.pattern is not None]
            _draw_patterns_in_napari(
                 self.viewer, self.image_widget.ib_image, self.image_widget.eb_image, patterns
            )

        else:
            if "Stage 1" in self.viewer.layers:
                self.viewer.layers["Stage 1"].visible = False
            if "Stage 2" in self.viewer.layers:
                self.viewer.layers["Stage 2"].visible = False 
            if "Stage 3" in self.viewer.layers:
                self.viewer.layers["Stage 3"].visible = False
            if "Stage 4" in self.viewer.layers:
                self.viewer.layers["Stage 4"].visible = False

        self.viewer.layers.selection.active = self.image_widget.eb_layer

    def enable_buttons(
        self,
        add: bool = False,
        remove: bool = False,
        fiducial: bool = False,
        go_to: bool = False,
        remill: bool = False,
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

    def update_ui(self):
        if self.image_widget is not None:
            if self.image_widget.ib_image is not None:
                self.update_displays() # THIS is redundant?
                self.show_lamella.setEnabled(True)
                self.checkBox_show_trench.setEnabled(True)

                if self.show_lamella.isChecked() or self.checkBox_show_trench.isChecked() or self.checkBox_show_notch.isChecked():
                    self.draw_patterns()

            else:
                self.enable_buttons()
                self.show_lamella.setEnabled(False)
                self.checkBox_show_trench.setEnabled(False)
                return
        if self.experiment.positions == []:
            self.enable_buttons(add=True)
        else:
            current_lamella = self.experiment.positions[self.lamella_index.currentIndex()]
            if current_lamella.state.stage in [AutoLamellaWaffleStage.Setup, AutoLamellaWaffleStage.ReadyTrench, 
                                               AutoLamellaWaffleStage.MillTrench, AutoLamellaWaffleStage.ReadyLamella]:
                self.enable_buttons(add=True, remove=True, fiducial=False, go_to=True)
            elif current_lamella.state.stage is AutoLamellaWaffleStage.MillFeatures:
                self.enable_buttons(add=True, go_to=True, remill=True)
            elif current_lamella.state.stage is AutoLamellaWaffleStage.Finished:
                self.enable_buttons(add=True, remove=True, go_to=True)
                # add, remove, goto, fiducial = True, True, True, False
                # # TODO: simplify this, remove 'remill fiducial' just allow milling of the fiducial generally 

            if current_lamella.state.stage in [AutoLamellaWaffleStage.Setup, AutoLamellaWaffleStage.MillTrench]:          
                self.pushButton_save_position.setText(f"Save Position")
                self.pushButton_save_position.setStyleSheet("color: white;")
                self.pushButton_save_position.setEnabled(True)
            elif current_lamella.state.stage in [AutoLamellaWaffleStage.ReadyTrench, AutoLamellaWaffleStage.ReadyLamella]:
                self.pushButton_save_position.setText(f"Position Ready")
                self.pushButton_save_position.setStyleSheet("color: white; background-color: green")
                self.pushButton_save_position.setEnabled(True)
            else: 
                self.pushButton_save_position.setText(f"Unavailable Milled")
                self.pushButton_save_position.setStyleSheet("color: white; background-color: gray")
                self.pushButton_save_position.setEnabled(False)


        string_lamella = ""
        for lamella in self.experiment.positions:
            string_lamella += f"Lamella {lamella._name}: \t\t{lamella.state.stage.name}\n"
        self.lamella_count_txt.setPlainText(
            string_lamella
        )
        self.update_image_message()

        return 
        
    def go_to_lamella_ui(self):
        index = self.lamella_index.currentIndex() 
        log_status_message(self.experiment.positions[index], "MOVING_TO_POSITION")
        position = self.experiment.positions[index].state.microscope_state.absolute_position
        self.microscope.move_stage_absolute(position)
        logging.info(f"Moved to position of lamella {self.experiment.positions[index]._name}.")
        log_status_message(self.experiment.positions[index], "MOVE_SUCCESSFUL")
        self.movement_widget.update_ui_after_movement()

    def add_lamella_ui(self):

        if self.image_widget.eb_image == None or self.image_widget.ib_image == None:
            _ = message_box_ui(
                title="No image has been taken.",
                text="Before adding a lamella please take at least one image for each beam.",
                buttons=QMessageBox.Ok,
            )
            return

        self.experiment = add_lamella(microscope=self.microscope, experiment=self.experiment, ref_image=self.image_widget.ib_image)

        pixelsize = self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]
        if len(self.experiment.positions) > 1:
            lamella_position = self.experiment.positions[-2].lamella_centre
            fiducial_position = self.experiment.positions[-2].fiducial_centre
        else:
            lamella_position = self.lamella_position if self.lamella_position is not None else Point(0.0, 0.0)
            fiducial_position = self.fiducial_position if self.fiducial_position is not None else  Point(-((self.image_widget.image_settings.resolution[0] / 3) * pixelsize), 0.0)
        
        lamella_position.x = float(lamella_position.x)
        lamella_position.y = float(lamella_position.y)
        fiducial_position.x = float(fiducial_position.x)
        fiducial_position.y = float(fiducial_position.y)

        self.experiment.positions[-1].lamella_centre = lamella_position
        self.experiment.positions[-1].fiducial_centre = fiducial_position
        self.experiment.positions[-1].trench_centre = lamella_position
        # self.experiment.positions[-1].state.microscope_state = self.microscope.get_current_microscope_state()
        self.experiment.save()
        log_status_message(self.experiment.positions[-1], "LAMELLA_ADDED")
        
        self.lamella_index.addItem(f"{self.experiment.positions[-1]._name}")
        self.lamella_index.setCurrentIndex(self.lamella_index.count() - 1)

        self.update_ui()

    def remove_lamella_ui(self):
        
        if self.experiment.positions[self.lamella_index.currentIndex()].state.stage == AutoLamellaWaffleStage.MillFeatures and self.lamella_saved > 0:
            self.lamella_saved -= 1

        name = self.lamella_index.currentText()
        self.experiment = remove_lamella(self.experiment, self.lamella_index.currentIndex())
        self.lamella_index.clear()

        lamella_names = [lam._name for lam in self.experiment.positions]
        self.lamella_index.addItems(lamella_names)
        self.lamella_index.setCurrentIndex(self.lamella_index.count() - 1)
        self.update_ui()
        self.experiment.save()

    def save_lamella_ui(self):
        self.save_button.setEnabled(False)
        self.save_button.setText("Running...")
        self.save_button.setStyleSheet("color: orange")

        if self.settings.protocol is None:
            _ = message_box_ui(
                title="No protocol.",
                text="Before saving a lamella please load a protocol.",
                buttons=QMessageBox.Ok,
            )
            self.update_ui()
            return
        if len(self.experiment.positions) == 0:
            _ = message_box_ui(
                title="No lamella.",
                text="Before saving a lamella please add one to the experiment.",
                buttons=QMessageBox.Ok,
            )
            self.update_ui()
            return

        index = self.lamella_index.currentIndex()

        if self.experiment.positions[index].state.stage != AutoLamellaWaffleStage.Setup:
            response = message_box_ui(
                title="Lamella already defined",
                text="This lamella has already been defined, please move on to next lamella.",
                buttons=QMessageBox.Ok,
            )
            self.update_ui()
            return
        
        hfw = self.image_widget.image_settings.hfw
        trench_height = self.settings.protocol["lamella"]["stages"][2]["trench_height"]
        if trench_height/hfw < cfg.HFW_THRESHOLD:

            response = message_box_ui(
                title="Field width too hight",
                text="The field width is too high for this pattern, please save lamella with lower hfw (take new Ion beam image).",
                buttons=QMessageBox.Ok,
            )
            self.update_ui()
            return

        # check to mill fiducial
        response = message_box_ui(
            title="Begin milling fiducial?",
            text="If you are happy with the placement of the trench and fiducial, press yes.",
        )

        if response:
            
            lamella_position = Point()
            fiducial_position = Point()

            lamella_position.x = float(self.lamella_position.x) if self.lamella_position is not None else 0.0
            lamella_position.y = float(self.lamella_position.y)    if self.lamella_position is not None else 0.0
            fiducial_position.x = float(self.fiducial_position.x)
            fiducial_position.y = float(self.fiducial_position.y)

            if not validate_lamella_placement(self.settings.protocol, lamella_position, self.image_widget.ib_image, self.microexpansionCheckBox.isChecked()):
                _ = message_box_ui(
                    title="Lamella placement invalid",
                    text="The lamella placement is invalid, please move the lamella so it is fully in the image.",
                    buttons=QMessageBox.Ok,
                )
                self.update_ui()

                return
        
            self.experiment.positions[index].lamella_centre = lamella_position
            self.experiment.positions[index].fiducial_centre = fiducial_position
            self.mill_fiducial_ui(index)
        self.update_ui()

    def _clickback(self, layer, event):
        if event.button == 2 :
            coords = self.image_widget.ib_layer.world_to_data(event.position)

            hfw = self.image_widget.image_settings.hfw
            pixelsize = hfw/self.image_widget.image_settings.resolution[0]

            moveable_trench = [AutoLamellaWaffleStage.Setup]
            moveable_lamella = [AutoLamellaWaffleStage.MillTrench, AutoLamellaWaffleStage.MillFeatures]
            moveable_notch = [AutoLamellaWaffleStage.Setup, AutoLamellaWaffleStage.MillTrench]

            position = conversions.image_to_microscope_image_coordinates(coord = Point(coords[1], coords[0]), image=self.image_widget.ib_image.data, pixelsize=pixelsize)

            # TODO: make sure there is at least one lamella before this, makes the checks much simpler

            if self.comboBox_moving_pattern.currentText() == "Fiducial":
                self.settings.image = self.image_widget.image_settings
                fiducial_length = self.settings.protocol["fiducial"]["height"]
                area, flag = calculate_fiducial_area(self.settings, position, fiducial_length, pixelsize)
                if flag:
                    show_error("The fiducial area is out of the field of view. Please move fiducial closer to centre of image.")
                    return
                if len(self.experiment.positions) != 0 and self.experiment.positions[int(self.lamella_index.currentIndex())].state.stage in moveable_lamella:
                    self.experiment.positions[int(self.lamella_index.currentIndex())].fiducial_centre = deepcopy(position)
                else:
                    self.fiducial_position = position
                logging.info("Moved fiducial")


            if self.comboBox_moving_pattern.currentText()== "Lamella": 
                logging.info("Moved lamella")
                if not validate_lamella_placement(self.settings.protocol, position, self.image_widget.ib_image, self.microexpansionCheckBox.isChecked()):
                    show_error("The lamella is out of the field of view. Please move lamella closer to centre of image.")
                    return
                if len(self.experiment.positions) != 0 and self.experiment.positions[int(self.lamella_index.currentIndex())].state.stage in moveable_lamella:
                    self.experiment.positions[int(self.lamella_index.currentIndex())].lamella_centre = deepcopy(position)
                else:
                    self.lamella_position = position
            
            if self.comboBox_moving_pattern.currentText()== "Trench": 
                logging.info("Moved lamella")
                if not validate_lamella_placement(self.settings.protocol, position, self.image_widget.ib_image, self.microexpansionCheckBox.isChecked(), "trench"):
                    show_error("The lamella is out of the field of view. Please move lamella closer to centre of image.")
                    return
                if len(self.experiment.positions) != 0 and self.experiment.positions[int(self.lamella_index.currentIndex())].state.stage in moveable_trench:
                    self.experiment.positions[int(self.lamella_index.currentIndex())].trench_centre = deepcopy(position)

                else:
                    self.trench_position = position

            if self.comboBox_moving_pattern.currentText()== "Notch": 
                logging.info("Moved lamella")
                # if not validate_lamella_placement(self.settings.protocol, position, self.image_widget.ib_image, self.microexpansionCheckBox.isChecked()):
                #     show_error("The lamella is out of the field of view. Please move lamella closer to centre of image.")
                #     return
                if len(self.experiment.positions) != 0 and self.experiment.positions[int(self.lamella_index.currentIndex())].state.stage in moveable_notch:
                    self.experiment.positions[int(self.lamella_index.currentIndex())].notch_centre = deepcopy(position)

            
            self.viewer.layers.selection.active = self.image_widget.eb_layer
            self.draw_patterns()
            
            self.experiment.save()
            
        return 

    def mill_fiducial_ui(self, index):
        
        self.experiment, flag = save_lamella(
                microscope=self.microscope,
                experiment=self.experiment,
                microscope_settings=self.settings,
                index=index,
                ref_image=deepcopy(self.image_widget.ib_image),
                microexpansion=self.microexpansionCheckBox.isChecked(),
            )

        if flag:
            self.update_ui()
            return
        
        self.experiment.positions[index] = mill_fiducial(
                microscope=self.microscope,
                image_settings=self.image_widget.image_settings,
                lamella=self.experiment.positions[index],
                fiducial_stage = self.fiducial_stage,
            )
        if self.experiment.positions[index].state.stage == AutoLamellaWaffleStage.MillFeatures:
            self.experiment.save()

        self.update_ui()
        self.lamella_saved += 1 

    def can_run_milling(self):
        ## First condition
        if self.microscope is None:
            return False
        ## Second condition
        elif self.experiment is None:
            return False
        ## Third condition
        elif len(self.experiment.positions) == 0:
            return False
        ## Fourth condition
        for lamella in self.experiment.positions:
            if lamella.state.stage.value == 0:
                return False
        # All conditions met
        return True

    def run_autolamella_ui(self):
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")
        self.run_button.setStyleSheet("color: orange")
        response = message_box_ui(
                title="Run full autolamella?.",
                text="If you click yes, all lamellas will be milled automatically.",
            )
        # First check that the pre-requisites to begin milling have been met.
        if self.can_run_milling() == False:
            # check to mill fiducial
            _ = message_box_ui(
                title="Milling Requirements have not been met.",
                text="The following requirements must be met:\n1. Microscope Connected.\n2. Experiment created.\n3. Atleast 1 Lamella saved.\n4. All fiducials milled.",
                buttons=QMessageBox.Ok,
            )
            self.update_ui()
            return
        if response:
            show_info(f"Running AutoLamella...")
            if self.comboBox_current_alignment.currentText() == "Milling Current":
                alignment_current = True
            else:
                alignment_current = False
            self.image_widget.image_settings.reduced_area = None
            self.experiment = run_autolamella(
                microscope=self.microscope,
                experiment=self.experiment,
                microscope_settings=self.settings,
                image_settings=self.image_widget.image_settings,
                current_alignment=alignment_current,
                lamella_stages=self.lamella_stages,
            )
        
        self.update_ui()
        
        self.lamella_finished = len(self.experiment.positions)

        instruction_text = INSTRUCTION_MESSAGES["lamella_milled"].format(self.lamella_finished)

        self.instructions_textEdit.setPlainText(instruction_text)

    def save_current_position(self):

        if self.experiment.positions == []:
            return
        
        index = self.lamella_index.currentIndex()
        # TOGGLE BETWEEN READY AND SETUP
        if self.experiment.positions[index].state.stage is AutoLamellaWaffleStage.Setup:
            self.experiment.positions[index].state.microscope_state = deepcopy(self.microscope.get_current_microscope_state())
            self.experiment.positions[index].state.stage = AutoLamellaWaffleStage.ReadyTrench

            # get current ib image, save as reference
            fname = os.path.join(self.experiment.positions[index].path, "ref_position_ib")
            self.image_widget.ib_image.save(fname)
    
        elif self.experiment.positions[index].state.stage is AutoLamellaWaffleStage.ReadyTrench:
            self.experiment.positions[index].state.stage = AutoLamellaWaffleStage.Setup


        if self.experiment.positions[index].state.stage is AutoLamellaWaffleStage.MillTrench:
            self.experiment.positions[index].state.microscope_state = deepcopy(self.microscope.get_current_microscope_state())
            self.experiment.positions[index].state.stage = AutoLamellaWaffleStage.ReadyLamella

            # get current ib image, save as reference
            fname = os.path.join(self.experiment.positions[index].path, "ref_position_lamella_ib")
            self.image_widget.ib_image.save(fname)
    
        elif self.experiment.positions[index].state.stage is AutoLamellaWaffleStage.ReadyLamella:
            self.experiment.positions[index].state.stage = AutoLamellaWaffleStage.MillTrench

        self.experiment.save()

        self.update_ui()

    def run_waffle_trench(self):

        response = message_box_ui(
            title="Start Waffle Trench milling?",
            text=f"Begin trench milling for {len(self.experiment.positions)} lamellas?",
            buttons=QMessageBox.Ok,
        )

        if response is False:
            return

        logging.info(f"Running waffle trench...")

        microscope = self.microscope
        experiment: Experiment = self.experiment
        settings: MicroscopeSettings = self.settings

        self.experiment = wfl.run_trench_milling(microscope, settings, experiment, parent_ui=self)

        self.update_ui()

        # stats and exit
        stages = Counter([lamella.state.stage for lamella in self.experiment.positions])
        n_trenches = stages[AutoLamellaWaffleStage.MillTrench] 
        n_lamella = len(self.experiment.positions)

        _ = message_box_ui(
                title="Waffle Trenching Complete",
                text=f"{n_trenches} trenches complete. {n_lamella} selected in total. Please continue to undercuts.",
                buttons=QMessageBox.Ok,)
    
    def run_waffle_notch(self):

        logging.info(f"Running waffle trench...")

        microscope = self.microscope
        experiment: Experiment = self.experiment
        microscope_settings: MicroscopeSettings = self.settings

        self.experiment = wfl.run_notch_milling(microscope, microscope_settings, experiment, parent_ui=self)

        self.update_ui()

        # stats and exit
        stages = Counter([lamella.state.stage for lamella in self.experiment.positions])
        n_notches = stages[AutoLamellaWaffleStage.MillFeatures] 
        n_lamella = len(self.experiment.positions)

        _ = message_box_ui(
                title="Waffle Notch Complete",
                text=f"{n_notches} notches complete. {n_lamella} selected in total. Please continue to lamella.",
                buttons=QMessageBox.Ok,)
    
    def run_autolamella_v2(self):
        response = message_box_ui(
            title="Start AutoLamella ?",
            text=f"Begin milling for {len(self.experiment.positions)} lamellas?",
            buttons=QMessageBox.Ok,
        )

        if response is False:
            return

        logging.info(f"Running autolamella...")

        microscope = self.microscope
        experiment: Experiment = self.experiment
        settings: MicroscopeSettings = self.settings

        self.experiment = wfl.run_lamella_milling(microscope, settings, experiment, parent_ui=self)

        self.update_ui()

        # stats and exit
        stages = Counter([lamella.state.stage for lamella in self.experiment.positions])
        n_lamella = stages[AutoLamellaWaffleStage.MillPolishingCut] 
        n_positions = len(self.experiment.positions)

        # TODO: mark finished

        _ = message_box_ui(
                title="Lamella Milling Complete",
                text=f"{n_lamella} lamella complete. {n_positions} selected in total.",
                buttons=QMessageBox.Ok,)


    def splutter_platinum(self):
        _ = message_box_ui(
                title="Not implemented",
                text="This feature has not been implemented yet.",
                buttons=QMessageBox.Ok,
            )


########################## End of Main Window Class ########################################

def add_lamella(microscope: FibsemMicroscope, experiment: Experiment, ref_image: FibsemImage):
    """
    Add an empty lamella to an Experiment and associate it with a reference image.

    Args:
        experiment (Experiment): An instance of the Experiment class representing the current experiment.
        ref_image (FibsemImage): An instance of the FibsemImage class representing the reference image associated with the lamella location.

    Returns:
        None
    """

    index = len(experiment.positions)

    lamella = Lamella(
        path = experiment.path,
        lamella_number=index + 1,
        reference_image=ref_image,
    )

    
    lamella.state.stage = AutoLamellaWaffleStage.Setup
    lamella.state.microscope_state = (
        microscope.get_current_microscope_state()
    )

    lamella.reference_image.metadata.image_settings.label = "Empty_ref"

    experiment.positions.append(deepcopy(lamella))

    logging.info("Empty lamella added to experiment")

    return experiment


def remove_lamella(experiment: Experiment, index: int):
    log_status_message(experiment.positions[index], "REMOVED_LAMELLA")
    experiment.positions.pop(index)
    logging.info("Lamella removed from experiment")
    return experiment


def save_lamella(
    microscope: FibsemMicroscope,
    experiment: Experiment,
    microscope_settings: MicroscopeSettings,
    index: int,
    ref_image: FibsemImage,
    microexpansion: bool,
):
    """
    Saves location and mills fiducial for a given lamella.

    Args:
        microscope (FibsemMicroscope): An instance of the FibsemMicroscope class.
        experiment (Experiment): The current experiment.
        image_settings (ImageSettings): The image settings.
        microscope_settings (MicroscopeSettings): The microscope settings.
        index (int): The index of the selected lamella.
        ref_image (FibsemImage): The image for beam alignment.
        microexpansion (bool): Whether or not to add stress relief cuts.

    Returns:
        Experiment, float: Updated experiment and the pixelsize.
    """
    
    initial_state = LamellaState(
        microscope_state=microscope.get_current_microscope_state(),
        stage=AutoLamellaWaffleStage.Setup,
    )

    pixelsize = ref_image.metadata.pixel_size.x
    fiducial_centre = experiment.positions[index].fiducial_centre
    fiducial_length = microscope_settings.protocol["fiducial"]["height"]

    fiducial_area, flag = calculate_fiducial_area(microscope_settings, fiducial_centre, fiducial_length, pixelsize)
    if flag:
        _ = message_box_ui(
            title = "Fiducial area is invalid",
            text = "The fiducial area is out of the field of view. Please move fiducial closer to centre of image.",
            buttons = QMessageBox.Ok,
            )
        return experiment,flag
    experiment.positions[index].state = initial_state
    experiment.positions[index].reference_image = ref_image
    experiment.positions[index].path = experiment.path
    experiment.positions[index].fiducial_area = fiducial_area
    experiment.positions[index].lamella_number = index + 1
    experiment.positions[index].mill_microexpansion = microexpansion
    experiment.positions[index].history = []

    experiment.save()

    logging.info("Lamella parameters saved")

    return experiment, flag



def calculate_fiducial_area(settings, fiducial_centre, fiducial_length, pixelsize):

    fiducial_centre_area = deepcopy(fiducial_centre)
    fiducial_centre_area.y = fiducial_centre_area.y * -1
    fiducial_centre_px = conversions.convert_point_from_metres_to_pixel(fiducial_centre_area, pixelsize)

    rcx = fiducial_centre_px.x  / settings.image.resolution[0] + 0.5
    rcy = fiducial_centre_px.y / settings.image.resolution[1] + 0.5

    fiducial_length_px = conversions.convert_metres_to_pixels(fiducial_length, pixelsize) * 1.5
    h_offset = fiducial_length_px / settings.image.resolution[0] / 2
    v_offset = fiducial_length_px / settings.image.resolution[1] / 2

    left = rcx - h_offset 
    top =  rcy - v_offset
    width = 2 * h_offset
    height = 2 * v_offset

    if left < 0  or (left + width)> 1 or top < 0 or (top + height) > 1:
        flag = True
    else:
        flag = False
    
    fiducial_area = FibsemRectangle(left, top, width, height)

    return fiducial_area, flag 

def validate_lamella_placement(protocol, lamella_centre, ib_image, micro_expansions, pattern="lamella"):

    stages = patterning._get_milling_stages(pattern, protocol, lamella_centre)

    # pattern = TrenchPattern()
    # protocol_trench = protocol["lamella"]["stages"][0]
    # # protocol_trench["lamella_height"] = protocol["lamella"]["lamella_height"]
    # # protocol_trench["lamella_width"] = protocol["lamella"]["stages"][0]["lamella_width"]
    # pattern.define(protocol_trench, lamella_centre)
    
    for pattern_settings in stages[0].pattern.patterns:
        shape = convert_pattern_to_napari_rect(pattern_settings=pattern_settings, image=ib_image)
        resolution = [ib_image.data.shape[1],ib_image.data.shape[0]]
        output = validate_pattern_placement(patterns=shape, resolution=resolution,shape=shape)
        if not output:
            return False
    
    # if micro_expansions :
    #     protocol_micro = protocol["microexpansion"]
    #     protocol_micro["depth"] = protocol["lamella"]["stages"][0]["depth"]
    #     protocol_micro["lamella_width"] = protocol["lamella"]["stages"][0]["lamella_width"]
    #     pattern = MicroExpansionPattern()
    #     pattern.define(protocol_micro, lamella_centre)

    #     for pattern_settings in pattern.patterns:
    #         shape = convert_pattern_to_napari_rect(pattern_settings=pattern_settings, image=ib_image)
    #         resolution = [ib_image.data.shape[1],ib_image.data.shape[0]]
    #         output = validate_pattern_placement(patterns=shape, resolution=resolution,shape=shape)
    #         if not output:
    #             return False

    return True

def mill_fiducial(
    microscope: FibsemMicroscope,
    image_settings: ImageSettings,
    lamella: Lamella,
    fiducial_stage: FibsemMillingStage,
):
    """
    Mill a fiducial

    Args:
        microscope (FibsemMicroscope): An instance of the FibsemMicroscope class.
        microscope_settings (MicroscopeSettings): microscope settings object
        image_settings (ImageSettings): image settings object
        lamella (Lamella): current lamella object
        pixelsize (float): size of pixels in the image

    Returns:
        lamella (Lamella): updated lamella object

    Logs:
        - "Fiducial milled successfully" if successful
        - "Unable to draw/mill the fiducial: {e}" if unsuccessful, where {e} is the error message
    """
   
    try:
        lamella.state.start_timestamp = datetime.timestamp(datetime.now())
        log_status_message(lamella, "MILLING_FIDUCIAL")
        milling.setup_milling(microscope, mill_settings=fiducial_stage.milling)
        milling.draw_patterns(
            microscope,
            fiducial_stage.pattern.patterns,
        )
        milling.run_milling(
            microscope, milling_current=fiducial_stage.milling.milling_current
        )
        milling.finish_milling(microscope)
        lamella.state.end_timestamp = datetime.timestamp(datetime.now())
        lamella = lamella.update(stage=AutoLamellaWaffleStage.MillFeatures)
        log_status_message(lamella, "FIDUCIAL_MILLED_SUCCESSFULLY")
        image_settings.reduced_area = lamella.fiducial_area
        lamella.path = os.path.join(lamella.path, f"{str(lamella.lamella_number).rjust(2, '0')}-{lamella._petname}")
        image_settings.save_path = lamella.path
        image_settings.label = "milled_fiducial"
        image_settings.save = True
        reference_image = acquire.take_reference_images(microscope, image_settings)
        lamella.reference_image = reference_image[1]
        image_settings.reduced_area = None

        logging.info("Fiducial milled successfully")

    except Exception as e:
        logging.error(f"Unable to draw/mill the fiducial: {traceback.format_exc()}")

    finally:
        return lamella



def run_autolamella(
    microscope: FibsemMicroscope,
    experiment: Experiment,
    microscope_settings: MicroscopeSettings,
    image_settings: ImageSettings,
    current_alignment: bool,
    lamella_stages = list[FibsemMillingStage]
):
    """
    Runs the AutoLamella protocol. This function iterates over the specified stages and Lamella positions in the `microscope_settings` protocol to mill a lamella for each position.

    Args:
        microscope (FibsemMicroscope): The FibsemMicroscope object representing the microscope to be used for milling.
        experiment (Experiment): The Experiment object representing the experiment where the lamella milling is taking place.
        microscope_settings (MicroscopeSettings): The MicroscopeSettings object containing the parameters for the microscope operation.
        image_settings (ImageSettings): The ImageSettings object containing the parameters for image acquisition.

    Returns:
        Experiment: The updated Experiment object after the successful milling of all the lamella positions specified in the `microscope_settings` protocol.
    """

    _microexpansion_used = any([stage for stage in lamella_stages if stage.name == AutoLamellaWaffleStage.MicroExpansion.name])
    success = True 
    lamella: Lamella
    for i, stage in enumerate(
        lamella_stages
    ):
        curr_stage = AutoLamellaWaffleStage[stage.name]

        lamella:Lamella
        for j, lamella in enumerate(experiment.positions):
            
            _COMPLETE_STAGE = False
            if curr_stage is AutoLamellaWaffleStage.RoughCut:
                if not _microexpansion_used: #, check if last stage was fiducial milled
                    if lamella.state.stage is AutoLamellaWaffleStage.MillFeatures:
                        _COMPLETE_STAGE = True
                elif lamella.state.stage is AutoLamellaWaffleStage.MicroExpansion:
                        _COMPLETE_STAGE = True
            elif (lamella.state.stage.value == curr_stage.value - 1):
                _COMPLETE_STAGE = True

            if not _COMPLETE_STAGE:
                continue

            lamella.state.start_timestamp = datetime.timestamp(datetime.now())
            log_status_message(lamella, "MOVING_TO_POSITION")
            microscope.move_stage_absolute(
                lamella.state.microscope_state.absolute_position
            )
            log_status_message(lamella, "MOVE_TO_POSITION_SUCCESSFUL")

            image_settings.save_path = lamella.path
            image_settings.save = True
            image_settings.label = f"start_mill_stage_{i}"
            image_settings.reduced_area = None
            acquire.take_reference_images(microscope, image_settings)
            image_settings.save = False
            

            # alignment
            for _ in range(
                int(microscope_settings.protocol["lamella"]["beam_shift_attempts"])
            ):  
                log_status_message(lamella, "BEAM_ALIGNMENT")
                if current_alignment:
                    if isinstance(microscope, ThermoMicroscope) or isinstance(microscope, DemoMicroscope):
                        microscope.set("current", stage.milling.milling_current, BeamType.ION)
                    elif isinstance(microscope, TescanMicroscope):
                        microscope.set('preset', stage.milling.preset, BeamType.ION)
                image_settings.beam_type = BeamType.ION
                image_settings.reduced_area = lamella.fiducial_area
                beam_shift_alignment(
                    microscope=microscope,
                    image_settings=image_settings,
                    ref_image=lamella.reference_image,
                    reduced_area=lamella.fiducial_area,
                )

            try:
                stage.milling.hfw = lamella.state.microscope_state.ib_settings.hfw
                log_status_message(lamella, F"MILLING_TRENCH")

                milling.setup_milling(
                    microscope,
                    mill_settings=stage.milling,
                )

                # redefine pattern for each lamella
                stage.pattern.define(stage.pattern.protocol, lamella.lamella_centre)

                milling.draw_patterns(
                    microscope=microscope,
                    patterns = stage.pattern.patterns,
                )

                milling.run_milling(
                    microscope, milling_current=stage.milling.milling_current
                )
                milling.finish_milling(microscope)
                lamella.state.end_timestamp = datetime.timestamp(datetime.now())
                image_settings.save_path = lamella.path
                image_settings.reduced_area = None
                log_status_message(lamella, F"MILLING_COMPLETED_SUCCESSFULLY")

                # Update Lamella Stage and Experiment
                lamella = lamella.update(stage=curr_stage)

                # save reference images
                image_settings.save = True
                image_settings.label = f"ref_mill_stage_{i}"
                image_settings.reduced_area = None
                acquire.take_reference_images(microscope, image_settings)

                image_settings.save = False
                
                experiment.save()

                l_stage = stage.name

                logging.info(f"Lamella {j+1}, stage: '{l_stage}' milled successfully.")
                log_status_message(lamella, F"STAGE_COMPLETE")

                success= True; 
            except Exception as e:
                logging.error(
                    f"Unable to draw/mill the lamella: {traceback.format_exc()}"
                )
                lamella.state.stage = AutoLamellaWaffleStage.MillFeatures
                success = False
            finally:
                milling.finish_milling(microscope)


    if success:
        logging.info("All Lamella milled successfully.")
    else:
        logging.info("Lamellas were not milled successfully.")
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.PolishingCut:
            lamella = lamella.update(stage=AutoLamellaWaffleStage.Finished)

    experiment.save()
    
    return experiment


def splutter_platinum(microscope: FibsemMicroscope):
    print("Sputtering Platinum")
    return # PPP: implement for whole_grid, increasing movement + return movement
    protocol = []  #  where do we get this from?

    gis.sputter_platinum(
        microscope=microscope,
        protocol=protocol,
        whole_grid=False,
        default_application_file="Si",
    )

    logging.info("Platinum sputtering complete")


def main():
    
    window = UiInterface(viewer=napari.Viewer())
    widget = window.viewer.window.add_dock_widget(window, area = 'right', add_vertical_stretch=True, name='Autolamella')
    #widget.setMinimumWidth(400)
    napari.run()

if __name__ == "__main__":
    main()
