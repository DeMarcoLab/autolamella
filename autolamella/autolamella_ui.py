import logging
import os
import re
import sys
import tkinter
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, simpledialog
from time import sleep

import fibsem.constants as constants
import fibsem.conversions as conversions
import fibsem.gis as gis
import fibsem.milling as milling
from fibsem.patterning import FibsemMillingStage, MicroExpansionPattern, TrenchPattern, FiducialPattern
import napari
import numpy as np
import yaml
from fibsem import acquire, utils
from fibsem.alignment import beam_shift_alignment
from fibsem.microscope import FibsemMicroscope, TescanMicroscope, ThermoMicroscope, DemoMicroscope
from fibsem.structures import (
    BeamType,
    FibsemImage,
    FibsemMillingSettings,
    FibsemPatternSettings,
    FibsemRectangle,
    MicroscopeSettings,
    Point,
    ImageSettings,
)
from fibsem.ui.utils import _draw_patterns_in_napari, message_box_ui, convert_point_to_napari
from fibsem.ui.FibsemImageSettingsWidget import FibsemImageSettingsWidget
from fibsem.ui.FibsemMovementWidget import FibsemMovementWidget
from fibsem.ui.FibsemSystemSetupWidget import FibsemSystemSetupWidget
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QTextCursor
from qtpy import QtWidgets
from structures import (
    AutoLamellaStage,
    Experiment,
    Lamella,
    LamellaState,
    MovementMode,
    MovementType,
)
import config as cfg

from utils import check_loaded_protocol, INSTRUCTION_MESSAGES

