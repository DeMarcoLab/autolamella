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
import napari
import numpy as np
import yaml
from fibsem import acquire, utils
from fibsem.alignment import beam_shift_alignment
from fibsem.microscope import FibsemMicroscope
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
from fibsem.ui.utils import _draw_patterns_in_napari, message_box_ui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
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

from ui import UI as UI
from napari.utils.notifications import show_info


class MainWindow(QtWidgets.QMainWindow, UI.Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs) -> None:
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        # setting up ui
        self.setup_connections()
        self.lines = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_log)
        self.timer.start(1000)

        viewer.window.qt_viewer.dockLayerList.hide()
        viewer.window.qt_viewer.dockLayerControls.hide()

        self.pattern_settings = []
        self.save_path = None

        self.log_txt.setPlainText(
            "Welcome to OpenFIBSEM AutoLamella! Begin by Connecting to a Microscope. \n"
        )

        # Initialise microscope object
        self.microscope = None
        self.microscope_settings = None
        self.connect_to_microscope()

        # Gamma and Image Settings
        self.FIB_IB = FibsemImage(
            data=np.zeros(
                (self.image_settings.resolution[0], self.image_settings.resolution[1]),
                dtype=np.uint8,
            )
        )
        self.FIB_EB = FibsemImage(
            data=np.zeros(
                (self.image_settings.resolution[0], self.image_settings.resolution[1]),
                dtype=np.uint8,
            )
        )

        if self.microscope is not None:
            self.microscope_settings.protocol = None
            self.reset_ui_settings()
            self.update_displays()

        ### NAPARI settings and initialisation

        viewer.grid.enabled = False

        # Initialise experiment object
        self.experiment: Experiment = None
        self.protocol_loaded = False
        pixelsize = self.image_settings.hfw / self.image_settings.resolution[0]
        self.fiducial_position_napari = Point(-((self.image_settings.resolution[0] / 3) * pixelsize), 0.0)
        self.fiducial_position_microscope = Point(float((self.image_settings.resolution[0] / 4) * pixelsize), 0.0)
        self.lamella_position_napari = Point(0.0, 0.0)
        self.lamella_position_microscope = Point(0.0, 0.0)

    def setup_connections(self):
        
        # Buttons setup
        self.RefImage.clicked.connect(self.take_ref_images_ui)
        self.show_lamella.stateChanged.connect(self.update_displays)
        self.hfw_box.valueChanged.connect(self.hfw_box_change)
        self.microexpansionCheckBox.stateChanged.connect(self.draw_patterns)
        self.add_button.clicked.connect(self.add_lamella_ui)
        self.run_button.clicked.connect(self.run_autolamella_ui)
        self.platinum.triggered.connect(self.splutter_platinum)
        self.create_exp.triggered.connect(self.create_experiment)
        self.load_exp.triggered.connect(self.load_experiment)
        self.action_load_protocol.triggered.connect(self.load_protocol)
        self.save_button.clicked.connect(self.save_lamella_ui)
        self.tilt_button.clicked.connect(self.tilt_stage_ui)
        self.go_to_lamella.clicked.connect(self.move_to_position_ui)
        self.remill_fiducial.clicked.connect(self.remill_fiducial_ui)
        self.move_fiducial_button.clicked.connect(self.move_fiducial)
        self.move_lamella_button.clicked.connect(self.move_lamella)

        # Protocol setup
        self.stage_rotation.editingFinished.connect(self.change_protocol)
        self.stage_tilt.editingFinished.connect(self.change_protocol)
        self.beamshift_attempts.editingFinished.connect(self.change_protocol)
        self.fiducial_length.editingFinished.connect(self.change_protocol)
        self.width_fiducial.editingFinished.connect(self.change_protocol)
        self.depth_fiducial.editingFinished.connect(self.change_protocol)
        self.current_fiducial.editingFinished.connect(self.change_protocol)
        self.stage_lamella.currentTextChanged.connect(self.select_stage)
        self.lamella_width.editingFinished.connect(self.change_protocol)
        self.lamella_height.editingFinished.connect(self.change_protocol)
        self.trench_height.editingFinished.connect(self.change_protocol)
        self.depth_trench.editingFinished.connect(self.change_protocol)
        self.offset.editingFinished.connect(self.change_protocol)
        self.current_lamella.editingFinished.connect(self.change_protocol)
        self.size_ratio.editingFinished.connect(self.change_protocol)
        self.export_protocol.clicked.connect(self.save_protocol)
        self.micro_exp_distance.editingFinished.connect(self.change_protocol)
        self.micro_exp_height.editingFinished.connect(self.change_protocol)
        self.micro_exp_width.editingFinished.connect(self.change_protocol)

    def draw_patterns(self):
        if self.microscope_settings.protocol is None:
            logging.info("No protocol loaded")
            return
        # Initialise the Lamella and Fiducial Settings
        hfw = self.image_settings.hfw
        self.patterns_protocol = []
        for i, protocol in enumerate(
            self.microscope_settings.protocol["lamella"]["protocol_stages"]
        ):
            protocol["lamella_width"] = self.microscope_settings.protocol["lamella"]["lamella_width"]
            protocol["lamella_height"] = self.microscope_settings.protocol["lamella"]["lamella_height"]
            stage = []
            
            lower_pattern_settings, upper_pattern_settings = milling.extract_trench_parameters(protocol, self.lamella_position_napari)

            stage.append(
                lower_pattern_settings
            )

            stage.append(
                upper_pattern_settings
            )

            if i == 0 and self.microexpansionCheckBox.isChecked():
                microexpansion_protocol = self.microscope_settings.protocol[
                    "microexpansion"
                ]
                width = microexpansion_protocol["width"]
                height = microexpansion_protocol["height"]
                depth = protocol["milling_depth"]
                lamella_width = protocol["lamella_width"]
                stage.append(
                    FibsemPatternSettings(
                        width=width,
                        height=height,
                        depth=depth,
                        centre_x=self.lamella_position_napari.x
                        - lamella_width / 2
                        - microexpansion_protocol["distance"],
                        centre_y=self.lamella_position_napari.y,
                        cleaning_cross_section=True,
                        scan_direction="LeftToRight",
                    )
                )

                stage.append(
                    FibsemPatternSettings(
                        width=width,
                        height=height,
                        depth=depth,
                        centre_x=self.lamella_position_napari.x
                        + lamella_width / 2
                        + microexpansion_protocol["distance"],
                        centre_y=self.lamella_position_napari.y,
                        cleaning_cross_section=True,
                        scan_direction="RightToLeft",
                    )
                )

            self.patterns_protocol.append(stage)

        # Fiducial
        stage = []
        protocol = self.microscope_settings.protocol["fiducial"]

        centre_fiducial = self.fiducial_position_napari

        stage.append(
            FibsemPatternSettings(
                width=protocol["width"],
                height=protocol["length"],
                depth=protocol["depth"],
                rotation=np.deg2rad(45),
                centre_x=centre_fiducial.x,
                centre_y=centre_fiducial.y,
            )
        )
        stage.append(
            FibsemPatternSettings(
                width=protocol["width"],
                height=protocol["length"],
                depth=protocol["depth"],
                rotation=np.deg2rad(135),
                centre_x=centre_fiducial.x,
                centre_y=centre_fiducial.y,
            )
        )
        self.patterns_protocol.append(stage)

        self.update_displays()

    def create_experiment(self):
        self.timer.stop()

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
        if self.protocol_loaded is False:
            self.load_protocol()

        self.experiment = Experiment(path=self.save_path, name=self.experiment_name)
        self.log_path = os.path.join(self.save_path, self.experiment_name, "logfile.log")

        self.lines = 0
        self.timer.start(1000)

        logging.info("Experiment created")

    def load_experiment(self):
        self.timer.stop()
        tkinter.Tk().withdraw()
        file_path = filedialog.askopenfilename(title="Select experiment directory")
        self.experiment = Experiment.load(file_path) if file_path != '' else self.experiment

        if file_path == '':
            return

        folder_path = os.path.dirname(file_path)
        self.log_path = os.path.join(folder_path, "logfile.log")
        self.save_path = folder_path

        if self.protocol_loaded is False:
            self.load_protocol()
        lamella_ready = 0
        for lam in self.experiment.positions:
            if lam.state.stage == AutoLamellaStage.FiducialMilled:
                lamella_ready += 1

        self.lamella_count_txt.setText(
            f"Out of: {len(self.experiment.positions)} lamellas, lamellas ready: {lamella_ready}"
        )
        self.lamella_index.setMaximum(len(self.experiment.positions))
        self.lamella_index.setMinimum(1)

        self.lines = 0
        self.timer.start(1000)

        logging.info("Experiment loaded")

    ########################### Movement Functionality ##########################################

    def get_data_from_coord(self, coords: tuple) -> tuple:
        # check inside image dimensions, (y, x)
        eb_shape = self.FIB_EB.data.shape[0], self.FIB_EB.data.shape[1]
        ib_shape = self.FIB_IB.data.shape[0], self.FIB_IB.data.shape[1] * 2

        if (coords[0] > 0 and coords[0] < eb_shape[0]) and (
            coords[1] > 0 and coords[1] < eb_shape[1]
        ):
            image = self.FIB_EB
            beam_type = BeamType.ELECTRON
            print("electron")

        elif (coords[0] > 0 and coords[0] < ib_shape[0]) and (
            coords[1] > eb_shape[0] and coords[1] < ib_shape[1]
        ):
            image = self.FIB_IB
            coords = (coords[0], coords[1] - ib_shape[1] // 2)
            beam_type = BeamType.ION
            print("ion")
        else:
            beam_type, image = None, None

        return coords, beam_type, image

    def _double_click(self, layer, event):
        # get coords
        coords = layer.world_to_data(event.position)

        # TODO: dimensions are mixed which makes this confusing to interpret... resolve

        coords, beam_type, image = self.get_data_from_coord(coords)

        if beam_type is None:
            show_info(
                f"Clicked outside image dimensions. Please click inside the image to move."
            )
            return

        point = conversions.image_to_microscope_image_coordinates(
            Point(x=coords[1], y=coords[0]), image.data, image.metadata.pixel_size.x
        )

        # move
        if self.comboBox.currentText() == "Stable Movement":
            self.movement_mode = MovementMode["Stable"]
        elif self.comboBox.currentText() == "Eucentric Movement":
            self.movement_mode = MovementMode["Eucentric"]

        logging.debug(
            f"Movement: {self.movement_mode.name} | COORD {coords} | SHIFT {point.x:.2e}, {point.y:.2e} | {beam_type}"
        )

        # eucentric is only supported for ION beam
        if beam_type is BeamType.ION and self.movement_mode is MovementMode.Eucentric:
            self.microscope.eucentric_move(
                settings=self.microscope_settings, dy=-point.y
            )

        else:
            # corrected stage movement
            self.microscope.stable_move(
                settings=self.microscope_settings,
                dx=point.x,
                dy=point.y,
                beam_type=beam_type,
            )

        self.take_ref_images_ui()

    ################# UI Display helper functions  ###########################################

    def hfw_box_change(self):
        ### field width in microns in UI!!!!!!!!
        self.image_settings.hfw = self.hfw_box.value() * constants.MICRO_TO_SI
        if self.microscope_settings.protocol is not None:
            self.draw_patterns()

    ##################################################################

    def update_log(self):

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
                line_divided = line_display.split(",")
                time = line_divided[0]
                message = line_display.split("—")
                disp_str = f"{time} | {message[-1]}"

                disp_paragraph = self.log_txt.toPlainText() + disp_str + "\n"

                self.lines = lin_len
                self.log_txt.setPlainText(disp_paragraph)

    def connect_to_microscope(self):
        self.CONFIG_PATH = os.path.join(os.path.dirname(__file__))

        try:
            self.microscope, self.microscope_settings = utils.setup_session(
                config_path=self.CONFIG_PATH
            )
            self.log_path = os.path.join(
                self.microscope_settings.image.save_path, "logfile.log"
            )
            self.image_settings = self.microscope_settings.image
            self.milling_settings = self.microscope_settings.milling
            logging.info("Microscope Connected")
            self.RefImage.setEnabled(True)
            self.microscope_status.setText("Microscope Connected")
            self.microscope_status.setStyleSheet("background-color: green")

        except:
            self.microscope_status.setText("Microscope Disconnected")
            self.microscope_status.setStyleSheet("background-color: red")
            self.RefImage.setEnabled(False)

    def disconnect_from_microscope(self):
        self.microscope.disconnect()
        self.microscope = None
        self.microscope_settings = None
        self.RefImage.setEnabled(False)
        logging.info("Microscope Disconnected")
        self.microscope_status.setText("Microscope Disconnected")
        self.microscope_status.setStyleSheet("background-color: red")

    def load_protocol(self):
        tkinter.Tk().withdraw()
        protocol_path = filedialog.askopenfilename(initialdir = cfg.BASE_PATH, title="Select protocol file")
        self.microscope_settings.protocol = utils.load_protocol(
            protocol_path=protocol_path
        ) if protocol_path != '' else self.microscope_settings.protocol

        if protocol_path == '':
            return
        
        self.protocol_txt.setText(self.microscope_settings.protocol["name"])
        self.draw_patterns()
        tilt = self.microscope_settings.protocol["stage_tilt"]
        rotation = self.microscope_settings.protocol["stage_rotation"]
        string = f"Tilt: {tilt}° | Rotation: {rotation}°"
        self.mill_position_txt.setText(string)

        self.protocol_loaded = True

        ## Loading protocol tab 
        self.stage_rotation.setValue((self.microscope_settings.protocol["stage_rotation"]))
        self.stage_tilt.setValue((self.microscope_settings.protocol["stage_tilt"]))
        self.beamshift_attempts.setValue((self.microscope_settings.protocol["lamella"]["beam_shift_attempts"]))
        self.fiducial_length.setValue((self.microscope_settings.protocol["fiducial"]["length"]*constants.SI_TO_MICRO))
        self.width_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["width"]*constants.SI_TO_MICRO))
        self.depth_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["depth"]*constants.SI_TO_MICRO))
        self.current_fiducial.setValue((self.microscope_settings.protocol["fiducial"]["milling_current"]*constants.SI_TO_NANO))
        self.stage_lamella.setCurrentText("1. Rough Cut")
        self.lamella_width.setValue((self.microscope_settings.protocol["lamella"]["lamella_width"]*constants.SI_TO_MICRO))
        self.lamella_height.setValue((self.microscope_settings.protocol["lamella"]["lamella_height"]*constants.SI_TO_MICRO))
        self.trench_height.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["trench_height"]*constants.SI_TO_MICRO))
        self.depth_trench.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["milling_depth"]*constants.SI_TO_MICRO))
        self.offset.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["offset"]*constants.SI_TO_MICRO))
        self.current_lamella.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["milling_current"]*constants.SI_TO_NANO))
        self.size_ratio.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][0]["size_ratio"]))
        self.micro_exp_width.setValue((self.microscope_settings.protocol["microexpansion"]["width"]*constants.SI_TO_MICRO))
        self.micro_exp_height.setValue((self.microscope_settings.protocol["microexpansion"]["height"]*constants.SI_TO_MICRO))
        self.micro_exp_distance.setValue((self.microscope_settings.protocol["microexpansion"]["distance"]*constants.SI_TO_MICRO))
   
        logging.info("Protocol loaded")

    def select_stage(self):
        index = 0 
        if self.stage_lamella.currentText() == "1. Rough Cut":
            index = 0
        elif self.stage_lamella.currentText() == "2. Regular Cut":
            index = 1
        elif self.stage_lamella.currentText() == "3. Polishing Cut":
            index = 2
        self.lamella_width.setValue((self.microscope_settings.protocol["lamella"]["lamella_width"]*constants.SI_TO_MICRO))
        self.lamella_height.setValue((self.microscope_settings.protocol["lamella"]["lamella_height"]*constants.SI_TO_MICRO))
        self.trench_height.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["trench_height"]*constants.SI_TO_MICRO))
        self.depth_trench.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_depth"]*constants.SI_TO_MICRO))
        self.offset.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["offset"]*constants.SI_TO_MICRO))
        self.current_lamella.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_current"]*constants.SI_TO_NANO))
        self.size_ratio.setValue((self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["size_ratio"]))

    def change_protocol(self):
        self.microscope_settings.protocol["stage_rotation"] = float(self.stage_rotation.value())
        self.microscope_settings.protocol["stage_tilt"] = float(self.stage_tilt.value())
        self.microscope_settings.protocol["lamella"]["beam_shift_attempts"] = float(self.beamshift_attempts.value())
        self.microscope_settings.protocol["fiducial"]["length"] = float(self.fiducial_length.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["width"] = float(self.width_fiducial.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["depth"] = float(self.depth_fiducial.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["fiducial"]["milling_current"] = float(self.current_fiducial.value()*constants.NANO_TO_SI)

        self.microscope_settings.protocol["lamella"]["lamella_width"] = float(self.lamella_width.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["lamella_height"] = float(self.lamella_height.value()*constants.MICRO_TO_SI)
        index = 0
        if self.stage_lamella.currentText() == "1. Rough Cut":
            index = 0
        elif self.stage_lamella.currentText() == "2. Regular Cut":
            index = 1
        elif self.stage_lamella.currentText() == "3. Polishing Cut":
            index = 2
        
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["trench_height"] = float(self.trench_height.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_depth"] = float(self.depth_trench.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["offset"] = float(self.offset.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["milling_current"] = float(self.current_lamella.value()*constants.NANO_TO_SI)
        self.microscope_settings.protocol["lamella"]["protocol_stages"][index]["size_ratio"] = float(self.size_ratio.value())
        self.microscope_settings.protocol["microexpansion"]["width"] = float(self.micro_exp_width.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["microexpansion"]["height"] = float(self.micro_exp_height.value()*constants.MICRO_TO_SI)
        self.microscope_settings.protocol["microexpansion"]["distance"] = float(self.micro_exp_distance.value()*constants.MICRO_TO_SI)
        self.draw_patterns()
   
    def save_protocol(self):
        tkinter.Tk().withdraw()
        protocol_path = filedialog.askopenfilename(title="Select protocol file")

        with open(os.path.join(protocol_path), "w") as f:
            yaml.safe_dump(self.microscope_settings.protocol, f, indent=4)

        logging.info("Protocol saved to file")

    ###################################### Imaging ##########################################

    def update_displays(self):
        viewer.layers.clear()
        self.eb_layer = viewer.add_image(self.FIB_EB.data, name="EB Image")
        self.ib_layer = viewer.add_image(self.FIB_IB.data, name="IB Image")
        viewer.camera.center = [
            0.0,
            self.image_settings.resolution[1] / 2,
            self.image_settings.resolution[0],
        ]

        viewer.camera.zoom = 0.5

        self.eb_layer.mouse_double_click_callbacks.append(self._double_click)
        self.ib_layer.mouse_double_click_callbacks.append(self._double_click)
        self.ib_layer.translate = [0.0, self.image_settings.resolution[0]]



        if self.show_lamella.isChecked():
            if self.microscope_settings.protocol is None:
                logging.info("No protocol loaded")
                return
            _draw_patterns_in_napari(
                viewer, self.FIB_IB, self.FIB_EB, self.patterns_protocol
            )

        # self.reset_ui_settings()
        viewer.layers.selection.active = self.eb_layer
        # viewer.window.qt_viewer.view.camera.interactive = False

    def save_filepath(self):
        """Opens file explorer to choose location to save image files"""

        tkinter.Tk().withdraw()
        folder_path = filedialog.askdirectory()
        self.label_5.setText(folder_path)
        self.save_path = folder_path

        if self.experiment is not None:
            self.experiment.path = self.save_path

    def reset_ui_settings(self):
        self.hfw_box.setValue(int(self.image_settings.hfw * constants.SI_TO_MICRO))

    def tilt_stage_ui(self):

        if self.microscope_settings.protocol is None:
            _ = message_box_ui(
                title="No protocol.",
                text="Before milling please load a protocol.",
                buttons=QMessageBox.Ok,
            )
            return
        tilt_stage(self.microscope, self.microscope_settings)



    def take_ref_images_ui(self):
        show_info(f"Taking reference images...")
        eb_image, ib_image = take_reference_images(self.microscope, self.image_settings)
        self.FIB_IB = ib_image
        self.FIB_EB = eb_image
        self.update_displays()


    def move_to_position_ui(self):
        move_to_position(self.microscope, self.experiment, self.lamella_index.value())
        self.take_ref_images_ui()

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
        if self.FIB_EB.metadata == None:
            _ = message_box_ui(
                title="No image has been taken.",
                text="Before adding a lamella please take atleast one image.",
                buttons=QMessageBox.Ok,
            )
            self.add_button.setEnabled(True)
            self.add_button.setText("Add Lamella")
            self.add_button.setStyleSheet("color: white")
            return

        self.experiment = add_lamella(experiment=self.experiment, ref_image=self.FIB_IB)

        self.experiment.positions[-1].lamella_centre = self.lamella_position_microscope
        self.experiment.positions[-1].fiducial_centre = self.fiducial_position_microscope
        
        lamella_ready = 0
        for lam in self.experiment.positions:
            if lam.state.stage == AutoLamellaStage.FiducialMilled:
                lamella_ready += 1

        self.lamella_count_txt.setText(
            f"Out of: {len(self.experiment.positions)} lamellas, lamellas ready: {lamella_ready}"
        )
        self.lamella_index.setMaximum(len(self.experiment.positions))
        self.lamella_index.setMinimum(1)
        self.add_button.setEnabled(True)
        self.add_button.setText("Add Lamella")
        self.add_button.setStyleSheet("color: white")

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
            return
        if len(self.experiment.positions) == 0:
            _ = message_box_ui(
                title="No lamella.",
                text="Before saving a lamella please add one to the experiment.",
                buttons=QMessageBox.Ok,
            )
            return
        if self.save_path is None:
            tkinter.Tk().withdraw()
            folder_path = filedialog.askdirectory()
            self.save_path = folder_path

        index = self.lamella_index.value() - 1

        if (
            self.experiment.positions[index].state.stage
            == AutoLamellaStage.FiducialMilled
        ):
            response = message_box_ui(
                title="Lamella already defined",
                text="This lamella has already been defined, please move on to next lamella.",
                buttons=QMessageBox.Ok,
            )
            return
        # check to mill fiducial
        response = message_box_ui(
            title="Begin milling fiducial?",
            text="If you are happy with the placement of the trench and fiducial, press yes.",
        )

        if response:
            self.experiment.positions[index].fiducial_centre = self.fiducial_position_microscope
            self.experiment.positions[index].lamella_centre = self.lamella_position_microscope
            self.mill_fiducial_ui(index)
        self.save_button.setEnabled(True)
        self.save_button.setText("Save current lamella")
        self.save_button.setStyleSheet("color: white")

    def _clickback_lamella(self, layer, event):
        coords = self.ib_layer.world_to_data(event.position)
        pixel_size = self.image_settings.hfw/self.image_settings.resolution[0]

        #### Thermo has origin top left, tescan is in the middle 
        if self.microscope_settings.system.manufacturer == "Thermo":
            self.lamella_position_microscope = Point(float(coords[1] * pixel_size), float(coords[0] * pixel_size))
        elif self.microscope_settings.system.manufacturer == "Tescan":
            self.lamella_position_microscope = Point(float((coords[1] - self.image_settings.resolution[0]/2) * pixel_size), float((coords[0]-self.image_settings.resolution[1]/2) * pixel_size))
  
        self.lamella_position_napari = Point(float(coords[1] - self.image_settings.resolution[0]/2)* pixel_size, -float(coords[0] - self.image_settings.resolution[1]/2) * pixel_size)
        viewer.layers.selection.active = self.eb_layer
        self.draw_patterns()
        logging.info("Moved lamella")
        
        return 
    
    def _clickback_fiducial(self, layer, event):
        coords = self.ib_layer.world_to_data(event.position)
        pixel_size = self.image_settings.hfw/self.image_settings.resolution[0]

        #### Thermo has origin top left, tescan is in the middle 
        if self.microscope_settings.system.manufacturer == "Thermo":
            self.fiducial_position_microscope = Point(float(coords[1] * pixel_size), float(coords[0] * pixel_size))
        elif self.microscope_settings.system.manufacturer == "Tescan":
            self.fiducial_position_microscope = Point(float((coords[1] - self.image_settings.resolution[0]/2) * pixel_size), float((coords[0]-self.image_settings.resolution[1]/2) * pixel_size))
  
        self.fiducial_position_napari = Point(float(coords[1] - self.image_settings.resolution[0]/2)* pixel_size, -float(coords[0] - self.image_settings.resolution[1]/2) * pixel_size)
        viewer.layers.selection.active = self.eb_layer
        self.draw_patterns()
        logging.info("Moved fiducial")
    
    def move_fiducial(self):

        viewer.layers.selection.active = self.ib_layer
        self.ib_layer.mouse_drag_callbacks.append(self._clickback_fiducial)
        _ = message_box_ui(
            title="Place fiducial.",
            text="Please click once where you want the fiducial to be.",
            buttons=QMessageBox.Ok,
        )

    def move_lamella(self):

            viewer.layers.selection.active = self.ib_layer
            self.ib_layer.mouse_drag_callbacks.append(self._clickback_lamella)
            _ = message_box_ui(
                title="Place lamella.",
                text="Please click once where you want the lamella centre to be.",
                buttons=QMessageBox.Ok,
            )

    def mill_fiducial_ui(self, index):
        
        self.experiment = save_lamella(
                microscope=self.microscope,
                experiment=self.experiment,
                image_settings=self.image_settings,
                microscope_settings=self.microscope_settings,
                index=index,
                ref_image=self.FIB_IB,
                microexpansion=self.microexpansionCheckBox.isChecked(),
            )


        self.experiment.positions[index] = mill_fiducial(
                microscope=self.microscope,
                microscope_settings=self.microscope_settings,
                image_settings=self.image_settings,
                lamella=self.experiment.positions[index],
            )
        if self.experiment.positions[index].state.stage == AutoLamellaStage.FiducialMilled:
            self.experiment.save()

        lamella_ready = 0
        for lam in self.experiment.positions:
            if lam.state.stage == AutoLamellaStage.FiducialMilled:
                lamella_ready += 1
        
        self.lamella_count_txt.setText(
            f"Out of: {len(self.experiment.positions)} lamellas, lamellas ready: {lamella_ready}"
        )

    def remill_fiducial_ui(self):
        self.remill_fiducial.setEnabled(False)
        self.remill_fiducial.setText("Running...")
        self.remill_fiducial.setStyleSheet("color: orange")
        response = message_box_ui(
            title="Redo Fiducial?",
            text="If you want to remill this fiducial, press yes.",
        )
        
        if response:
            index = self.lamella_index.value() - 1
            self.experiment.positions[index].state.stage = AutoLamellaStage.Setup
            self.move_to_position_ui()
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
        _ = message_box_ui(
                title="Run full autolamella?.",
                text="If you click yes, all lamellas will be milled automatically.",
                buttons=QMessageBox.Ok,
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
        show_info(f"Running AutoLamella...")
        self.image_settings.reduced_area = None
        self.experiment = run_autolamella(
            microscope=self.microscope,
            experiment=self.experiment,
            microscope_settings=self.microscope_settings,
            image_settings=self.image_settings,
        )
        self.run_button.setEnabled(True)
        self.run_button.setText("Run Autolamella")
        self.run_button.setStyleSheet("color: white")

    def splutter_platinum(self):
        _ = message_box_ui(
                title="Not implemented",
                text="This feature has not been implemented yet.",
                buttons=QMessageBox.Ok,
            )


########################## End of Main Window Class ########################################


def tilt_stage(microscope: FibsemMicroscope, settings: MicroscopeSettings):
    """
    Tilt the stage of a FibsemMicroscope to a specified angle and rotation using the provided settings.

    Args:
        microscope (FibsemMicroscope): An instance of the FibsemMicroscope class.
        settings (MicroscopeSettings): An instance of the MicroscopeSettings class containing the protocol for the stage tilt and rotation.

    Returns:
        None
    """
    position = microscope.get_stage_position()
    position.t = settings.protocol["stage_tilt"] * constants.DEGREES_TO_RADIANS
    position.r = settings.protocol["stage_rotation"] * constants.DEGREES_TO_RADIANS
    microscope.move_stage_absolute(position)
    logging.info(f"Stage moved to r = {position.r * constants.RADIANS_TO_DEGREES}°, t = {position.t * constants.RADIANS_TO_DEGREES}°")


def take_reference_images(microscope: FibsemMicroscope, image_settings: ImageSettings):
    """
    Acquire reference images using both the electron and ion beams of a FibsemMicroscope, based on the provided ImageSettings.

    Args:
        microscope (FibsemMicroscope): An instance of the FibsemMicroscope class.
        image_settings (ImageSettings): An instance of the ImageSettings class containing the settings for the reference images.

    Returns:
        eb_image, ib_image: Two images, one taken with the electron beam (eb_image) and one taken with the ion beam (ib_image).

    """
    # take image with both beams
    eb_image, ib_image = acquire.take_reference_images(microscope, image_settings)

    logging.info("Reference Images Taken")

    return eb_image, ib_image


def move_to_position(microscope: FibsemMicroscope, experiment: Experiment, index: int):
    """
    Move a FibsemMicroscope to a specified lamella position.

    Args:
        microscope (FibsemMicroscope): An instance of the FibsemMicroscope class.
        experiment (Experiment): An instance of the Experiment class containing the positions to move the microscope to.

    Returns:
        None
    """
    position = experiment.positions[
        index - 1
    ].state.microscope_state.absolute_position
    microscope.move_stage_absolute(position)
    logging.info(f"Moved to lamella position: {position}")


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


def update_lamella(lamella: Lamella, stage: AutoLamellaStage):
    """
    Update the state of a Lamella with a new AutoLamellaStage and add the previous state to the Lamella's history.

    Args:
        lamella (Lamella): An instance of the Lamella class representing the current lamella to be updated.
        stage (AutoLamellaStage): An instance of the AutoLamellaStage class representing the stage of the experiment for the current lamella.

    Returns:
        lamella (Lamella): The updated Lamella class.

    """
    lamella.state.end_timestamp = datetime.timestamp(datetime.now())
    lamella.history.append(deepcopy(lamella.state))
    lamella.state.stage = AutoLamellaStage(stage)
    lamella.state.start_timestamp = datetime.timestamp(datetime.now())
    return lamella


def save_lamella(
    microscope: FibsemMicroscope,
    experiment: Experiment,
    image_settings: ImageSettings,
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
    fiducial_area = FibsemRectangle(
        left=abs(experiment.positions[index].fiducial_centre.x/image_settings.hfw)
        - 1.5
        * float(
            microscope_settings.protocol["fiducial"]["length"] / image_settings.hfw
        ),
        top=abs(experiment.positions[index].fiducial_centre.x/(ref_image.metadata.pixel_size.x*ref_image.metadata.image_settings.resolution[1]))
        - 1.5
        * float(
            microscope_settings.protocol["fiducial"]["length"] / image_settings.hfw
        ),
        width=2.0
        * float(
            microscope_settings.protocol["fiducial"]["length"] / image_settings.hfw
        ),
        height=3.0
        * float(
            microscope_settings.protocol["fiducial"]["length"] / image_settings.hfw
        ),
    )

    experiment.positions[index].state = initial_state
    experiment.positions[index].reference_image = ref_image
    experiment.positions[index].path = experiment.path
    experiment.positions[index].fiducial_area = fiducial_area
    experiment.positions[index].lamella_number = index + 1
    experiment.positions[index].mill_microexpansion = microexpansion
    experiment.positions[index].history = []

    experiment.save()

    logging.info("Lamella parameters saved")

    return experiment


def mill_fiducial(
    microscope: FibsemMicroscope,
    microscope_settings: MicroscopeSettings,
    image_settings: ImageSettings,
    lamella: Lamella,
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
        protocol = microscope_settings.protocol["fiducial"]
        fiducial_pattern = FibsemPatternSettings(
            width=protocol["width"],
            height=protocol["length"],
            depth=protocol["depth"],
            centre_x=lamella.fiducial_centre.x,
            centre_y=lamella.fiducial_centre.y,
        )
        fiducial_milling = FibsemMillingSettings(
            milling_current=protocol["milling_current"]
        )

        milling.setup_milling(microscope, mill_settings=fiducial_milling)
        milling.draw_fiducial(
            microscope,
            fiducial_pattern,
        )
        milling.run_milling(
            microscope, milling_current=fiducial_milling.milling_current
        )
        milling.finish_milling(microscope)

        lamella = update_lamella(lamella=lamella, stage=AutoLamellaStage.FiducialMilled)

        image_settings.beam_type = BeamType.ION
        image_settings.reduced_area = lamella.fiducial_area
        lamella.reference_image = acquire.new_image(microscope, image_settings)
        image_settings.reduced_area = None

        lamella.reference_image.metadata.image_settings.label = "milled_fiducial"

        logging.info("Fiducial milled successfully")

        return lamella

    except Exception as e:
        logging.error(f"Unable to draw/mill the fiducial: {e}")


def run_autolamella(
    microscope: FibsemMicroscope,
    experiment: Experiment,
    microscope_settings: MicroscopeSettings,
    image_settings: ImageSettings,
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
    for i, protocol in enumerate(
        microscope_settings.protocol["lamella"]["protocol_stages"]
    ):
        protocol["lamella_height"] = microscope_settings.protocol["lamella"]["lamella_height"]
        protocol["lamella_width"] = microscope_settings.protocol["lamella"]["lamella_width"]
        curr_stage = (i + 2)  # Lamella cuts start at 2 in AutoLamellaStage. Setup=0, FiducialMilled=1, RoughtCut=2,...,etc.
        for j, lamella in enumerate(experiment.positions):
            if lamella.state.stage == AutoLamellaStage(
                curr_stage - 1
            ):  # Checks to make sure the next stage for the selected Lamella is the current protocol
                microscope.move_stage_absolute(
                    lamella.state.microscope_state.absolute_position
                )
                logging.info("Moving to lamella position")
                mill_settings = FibsemMillingSettings(
                    milling_current=protocol["milling_current"]
                )

                # alignment
                for _ in range(
                    int(microscope_settings.protocol["lamella"]["beam_shift_attempts"])
                ):
                    beam_shift_alignment(
                        microscope=microscope,
                        image_settings=image_settings,
                        ref_image=lamella.reference_image,
                        reduced_area=lamella.fiducial_area,
                    )

                try:
                    mill_settings.hfw = image_settings.hfw
                    milling.setup_milling(
                        microscope,
                        patterning_mode="Serial",
                        mill_settings=mill_settings,
                    )
                    milling.draw_trench(
                        microscope=microscope,
                        protocol=protocol,
                        point=lamella.lamella_centre,
                    )

                    if (
                        curr_stage == 2 and lamella.mill_microexpansion
                    ):  # stage = 2 is RoughCut
                        milling.draw_stress_relief(
                            microscope=microscope,
                            microexpansion_protocol=microscope_settings.protocol[
                                "microexpansion"
                            ],
                            lamella_protocol=protocol,
                        )

                    milling.run_milling(
                        microscope, milling_current=protocol["milling_current"]
                    )
                    milling.finish_milling(microscope)

                    image_settings.save_path = lamella.path
                    image_settings.label = f"ref_mill_stage_{i}"
                    image_settings.reduced_area = None

                    # Update Lamella Stage and Experiment
                    lamella = update_lamella(lamella=lamella, stage=curr_stage)

                    image_settings.beam_type = BeamType.ION
                    reference_image = acquire.new_image(
                        microscope, image_settings
                    )
                    path_image = os.path.join(lamella.path, str(lamella.lamella_number).rjust(6, '0'), image_settings.label)
                    reference_image.save(path_image)

                    experiment.save()
                    if curr_stage == 2:
                        l_stage = "Rough Cut"
                    elif curr_stage == 3:
                        l_stage = "Regular Cut"
                    elif curr_stage == 4:
                        l_stage = "Polishing Cut"
                    logging.info(f"Lamella {j+1}, stage: '{l_stage}' milled successfully.")

                except Exception as e:
                    logging.error(
                        f"Unable to draw/mill the lamella: {traceback.format_exc()}"
                    )
    logging.info("All Lamella milled successfully.")
    return experiment


def splutter_platinum(microscope: FibsemMicroscope):
    print("Sputtering Platinum")
    return
    protocol = []  #  where do we get this from?

    gis.sputter_platinum(
        microscope=microscope,
        protocol=protocol,
        whole_grid=False,
        default_application_file="Si",
    )

    logging.info("Platinum sputtering complete")


if __name__ == "__main__":
    viewer = napari.Viewer()
    window = MainWindow()
    widget = viewer.window.add_dock_widget(window)
    widget.setMinimumWidth(400)
    napari.run()