from ui import UI as UI
from napari.utils.notifications import show_info, show_error

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
        self.microscope_settings = None
        #self.connect_to_microscope()

        self.viewer.grid.enabled = False

        # Initialise experiment object
        self.experiment: Experiment = None
        self.protocol_loaded = False
        self.remove_button.setStyleSheet("background-color: transparent")
        self.fiducial_position = None
        self.lamella_position = None
        self.moving_fiducial = False   
        CONFIG_PATH = os.path.join(os.path.dirname(__file__))
        self.system_widget = FibsemSystemSetupWidget(
                microscope=self.microscope,
                settings=self.microscope_settings,
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

        



    def setup_connections(self):
        
        # Buttons setup
        self.show_lamella.stateChanged.connect(self.update_displays)
        self.show_lamella.setEnabled(False)
        self.microexpansionCheckBox.stateChanged.connect(self.draw_patterns)
        self.add_button.clicked.connect(self.add_lamella_ui)
        self.add_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_lamella_ui)
        self.remove_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_autolamella_ui)
        self.platinum.triggered.connect(self.splutter_platinum)
        self.create_exp.triggered.connect(self.create_experiment)
        self.load_exp.triggered.connect(self.load_experiment)
        self.action_load_protocol.triggered.connect(self.load_protocol)
        self.save_button.clicked.connect(self.save_lamella_ui)
        self.save_button.setEnabled(False)
        self.remill_fiducial.clicked.connect(self.remill_fiducial_ui)
        self.remill_fiducial.setEnabled(False)
        self.go_to_lamella.clicked.connect(self.go_to_lamella_ui)
        self.go_to_lamella.setEnabled(False)
        self.lamella_index.valueChanged.connect(self.lamella_index_changed)

        

        


    def connect_protocol_signals(self):
        # Protocol setup
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

    def lamella_index_changed(self):

        if self.lamella_index.value() > 0:

            self.draw_patterns()

            if self.experiment.positions[self.lamella_index.value()-1].state.stage == AutoLamellaStage.Setup:
                self.go_to_lamella.setEnabled(False)
                self.remill_fiducial.setEnabled(False)
                self.save_button.setEnabled(True)
            else:
                self.go_to_lamella.setEnabled(True)
                self.remill_fiducial.setEnabled(True)
                self.save_button.setEnabled(False)
        
        else:

            return


    def draw_patterns(self):
        if self.microscope_settings.protocol is None:
            logging.info("No protocol loaded")
            return
        # Initialise the Lamella and Fiducial Settings
        self.patterns_protocol = []
        pixelsize = self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]
        self.lamella_stages = []
        self.fiducial_stage = None
        ############### Lamella Pattern ################

        default_position_lamella = self.lamella_position if self.lamella_position is not None else Point(0.0, 0.0) # has the user defined a position manually? If not use 0,0
        self.lamella_position = default_position_lamella
        index = self.lamella_index.value() - 1
        if self.experiment is not None and len(self.experiment.positions) > 0: # do we have an experiment with at least one lamella
            if self.experiment.positions[index].state.stage != AutoLamellaStage.Setup: # has the lamella been saved 
                lamella_position = self.experiment.positions[index].lamella_centre
            else:
                lamella_position = default_position_lamella
        else:
            lamella_position = default_position_lamella  

        

        if self.microexpansionCheckBox.isChecked():
            pattern = MicroExpansionPattern()
            protocol = self.microscope_settings.protocol["microexpansion"]
            protocol["depth"] = self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["depth"]
            protocol["milling_current"] = self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["milling_current"]
            protocol["lamella_width"] = self.microscope_settings.protocol["lamella"]["lamella_width"]
            mill_settings = FibsemMillingSettings(
                patterning_mode="Serial",
                application_file=protocol.get("application_file", "autolamella"),
                milling_current=protocol["milling_current"],
                preset = protocol.get("preset", None),
            )
            pattern.define(
                    protocol = protocol,
                    point = lamella_position
                )
            mill_stage = FibsemMillingStage(
                name = "MicroExpansion",
                num = 0,
                milling = mill_settings,
                pattern = pattern,
                point = lamella_position
            )
            self.lamella_stages.append(mill_stage)

        for i, protocol in enumerate(
            self.microscope_settings.protocol["lamella"]["protocol_stages"]
        ):
            protocol["lamella_width"] = self.microscope_settings.protocol["lamella"]["lamella_width"]
            protocol["lamella_height"] = self.microscope_settings.protocol["lamella"]["lamella_height"]
                  
            pattern = TrenchPattern()
            pattern.define(
                    protocol = protocol,
                    point = lamella_position
                )
            mill_settings = FibsemMillingSettings(
                patterning_mode="Serial",
                application_file=self.microscope_settings.protocol.get("application_file", "Si"),
                milling_current=protocol["milling_current"],
                preset = protocol.get("preset", None),
            )
            if i == 0:
                name = "RoughCut"
            elif i == 1:
                name = "RegularCut"
            elif i == 2:
                name = "PolishingCut"

            mill_stage = FibsemMillingStage(
                name = name,
                num = i + 1,
                milling = mill_settings,
                pattern = pattern,
                point = lamella_position
            )

            self.lamella_stages.append(mill_stage)

        ############### Fiducial Pattern ################

        protocol = self.microscope_settings.protocol["fiducial"]

        default_position_fiducial = self.fiducial_position if self.fiducial_position is not None else Point(-self.image_widget.image_settings.resolution[0]/3 * pixelsize, 0.0) # has the user defined a fiducial position?
        self.fiducial_position = default_position_fiducial
        if self.experiment is not None and len(self.experiment.positions) > 0:
                if self.experiment.positions[index].state.stage != AutoLamellaStage.Setup: # if the current lamella has been saved, display relevant pattern 
                    fiducial_position = self.experiment.positions[index].fiducial_centre
                else:
                    fiducial_position = default_position_fiducial
        else:
            fiducial_position = default_position_fiducial
        fiducial_milling = FibsemMillingSettings(
            milling_current=protocol["milling_current"],
            hfw = self.image_widget.image_settings.hfw,
            application_file=self.microscope_settings.protocol.get("application_file", "Si"),
            preset = protocol.get("preset", None),
        )
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
            point = fiducial_position,
        )
        self.fiducial_stage = stage

        self.update_displays()

    def create_experiment(self):

        if self.experiment is not None:
            self.timer.stop()

        self.experiment = None
        self.lamella_count_txt.setPlainText("")
        self.lamella_index.setValue(0)
        self.lamella_index.setMaximum(0)

        tkinter.Tk().withdraw()
        folder_path = filedialog.askdirectory(initialdir = cfg.LOG_PATH, title="Select experiment directory")
        self.save_path = folder_path if folder_path != "" else None

        if folder_path == '':
            logging.info("No path selected, experiment not created")
            return

        name = simpledialog.askstring(
            "Experiment name", "Please enter experiment name"
        )

        if name is None:
            logging.info("No name entered, experiment not created")
            return
        
        self.experiment_name = name
        self.experiment = Experiment(path=self.save_path, name=self.experiment_name)
        self.log_path = os.path.join(self.save_path, self.experiment_name, "logfile.log")

        self.lines = 0
    
        self.add_button.setEnabled(True)

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
            
        
        logging.info("Experiment created")



    def load_experiment(self):
        if self.microscope is not None:
            self.timer.stop()

        self.experiment = None
        self.lamella_count_txt.setPlainText("")
        self.lamella_index.setValue(0)


        tkinter.Tk().withdraw()
        file_path = filedialog.askopenfilename(title="Select experiment directory")
        self.experiment = Experiment.load(file_path) if file_path != '' else self.experiment

        if file_path == '':
            return

        folder_path = os.path.dirname(file_path)
        self.log_path = os.path.join(folder_path, "logfile.log")
        self.save_path = folder_path

        self.lines = 0
        

        self.add_button.setEnabled(True)
        
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
                    if re.search("DEBUG", line_display):
                        self.lines = lin_len
                        continue
                    if re.search("vispy", line_display):
                        self.lines = lin_len
                        continue
                    if re.search("Unknown key", line_display):
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
        self.microscope_settings = self.system_widget.settings
        self.log_path = os.path.join(
            self.microscope_settings.image.save_path, "logfile.log"
        )
        self.image_settings = self.microscope_settings.image
        self.milling_settings = self.microscope_settings.milling
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
                image_settings=self.microscope_settings.image,
                viewer=self.viewer,
            )
        self.movement_widget = FibsemMovementWidget(
            microscope=self.microscope,
            settings=self.microscope_settings,
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

        if len(self.experiment.positions) > 0:
            string_lamella = ""
            for lam in self.experiment.positions:
                self.save_button.setEnabled(True)
                self.go_to_lamella.setEnabled(True)
                if lam.state.stage == AutoLamellaStage.FiducialMilled:
                    self.remill_fiducial.setEnabled(True)
                string_lamella += f"Lamella {lam.lamella_number}-{lam._petname}: {lam.state.stage.name}\n"
            self.lamella_count_txt.setPlainText(
                string_lamella
            )
            self.lamella_index.setMaximum(len(self.experiment.positions))
            self.lamella_index.setMinimum(1)

        
        self.draw_patterns()
        self.update_displays()
        self.image_widget.eb_layer.mouse_drag_callbacks.append(self._clickback)
        self.image_widget.picture_signal.connect(self.update_image_message)

        self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["take_images_message"])

    def update_image_message(self,add=False):

        if self.initial_setup_stage is False:

            self.instructions_textEdit.setPlainText(INSTRUCTION_MESSAGES["add_lamella_message"])

        if add is True or len(self.experiment.positions) > 0:
            

            stages = [lamella.state.stage for lamella in self.experiment.positions]

            from collections import Counter
            stages = Counter(stages)
            self.lamella_finished = stages[AutoLamellaStage.Finished]
            self.lamella_saved = stages[AutoLamellaStage.FiducialMilled]
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
            self.microscope_settings = None
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
        self.microscope_settings.system.stage = self.system_widget.settings.system.stage   
        logging.info("Stage parameters set")  

    


    def load_protocol(self): 
        tkinter.Tk().withdraw()
        protocol_path = filedialog.askopenfilename(initialdir = cfg.BASE_PATH, title="Select protocol file")
        if protocol_path == '':
            return
        
        self.microscope_settings.protocol = utils.load_protocol(
            protocol_path=protocol_path
        ) 

        _THERMO = isinstance(self.microscope, (ThermoMicroscope))
        _TESCAN = isinstance(self.microscope, (TescanMicroscope))
        _DEMO = isinstance(self.microscope, (DemoMicroscope))

        error_returned = check_loaded_protocol(self.microscope_settings.protocol, _THERMO, _TESCAN, _DEMO)

        if error_returned is not None:
            _ = message_box_ui(
                title="Protocol error",
                text=error_returned,
                buttons=QMessageBox.Ok,
            )
            self.protocol_loaded = False
            self.load_protocol()

        self.set_ui_from_protocol() 
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
        return True

    def set_ui_from_protocol(self):

        self.protocol_txt.setText(self.microscope_settings.protocol["name"])
        self.protocol_loaded = True

        ## Loading protocol tab 
        self.beamshift_attempts.setValue((self.microscope_settings.protocol["lamella"]["beam_shift_attempts"]))
        self.fiducial_length.setValue((self.microscope_settings.protocol["fiducial"]["height"]*constants.SI_TO_MICRO))
        self.width_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["width"]*constants.SI_TO_MICRO))
        self.depth_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["depth"]*constants.SI_TO_MICRO))
        self.current_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["milling_current"]*constants.SI_TO_NANO))
        self.presetComboBox_fiducial.setCurrentText(self.microscope_settings.protocol["fiducial"].get("preset", None))
        self.stage_lamella.setCurrentText("1. Rough Cut")
        self.select_stage()
        self.micro_exp_width.setValue((self.microscope_settings.protocol["microexpansion"]["width"]*constants.SI_TO_MICRO))
        self.micro_exp_height.setValue((self.microscope_settings.protocol["microexpansion"]["height"]*constants.SI_TO_MICRO))
        self.micro_exp_distance.setValue((self.microscope_settings.protocol["microexpansion"]["distance"]*constants.SI_TO_MICRO))

        if isinstance(self.microscope, ThermoMicroscope):
            self.comboBoxapplication_file.setCurrentText(self.microscope_settings.protocol["application_file"])

        if self.comboBox_current_alignment.count() == 0:
            self.comboBox_current_alignment.addItems(["Imaging Current","Milling Current"])

        protocol_alignment_current = self.microscope_settings.protocol["lamella"]["alignment_current"]

        if protocol_alignment_current.lower() in ["imaging","imaging current","imagingcurrent"]:
            self.comboBox_current_alignment.setCurrentText("Imaging Current")
        elif protocol_alignment_current.lower() in ["milling","milling current","millingcurrent"]:
            self.comboBox_current_alignment.setCurrentText("Milling Current")
        else:
            self.comboBox_current_alignment.setCurrentText("Imaging Current")
        
       
        logging.info("Protocol loaded")


        self.draw_patterns()

    def select_stage(self):
        index = self.stage_lamella.currentIndex()
        self.lamella_width.setValue((self.microscope_settings.protocol["lamella"]["lamella_width"]*constants.SI_TO_MICRO))
        self.lamella_height.setValue((self.microscope_settings.protocol["lamella"]["lamella_height"]*constants.SI_TO_MICRO))
        self.trench_height.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["trench_height"]*constants.SI_TO_MICRO))
        self.depth_trench.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["depth"]*constants.SI_TO_MICRO))
        self.offset.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["offset"]*constants.SI_TO_MICRO))
        self.current_lamella.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_current"]*constants.SI_TO_NANO))
        self.size_ratio.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["size_ratio"]))
        self.presetComboBox.setCurrentText(self.microscope_settings.protocol["lamella"]["protocol_stages"][index].get("preset", None))

    def get_protocol_from_ui(self):
        self.microscope_settings.protocol["application_file"] = self.comboBoxapplication_file.currentText()
        self.microscope_settings.protocol["lamella"]["beam_shift_attempts"] = float(self.beamshift_attempts.value())
        self.microscope_settings.protocol["fiducial"]["height"] = float(self.fiducial_length.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["width"] = float(self.width_fiducial.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["depth"] = float(self.depth_fiducial.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["milling_current"] = float(self.current_fiducial.value()*constants.NANO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["preset"] = self.presetComboBox_fiducial.currentText()
        self.microscope_settings.protocol["application_file"] = self.comboBoxapplication_file.currentText()

        self.microscope_settings.protocol["lamella"]["lamella_width"] = float(self.lamella_width.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["lamella_height"] = float(self.lamella_height.value()*constants.MICRO_TO_SI)
        

        index = self.stage_lamella.currentIndex()
        
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["trench_height"] = float(self.trench_height.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["depth"] = float(self.depth_trench.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["offset"] = float(self.offset.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_current"] = float(self.current_lamella.value()*constants.NANO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["size_ratio"] = float(self.size_ratio.value())
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["preset"] = self.presetComboBox.currentText()
        self.microscope_settings.protocol["microexpansion"]["width"] = float(self.micro_exp_width.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["microexpansion"]["height"] = float(self.micro_exp_height.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["microexpansion"]["distance"] = float(self.micro_exp_distance.value()*constants.MICRO_TO_SI)

        self.microscope_settings.protocol["lamella"]["alignment_current"] = self.comboBox_current_alignment.currentText().lower()
        
        self.draw_patterns()
   
    def save_protocol(self):
        tkinter.Tk().withdraw()
        protocol_path = filedialog.asksaveasfilename(title="Select protocol file")

        with open(os.path.join(protocol_path), "w") as f:
            yaml.safe_dump(self.microscope_settings.protocol, f, indent=4)

        logging.info("Protocol saved to file")

    ###################################### Imaging ##########################################

    def update_displays(self):
       
        if self.show_lamella.isChecked():
            if self.microscope_settings.protocol is None:
                logging.info("No protocol loaded")
                return
            patterns: list[list[FibsemPatternSettings]] = [stage.pattern.patterns for stage in self.lamella_stages if stage.pattern is not None]
            patterns.append(self.fiducial_stage.pattern.patterns)
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

        
    def save_filepath(self):
        """Opens file explorer to choose location to save image files"""

        tkinter.Tk().withdraw()
        folder_path = filedialog.askdirectory()
        self.label_5.setText(folder_path)
        self.save_path = folder_path

        if self.experiment is not None:
            self.experiment.path = self.save_path

    def go_to_lamella_ui(self):
        index = self.lamella_index.value() -1 
        if self.experiment.positions[index].state.stage == AutoLamellaStage.Setup:
            _ = message_box_ui(
                title="Lamella not saved.",
                text="Please save the lamella before moving to it.",
                buttons=QMessageBox.Ok,
            )
            return
        position = self.experiment.positions[index].state.microscope_state.absolute_position
        self.microscope.move_stage_absolute(position)
        logging.info(f"Moved to position of lamella {index}.")
        self.movement_widget.update_ui()

    def add_lamella_ui(self):
        # check experiemnt has been loaded/created
        self.add_button.setEnabled(False)
        self.add_button.setText("Running...")
        self.add_button.setStyleSheet("color: orange")
        if self.experiment == None:
            _ = message_box_ui(
                title="No experiemnt.",
                text="Before adding a lamella please create or load an experiment.",
                buttons=QMessageBox.Ok,
            )
            self.add_button.setEnabled(True)
            self.add_button.setText("Add Lamella")
            self.add_button.setStyleSheet("color: white")
            return
        # Check to see if an image has been taken first
        if self.image_widget.eb_image == None or self.image_widget.ib_image == None:
            _ = message_box_ui(
                title="No image has been taken.",
                text="Before adding a lamella please take at least one image for each beam.",
                buttons=QMessageBox.Ok,
            )
            self.add_button.setEnabled(True)
            self.add_button.setText("Add Lamella")
            self.add_button.setStyleSheet("color: white")
            return

        self.experiment = add_lamella(experiment=self.experiment, ref_image=self.image_widget.ib_image)

        pixelsize = self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]
        if self.lamella_position is None:
            lamella_position = Point(0.0,0.0)
        else:
            lamella_position = conversions.image_to_microscope_image_coordinates(coord=self.lamella_position, image=self.image_widget.ib_image.data, pixelsize=pixelsize)
        if self.fiducial_position is None:
            fiducial_position = Point(-((self.image_widget.image_settings.resolution[0] / 3) * pixelsize), 0.0)
        else:
            fiducial_position = conversions.image_to_microscope_image_coordinates(coord=self.fiducial_position, image=self.image_widget.ib_image.data, pixelsize=pixelsize)
        
        lamella_position.x = float(lamella_position.x)
        lamella_position.y = float(lamella_position.y)
        fiducial_position.x = float(fiducial_position.x)
        fiducial_position.y = float(fiducial_position.y)

        self.experiment.positions[-1].lamella_centre = lamella_position
        self.experiment.positions[-1].fiducial_centre = fiducial_position


        string_lamella = ""
        for lam in self.experiment.positions:
            string_lamella += f"Lamella {lam.lamella_number:02d}-{lam._petname}: {lam.state.stage.name}\n"
        self.lamella_count_txt.setPlainText(
            string_lamella
        )
        self.lamella_index.setMaximum(len(self.experiment.positions))
        self.lamella_index.setMinimum(1)
        self.add_button.setEnabled(True)
        self.add_button.setText("Add Lamella")
        self.add_button.setStyleSheet("color: white")
        self.save_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        self.remove_button.setStyleSheet("color: white")

        self.update_image_message(add=True)
        

    def remove_lamella_ui(self):
        
        # check experiemnt has been loaded/created
        self.remove_button.setEnabled(False)
        self.remove_button.setText("Running...")
        self.remove_button.setStyleSheet("color: orange")
        if self.experiment == None:
            _ = message_box_ui(
                title="No experiemnt.",
                text="Before adding/removing a lamella please create or load an experiment.",
                buttons=QMessageBox.Ok,
            )
            self.remove_button.setEnabled(True)
            self.remove_button.setText("Remove Lamella")
            self.remove_button.setStyleSheet("color: white")
            return
        # Check to see if an image has been taken first
        if self.image_widget.eb_image == None or self.image_widget.ib_image == None:
            _ = message_box_ui(
                title="No image has been taken.",
                text="Before adding/removing a lamella please take at least one image for each beam.",
                buttons=QMessageBox.Ok,
            )
            self.remove_button.setEnabled(True)
            self.remove_button.setText("Remove Lamella")
            self.remove_button.setStyleSheet("color: white")
            return

        if self.experiment.positions[self.lamella_index.value()-1].state.stage == AutoLamellaStage.FiducialMilled and self.lamella_saved > 0:
            self.lamella_saved -= 1

        self.experiment = remove_lamella(self.experiment, self.lamella_index.value()-1)
        self.lamella_index.setMaximum(len(self.experiment.positions))

        string_lamella = ""
        for i, lam in enumerate(self.experiment.positions):
            lam.lamella_number = i + 1
            string_lamella += f"Lamella {lam.lamella_number}-{lam._petname}: {lam.state.stage.name}\n"

        self.lamella_count_txt.setPlainText(
            string_lamella
        )
        self.experiment.save()
        self.remove_button.setText("Remove Lamella")
        self.remove_button.setStyleSheet("color: white")

        self.remove_button.setEnabled(True) if len(self.experiment.positions) > 0 else self.remove_button.setEnabled(False)


        self.update_image_message(add=False)

        

    def save_lamella_ui(self):
        self.save_button.setEnabled(False)
        self.save_button.setText("Running...")
        self.save_button.setStyleSheet("color: orange")

        if self.microscope_settings.protocol is None:
            _ = message_box_ui(
                title="No protocol.",
                text="Before saving a lamella please load a protocol.",
                buttons=QMessageBox.Ok,
            )
            self.save_button.setEnabled(True)
            self.save_button.setText("Save current lamella")
            self.save_button.setStyleSheet("color: white")
            return
        if len(self.experiment.positions) == 0:
            _ = message_box_ui(
                title="No lamella.",
                text="Before saving a lamella please add one to the experiment.",
                buttons=QMessageBox.Ok,
            )
            self.save_button.setEnabled(True)
            self.save_button.setText("Save current lamella")
            self.save_button.setStyleSheet("color: white")
            return
        if self.save_path is None:
            tkinter.Tk().withdraw()
            folder_path = filedialog.askdirectory()
            self.save_path = folder_path

        index = self.lamella_index.value() - 1

        if self.experiment.positions[index].state.stage != AutoLamellaStage.Setup:
            response = message_box_ui(
                title="Lamella already defined",
                text="This lamella has already been defined, please move on to next lamella.",
                buttons=QMessageBox.Ok,
            )
            self.save_button.setEnabled(True)
            self.save_button.setText("Save current lamella")
            self.save_button.setStyleSheet("color: white")
            return
        
        hfw = self.image_widget.image_settings.hfw
        trench_height = self.microscope_settings.protocol["lamella"]["protocol_stages"][2]["trench_height"]
        if trench_height/hfw < 0.005:
            response = message_box_ui(
                title="Field width too hight",
                text="The field width is too high for this pattern, please save lamella with lower hfw (take new Ion beam image).",
                buttons=QMessageBox.Ok,
            )
            self.save_button.setEnabled(True)
            self.save_button.setText("Save current lamella")
            self.save_button.setStyleSheet("color: white")
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

            pixelsize = hfw/self.image_widget.image_settings.resolution[0]
            if validate_lamella_placement(self.image_widget.image_settings.resolution, self.microscope_settings.protocol, pixelsize, lamella_position):
                _ = message_box_ui(
                    title="Lamella placement invalid",
                    text="The lamella placement is invalid, please move the lamella so it is fully in the image.",
                    buttons=QMessageBox.Ok,
                )
                self.save_button.setEnabled(True)
                self.save_button.setText("Save current lamella")
                self.save_button.setStyleSheet("color: white")
                self.go_to_lamella.setEnabled(False)
                self.remill_fiducial.setEnabled(False)

                return

            self.experiment.positions[index].lamella_centre = lamella_position
            self.experiment.positions[index].fiducial_centre = fiducial_position
            self.mill_fiducial_ui(index)
            self.update_image_message(add=False)


    def _clickback(self, layer, event):
        if event.button == 2 :
            coords = self.image_widget.ib_layer.world_to_data(event.position)


            hfw = self.image_widget.image_settings.hfw
            pixelsize = hfw/self.image_widget.image_settings.resolution[0]

            if self.comboBox_moving_pattern.currentText() == "Fiducial":
                fiducial_position = conversions.image_to_microscope_image_coordinates(coord = Point(coords[1], coords[0]), image=self.image_widget.ib_image.data, pixelsize=(self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]))
                self.microscope_settings.image = self.image_widget.image_settings
                fiducial_length = self.microscope_settings.protocol["fiducial"]["height"]
                area, flag = calculate_fiducial_area(self.microscope_settings, fiducial_position, fiducial_length, pixelsize)
                if flag:
                    show_error("The fiducial area is out of the field of view. Please move fiducial closer to centre of image.")
                    return
                self.fiducial_position = fiducial_position
                logging.info("Moved fiducial")
            else: 
                lamella_position = conversions.image_to_microscope_image_coordinates(coord = Point(coords[1], coords[0]), image=self.image_widget.ib_image.data, pixelsize=(self.image_widget.image_settings.hfw / self.image_widget.image_settings.resolution[0]))
                logging.info("Moved lamella")
                if validate_lamella_placement(self.image_widget.image_settings.resolution, self.microscope_settings.protocol, pixelsize, lamella_position):
                    show_error("The lamella is out of the field of view. Please move lamella closer to centre of image.")
                    return
                self.lamella_position = lamella_position
            self.viewer.layers.selection.active = self.image_widget.eb_layer
            self.draw_patterns()
            
        return 

    def mill_fiducial_ui(self, index):
        
        self.experiment, flag = save_lamella(
                microscope=self.microscope,
                experiment=self.experiment,
                microscope_settings=self.microscope_settings,
                index=index,
                ref_image=deepcopy(self.image_widget.ib_image),
                microexpansion=self.microexpansionCheckBox.isChecked(),
            )

        if flag:
            self.save_button.setEnabled(True)
            self.save_button.setText("Save current lamella")
            self.save_button.setStyleSheet("color: white")
            self.go_to_lamella.setEnabled(False)
            self.remill_fiducial.setEnabled(False)
            return
        
        self.experiment.positions[index] = mill_fiducial(
                microscope=self.microscope,
                microscope_settings=self.microscope_settings,
                image_settings=self.image_widget.image_settings,
                lamella=self.experiment.positions[index],
                fiducial_stage = self.fiducial_stage,
            )
        if self.experiment.positions[index].state.stage == AutoLamellaStage.FiducialMilled:
            self.experiment.save()

        string_lamella = ""
        for lam in self.experiment.positions:
            string_lamella += f"Lamella {lam.lamella_number}-{lam._petname}: {lam.state.stage.name}\n"
  
        self.lamella_count_txt.setPlainText(
            string_lamella
        )
        self.save_button.setEnabled(False)
        self.save_button.setText("Save current lamella")
        self.save_button.setStyleSheet("color: white")
        self.go_to_lamella.setEnabled(True)
        self.remill_fiducial.setEnabled(True)
        self.lamella_saved += 1 


    def remill_fiducial_ui(self):
        self.remill_fiducial.setEnabled(False)
        self.remill_fiducial.setText("Running...")
        self.remill_fiducial.setStyleSheet("color: orange")
        response = message_box_ui(
            title="Redo Fiducial?",
            text="If you want to remill this fiducial, press yes.",
        )
        
        index = self.lamella_index.value() - 1
        if self.experiment.positions[index].state.stage == AutoLamellaStage.Setup:
            _ = message_box_ui(
                title="Fiducial not milled",
                text="You haven't saved this lamella yet, cannot remill fiducial.",
            )
            return
        if response:
            self.experiment.positions[index].state.stage = AutoLamellaStage.Setup
            self.microscope.move_stage_absolute(self.experiment.positions[index].state.microscope_state.absolute_position)
            self.mill_fiducial_ui(index=index)
        self.remill_fiducial.setEnabled(True)
        self.remill_fiducial.setText("Remill fiducial")
        self.remill_fiducial.setStyleSheet("color: white")    

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
                text="The following requirements must be met:\n1. Microscope Connected.\n2. Experiment created.\n3.Atleast 1 Lamella saved.\n4. All fiducials milled.",
                buttons=QMessageBox.Ok,
            )
            self.run_button.setEnabled(True)
            self.run_button.setText("Run Autolamella")
            self.run_button.setStyleSheet("color: white")
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
                microscope_settings=self.microscope_settings,
                image_settings=self.image_widget.image_settings,
                current_alignment=alignment_current,
                stress_relief = self.microexpansionCheckBox.isChecked(),
                lamella_stages=self.lamella_stages,
            )
        
        self.run_button.setEnabled(True)
        self.run_button.setText("Run Autolamella")
        self.run_button.setStyleSheet("background-color: green")
        string_lamella = ""
        for lam in self.experiment.positions:
            string_lamella += f"Lamella {lam.lamella_number}-{lam._petname}: {lam.state.stage.name}\n"
        self.lamella_count_txt.setPlainText(
            string_lamella
        )
        self.lamella_index_changed()

        self.lamella_finished = len(self.experiment.positions)

        instruction_text = INSTRUCTION_MESSAGES["lamella_milled"].format(self.lamella_finished)
        

        self.instructions_textEdit.setPlainText(instruction_text)
        


    def splutter_platinum(self):
        _ = message_box_ui(
                title="Not implemented",
                text="This feature has not been implemented yet.",
                buttons=QMessageBox.Ok,
            )


########################## End of Main Window Class ########################################

def add_lamella(experiment: Experiment, ref_image: FibsemImage):
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
        lamella_number=index + 1,
        reference_image=ref_image,
    )

    lamella.reference_image.metadata.image_settings.label = "Empty_ref"

    experiment.positions.append(deepcopy(lamella))

    logging.info("Empty lamella added to experiment")

    return experiment


def remove_lamella(experiment: Experiment, index: int):
    experiment.positions.pop(index)
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
        stage=AutoLamellaStage.Setup,
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

def validate_lamella_placement(resolution, protocol, pixelsize, lamella_centre):

    lamella_centre_area = deepcopy(lamella_centre)
    lamella_centre_area.y = lamella_centre_area.y * -1
    lamella_centre_px = conversions.convert_point_from_metres_to_pixel(lamella_centre_area, pixelsize)


    rcx = lamella_centre_px.x  / resolution[0] + 0.5
    rcy = lamella_centre_px.y / resolution[1] + 0.5

    half_lamella_height = protocol["lamella"]["protocol_stages"][0]["trench_height"] + protocol["lamella"]["protocol_stages"][0]["offset"] + protocol["lamella"]["lamella_height"]/2
    half_lamella_width = protocol["lamella"]["lamella_width"] / 2

    lamella_length_px = conversions.convert_metres_to_pixels(half_lamella_height, pixelsize)
    lamella_width_px = conversions.convert_metres_to_pixels(half_lamella_width, pixelsize)

    h_offset = lamella_width_px / resolution[0] 
    v_offset = lamella_length_px / resolution[1]

    left = rcx - h_offset 
    top =  rcy - v_offset
    width = 2 * h_offset
    height = 2 * v_offset

    if left < 0  or (left + width)> 1 or top < 0 or (top + height) > 1:
        flag = True
    else:
        flag = False

    return flag 

def mill_fiducial(
    microscope: FibsemMicroscope,
    microscope_settings: MicroscopeSettings,
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
        
        milling.setup_milling(microscope, mill_settings=fiducial_stage.milling)
        milling.draw_patterns(
            microscope,
            fiducial_stage.pattern.patterns,
        )
        milling.run_milling(
            microscope, milling_current=fiducial_stage.milling.milling_current
        )
        milling.finish_milling(microscope)

        lamella = lamella.update(stage=AutoLamellaStage.FiducialMilled)

        image_settings.reduced_area = lamella.fiducial_area
        reference_image = acquire.take_reference_images(microscope, image_settings)
        lamella.reference_image = reference_image[1]

        image_settings.reduced_area = None

        lamella.reference_image.metadata.image_settings.label = "milled_fiducial_ib"
        path_image = os.path.join(lamella.path, str(lamella.lamella_number).rjust(6, '0'),  lamella.reference_image.metadata.image_settings.label)
        reference_image[1].save(path_image)
        path_image = os.path.join(lamella.path, str(lamella.lamella_number).rjust(6, '0'),  "milled_fiducial_eb")
        reference_image[0].save(path_image)

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
    stress_relief: bool,
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
    lamella: Lamella
    for i, stage in enumerate(
        lamella_stages
    ):
        curr_stage =  getattr(AutoLamellaStage, stage.name)  
        for j, lamella in enumerate(experiment.positions):
                
            microscope.move_stage_absolute(
                lamella.state.microscope_state.absolute_position
            )

            image_settings.save_path = os.path.join(lamella.path, str(lamella.lamella_number).rjust(6, '0'))
            image_settings.save = True
            image_settings.label = f"start_mill_stage_{i}"
            image_settings.reduced_area = None
            acquire.take_reference_images(microscope, image_settings)
            image_settings.save = False

            # alignment
            for _ in range(
                int(microscope_settings.protocol["lamella"]["beam_shift_attempts"])
            ):
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

                milling.setup_milling(
                    microscope,
                    mill_settings=stage.milling,
                )
                milling.draw_patterns(
                    microscope=microscope,
                    patterns = stage.pattern.patterns,
                )

                milling.run_milling(
                    microscope, milling_current=stage.milling.milling_current
                )
                milling.finish_milling(microscope)

                image_settings.save_path = lamella.path
                image_settings.reduced_area = None

                # Update Lamella Stage and Experiment
                lamella = lamella.update(stage=curr_stage)

                # save reference images
                image_settings.save = True
                image_settings.label = f"ref_mill_stage_{i}"
                image_settings.save_path = os.path.join(lamella.path, str(lamella.lamella_number).rjust(6, '0'))
                image_settings.reduced_area = None
                acquire.take_reference_images(microscope, image_settings)
                image_settings.save = False
                
                experiment.save()

                l_stage = stage.name

                logging.info(f"Lamella {j+1}, stage: '{l_stage}' milled successfully.")
                success= True; 
            except Exception as e:
                logging.error(
                    f"Unable to draw/mill the lamella: {traceback.format_exc()}"
                )
                lamella.state.stage = AutoLamellaStage.FiducialMilled
                success = False
            finally:
                milling.finish_milling(microscope)
                experiment.save()

    if success:
        logging.info("All Lamella milled successfully.")
    else:
        logging.info("Lamellas were not milled successfully.")
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaStage.PolishingCut:
            lamella = lamella.update(stage=AutoLamellaStage.Finished)

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
