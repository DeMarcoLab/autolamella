
import logging
import os
import re
import sys
import tkinter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, simpledialog

import fibsem.constants as constants
import fibsem.conversions as conversions
import fibsem.GIS as gis
import fibsem.milling as milling
import fibsem.movement as movement
import napari
import numpy as np
from fibsem import acquire, utils
from fibsem.structures import (BeamType, FibsemImage, FibsemMillingSettings,
                               FibsemPatternSettings, FibsemRectangle,
                               FibsemStagePosition, MicroscopeState, Point)
from fibsem.alignment import beam_shift_alignment
from fibsem.ui.utils import _draw_patterns_in_napari, message_box_ui
from PyQt5.QtCore import QTimer
from qtpy import QtWidgets

import traceback

import UI as UI
from structures import (AutoLamellaStage, Experiment, Lamella, LamellaState,
                        MovementMode, MovementType)
from PyQt5.QtWidgets import QMessageBox


class MainWindow(QtWidgets.QMainWindow, UI.Ui_MainWindow):
    def __init__(self,*args,obj=None,**kwargs) -> None:
        super(MainWindow,self).__init__(*args,**kwargs)
        self.setupUi(self)

        # setting up ui 
        self.setup_connections()
        self.lines = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_log)
        self.timer.start(1000)
        
        self.pattern_settings = []
        self.save_path = None
        

        self.CLog8.setText("Welcome to OpenFIBSEM AutoLamella! Begin by Connecting to a Microscope")

        # Initialise microscope object
        self.microscope = None
        self.microscope_settings = None
        self.connect_to_microscope()

        # Gamma and Image Settings
        self.FIB_IB = FibsemImage(data=np.zeros((self.image_settings.resolution[0], self.image_settings.resolution[1]), dtype=np.uint8))
        self.FIB_EB = FibsemImage(data=np.zeros((self.image_settings.resolution[0], self.image_settings.resolution[1]), dtype=np.uint8))
        
        if self.microscope is not None:
            self.reset_ui_settings()
            self.update_displays()

        self.draw_patterns(hfw=self.image_settings.hfw)

        ### NAPARI settings and initialisation

    
        viewer.grid.enabled = False

        # Initialise experiment object
        self.experiment: Experiment = None


    def setup_connections(self):

        # Buttons setup
   
        self.RefImage.clicked.connect(self.take_reference_images)
        self.show_lamella.stateChanged.connect(self.update_displays)
        self.hfw_box.valueChanged.connect(self.hfw_box_change)
        self.add_button.clicked.connect(self.add_lamella)
        self.run_button.clicked.connect(self.run_autolamella)
        self.platinum.triggered.connect(self.splutter_platinum)
        self.create_exp.triggered.connect(self.create_experiment)
        self.load_exp.triggered.connect(self.load_experiment)
        self.save_button.clicked.connect(self.save_lamella)
        self.tilt_button.clicked.connect(self.tilt_stage)
        self.go_to_lamella.clicked.connect(self.move_to_position)


        # Movement controls setup
  
    def tilt_stage(self):
        position = self.microscope.get_stage_position()
        position.t = self.microscope_settings.protocol["stage_tilt"]*constants.DEGREES_TO_RADIANS
        position.r = self.microscope_settings.protocol["stage_rotation"]*constants.DEGREES_TO_RADIANS
        self.microscope.move_stage_absolute(position)
        logging.info(f"Stage moved to r = {position.r}°, t = {position.t}°")

    def splutter_platinum(self):
        print("Sputtering Platinum")
        return
        protocol = [] #  where do we get this from?

        gis.sputter_platinum(
            microscope = self.microscope,
            protocol = protocol,
            whole_grid = False,
            default_application_file = "autolamella",
            )

        logging.info("Platinum sputtering complete")

    def draw_patterns(self, hfw: float):
        # Initialise the Lamella and Fiducial Settings
        self.patterns_protocol = []
        for i, protocol in enumerate(self.microscope_settings.protocol["lamella"]["protocol_stages"]):
            stage = []
            lamella_width = protocol["lamella_width"]
            lamella_height = protocol["lamella_height"]
            trench_height = protocol["trench_height"]
            upper_trench_height = trench_height / max(protocol["size_ratio"], 1.0)
            offset = protocol["offset"]
            milling_depth = protocol["milling_depth"]

            centre_upper_y = 0 + (lamella_height / 2 + upper_trench_height / 2 + offset)
            centre_lower_y = 0 - (lamella_height / 2 + trench_height / 2 + offset)

            stage.append(FibsemPatternSettings(
                width=lamella_width,
                height=trench_height,
                depth=milling_depth,
                centre_x=0,
                centre_y=centre_lower_y,
            ))

            stage.append(FibsemPatternSettings(
                width=lamella_width,
                height=upper_trench_height,
                depth=milling_depth,
                centre_x=0,
                centre_y=centre_upper_y,
            ))

            self.patterns_protocol.append(stage)

        
        # Fiducial
        stage = []
        protocol = self.microscope_settings.protocol["fiducial"]
        pixelsize = hfw / self.image_settings.resolution[0]
        stage.append(FibsemPatternSettings(
            width=protocol["width"],
            height=protocol["length"],
            depth=protocol["depth"],
            rotation=np.deg2rad(45),
            centre_x= -((self.image_settings.resolution[0]/4) * pixelsize) 
        ))
        stage.append(FibsemPatternSettings(
            width=protocol["width"],
            height=protocol["length"],
            depth=protocol["depth"],
            rotation=np.deg2rad(135),
            centre_x= -((self.image_settings.resolution[0]/4) * pixelsize)
        ))
        self.patterns_protocol.append(stage)

    def create_experiment(self): 

        self.timer.stop()

        if self.save_path is None:
            tkinter.Tk().withdraw()
            folder_path = filedialog.askdirectory()
            self.save_path = folder_path

        self.experiment_name = simpledialog.askstring("Experiment name", "Please enter experiment name")

        self.experiment = Experiment(path = self.save_path,  name = self.experiment_name)
        self.log_path = os.path.join(folder_path, self.experiment_name, "logfile.log")

        # self.timer.timeout.connect(self.update_log)
        self.lines = 0
        self.timer.start(1000)

        logging.info("Experiment created")

    def load_experiment(self): 
        
        self.timer.stop()
        tkinter.Tk().withdraw()
        file_path = filedialog.askopenfilename()
        self.experiment = Experiment.load(file_path)

        folder_path = os.path.dirname(file_path)
        self.log_path = os.path.join(folder_path, "logfile.log")
        self.save_path = folder_path

        # update UI lamella count
        index = len(self.experiment.positions)
        
        self.lamella_count_txt.setText(f"Out of: {index} lamellas") 
        
        self.lines = 0
        self.timer.start(1000)

        logging.info("Experiment loaded")


    def add_lamella(self):
        # Check to see if an image has been taken first
        if self.FIB_EB.metadata == None:
            _ = message_box_ui(
                title="No image has been taken.",
                text="Before adding a lamella please take atleast one image.",
                buttons=QMessageBox.Ok
            )
            return

        index = len(self.experiment.positions)
        lamella = Lamella(
            lamella_number=index +1,
            reference_image=self.FIB_IB,
        )

        lamella.reference_image.metadata.image_settings.label = "Empty ref"

        self.experiment.positions.append(deepcopy(lamella))

         # update UI lamella count
        index = len(self.experiment.positions)
        
        self.lamella_count_txt.setText(f"Out of: {index} lamellas") 
        self.lamella_index.setMaximum(index)

        logging.info("Empty lamella added to experiment")

        return


    def save_lamella(self):

            if self.save_path is None:
                tkinter.Tk().withdraw()
                folder_path = filedialog.askdirectory()
                self.save_path = folder_path

            # check to mill fiducial
            response = message_box_ui(
                title="Begin milling fiducial?",
                text="If you are happy with the placement of the trench and fiducial, press yes.",
            )

            if response:
                pixelsize = self.image_settings.hfw / self.image_settings.resolution[0]
                fiducial_x = float((self.image_settings.resolution[0]/4)*pixelsize)
                initial_state = LamellaState(
                    microscope_state=self.microscope.get_current_microscope_state(),
                    stage=AutoLamellaStage.Setup
                )
                fiducial_area = FibsemRectangle(
                        left=0.25 -float(self.microscope_settings.protocol["fiducial"]["length"]/self.microscope_settings.image.hfw),
                        top=0.5 - float(self.microscope_settings.protocol["fiducial"]["length"]/self.microscope_settings.image.hfw),
                        width=float(self.microscope_settings.protocol["fiducial"]["length"]/self.microscope_settings.image.hfw),
                        height=float(self.microscope_settings.protocol["fiducial"]["length"]/self.microscope_settings.image.hfw)
                )

                index = self.lamella_index.value() - 1

                self.experiment.positions[index].state = initial_state
                self.experiment.positions[index].reference_image = self.FIB_IB
                self.experiment.positions[index].path = self.experiment.path
                self.experiment.positions[index].fiducial_centre = Point(fiducial_x, 0)
                self.experiment.positions[index].fiducial_area = fiducial_area
                self.experiment.positions[index].lamella_centre = Point(0,0)
                self.experiment.positions[index].lamella_number = index + 1
                self.experiment.positions[index].mill_microexpansion = self.microexpansionCheckBox.isChecked()
                self.experiment.positions[index].history = []

                self.experiment.save()

                logging.info("Lamella parameters saved")

                self.mill_fiducial(self.experiment.positions[index], pixelsize)

            else:
                return

    def mill_fiducial(self, lamella: Lamella, pixelsize: float):

        try:
            protocol = self.microscope_settings.protocol["fiducial"]
            fiducial_pattern = FibsemPatternSettings(
                width=protocol["width"],
                height=protocol["length"],
                depth=protocol["depth"],
                centre_x= -((self.image_settings.resolution[0]/4) * pixelsize) 
            )
            fiducial_milling = FibsemMillingSettings(
                milling_current=protocol["milling_current"]
            ) 

            milling.setup_milling(self.microscope, mill_settings = fiducial_milling)
            milling.draw_fiducial(
                self.microscope, 
                fiducial_pattern,
            )
            milling.run_milling(self.microscope, milling_current = fiducial_milling.milling_current)
            milling.finish_milling(self.microscope)

            lamella.state.end_timestamp = datetime.timestamp(datetime.now())
            lamella.history.append(deepcopy(lamella.state))
            lamella.state.stage = AutoLamellaStage.FiducialMilled
            lamella.state.start_timestamp = datetime.timestamp(datetime.now())
            self.image_settings.beam_type = BeamType.ION
            self.image_settings.reduced_area = lamella.fiducial_area
            lamella.reference_image = acquire.new_image(self.microscope, self.image_settings)
            self.image_settings.reduced_area = None 

            lamella.reference_image.metadata.image_settings.label = "milled_fiducial"

            # path_image = os.path.join(self.save_path, str(lamella.lamella_number).rjust(6, '0'), f"milled_fiducial") 

            self.experiment.save()

            logging.info("Fiducial milled successfully")

            

        except Exception as e:
            logging.error(f"Unable to draw/mill the fiducial: {e}")


    def run_autolamella(self):
        # First check that the pre-requisites to begin milling have been met.
        if self.can_run_milling() == False:
            # check to mill fiducial
            _ = message_box_ui(
                title="Milling Requirements have not been met.",
                text="The following requirements must be met:\n1. Microscope Connected.\n2. Experiment created.\n3.Atleast 1 Lamella saved.\n4. All fiducials milled.",
                buttons=QMessageBox.Ok
            )
            return

        lamella: Lamella
        for i, protocol in enumerate(self.microscope_settings.protocol["lamella"]["protocol_stages"]):
            stage = i + 2 # Lamella cuts start at 2 in AutoLamellaStage. Setup=0, FiducialMilled=1, RoughtCut=2,...,etc.
            for j, lamella in enumerate(self.experiment.positions):
                
                if lamella.state.stage == AutoLamellaStage(stage-1): # Checks to make sure the next stage for the selected Lamella is the current protocol
                    self.microscope.move_stage_absolute(lamella.state.microscope_state.absolute_position)
                    logging.info("Moving to lamella position")
                    mill_settings = FibsemMillingSettings(
                        milling_current=protocol["milling_current"]
                    ) 

                    # alignment 
                    for _ in range(self.microscope_settings.protocol["lamella"]["beam_shift_attempts"]):
                        beam_shift_alignment(
                            microscope=self.microscope, 
                            image_settings=self.image_settings, 
                            ref_image=lamella.reference_image, 
                            reduced_area=lamella.fiducial_area)

                    try:

                        milling.setup_milling(self.microscope, application_file = "autolamella", patterning_mode = "Serial", hfw = self.image_settings.hfw, mill_settings = mill_settings)
                        milling.draw_trench(microscope = self.microscope, protocol = protocol, point = lamella.lamella_centre)

                        if stage is AutoLamellaStage.RoughCut and lamella.mill_microexpansion:
                            milling.draw_stress_relief(
                                microscope=self.microscope,
                                microexpansion_protocol=self.microscope_settings.protocol["microexpansion"],
                                lamella_protocol=protocol, 
                            )

                        milling.run_milling(self.microscope, milling_current = protocol["milling_current"])
                        milling.finish_milling(self.microscope)

                        self.microscope_settings.image.save_path = lamella.path
                        self.microscope_settings.image.label = f"ref_mill_stage_{i}"
                        lamella.reference_image = acquire.new_image(self.microscope, self.microscope_settings.image)

                        # Update Lamella Stage and Experiment
                        lamella.state.end_timestamp = datetime.timestamp(datetime.now())
                        lamella.history.append(deepcopy(lamella.state))
                        lamella.state.stage = AutoLamellaStage(stage)
                        lamella.state.start_timestamp = datetime.timestamp(datetime.now())
                        self.image_settings.beam_type = BeamType.ION
                        lamella.reference_image = acquire.new_image(self.microscope, self.image_settings)

                        self.experiment.save()

                        logging.info("Lamella milled successfully")

                    except Exception as e:
                        logging.error(f"Unable to draw/mill the lamella: {traceback.format_exc()}")

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

        
   
########################### Movement Functionality ##########################################

    def get_data_from_coord(self, coords: tuple) -> tuple:

        # check inside image dimensions, (y, x)
        eb_shape = self.FIB_EB.data.shape[0], self.FIB_EB.data.shape[1]
        ib_shape = self.FIB_IB.data.shape[0], self.FIB_IB.data.shape[1] *2

        if (coords[0] > 0 and coords[0] < eb_shape[0]) and (coords[1] > 0 and coords[1] < eb_shape[1]):
            image = self.FIB_EB
            beam_type = BeamType.ELECTRON
            print("electron")

        elif (coords[0] > 0 and coords[0] < ib_shape[0]) and (coords[1] > eb_shape[0] and coords[1] < ib_shape[1]):
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
            napari.utils.notifications.show_info(f"Clicked outside image dimensions. Please click inside the image to move.")
            return

        point = conversions.image_to_microscope_image_coordinates(Point(x=coords[1], y=coords[0]), 
                image.data, image.metadata.pixel_size.x)  
     
        
        # move
        if self.comboBox.currentText() == "Stable Movement":
            self.movement_mode = MovementMode["Stable"]
        elif self.comboBox.currentText() == "Eucentric Movement":
            self.movement_mode = MovementMode["Eucentric"]

        logging.debug(f"Movement: {self.movement_mode.name} | COORD {coords} | SHIFT {point.x:.2e}, {point.y:.2e} | {beam_type}")

        # eucentric is only supported for ION beam
        if beam_type is BeamType.ION and self.movement_mode is MovementMode.Eucentric:
            self.microscope.eucentric_move(
                settings=self.microscope_settings,
                dy=-point.y
            )

        else:
            # corrected stage movement
            self.microscope.stable_move(
                settings=self.microscope_settings,
                dx=point.x,
                dy=point.y,
                beam_type=beam_type,
            )

        self.take_reference_images()


    def move_to_position(self):

        position = self.experiment.positions[self.lamella_index.value()-1].state.microscope_state.absolute_position
        self.microscope.move_stage_absolute(position)
        logging.info(f"Moved to lamella position: {position}")
        self.take_reference_images()



    ################# UI Display helper functions  ###########################################

    def hfw_box_change(self):
        ### field width in microns in UI!!!!!!!!
        self.image_settings.hfw = self.hfw_box.value() * constants.MICRO_TO_SI
        self.draw_patterns(hfw=self.image_settings.hfw)
           

    ##################################################################


    def update_log(self):
        
        with open(self.log_path, "r") as f:
            lines = f.read().splitlines()
            lin_len = len(lines)
            
        if self.lines != lin_len:   
            for i in reversed(range(lin_len - self.lines)):
                line_display = lines[-1-i]
                if re.search("napari.loader — DEBUG", line_display):
                    self.lines = lin_len
                    continue
                line_divided = line_display.split(",")
                time = line_divided[0]
                message = line_divided[1].split("—")
                disp_str = f"{time} | {message[-1]}"

                self.lines = lin_len
                self.CLog.setText(self.CLog2.text())
                self.CLog2.setText(self.CLog3.text())
                self.CLog3.setText(self.CLog4.text())
                self.CLog4.setText(self.CLog5.text())
                self.CLog5.setText(self.CLog6.text())
                self.CLog6.setText(self.CLog7.text())
                self.CLog7.setText(self.CLog8.text())

                self.CLog8.setText(disp_str)
      

    def connect_to_microscope(self):
        
        self.PROTOCOL_PATH = os.path.join(os.path.dirname(__file__), "protocol_autolamella.yaml")

        try:
            self.microscope, self.microscope_settings = utils.setup_session(protocol_path = self.PROTOCOL_PATH)
            print(self.microscope_settings.protocol)
            self.log_path = os.path.join(self.microscope_settings.image.save_path,"logfile.log")
            self.image_settings = self.microscope_settings.image
            self.milling_settings = self.microscope_settings.milling
            logging.info("Microscope Connected")
            self.RefImage.setEnabled(True)
            self.microscope_status.setText("Microscope Connected")
            self.microscope_status.setStyleSheet("background-color: green")

        except:
            # logging.('Unable to connect to microscope')
            self.microscope_status.setText("Microscope Disconnected")
            self.microscope_status.setStyleSheet("background-color: red")
            self.RefImage.setEnabled(False)


    def disconnect_from_microscope(self):

        self.microscope.disconnect()
        self.microscope = None
        self.microscope_settings = None
        self.RefImage.setEnabled(False)
        logging.info('Microscope Disconnected')
        self.microscope_status.setText("Microscope Disconnected")
        self.microscope_status.setStyleSheet("background-color: red")


###################################### Imaging ##########################################

    def take_reference_images(self):
        
        self.image_settings.hfw = self.hfw_box.value()*constants.MICRO_TO_SI
        # take image with both beams
        eb_image, ib_image = acquire.take_reference_images(self.microscope, self.image_settings)

        self.FIB_IB = ib_image
        self.FIB_EB = eb_image

        logging.info("Reference Images Taken")
        
        self.update_displays()

    def update_displays(self):
       
        viewer.layers.clear()
        self.eb_layer = viewer.add_image(self.FIB_EB.data, name="EB Image")
        self.ib_layer = viewer.add_image(self.FIB_IB.data, name="IB Image")
        viewer.camera.center = [0.0,self.image_settings.resolution[1]/2,self.image_settings.resolution[0]]

        viewer.camera.zoom = 0.35

        self.eb_layer.mouse_double_click_callbacks.append(self._double_click)
        self.ib_layer.mouse_double_click_callbacks.append(self._double_click)
        self.ib_layer.translate=[0.0, self.image_settings.resolution[0]]
        
        viewer.window.qt_viewer.dockLayerList.hide()

        if self.show_lamella.isChecked():
            _draw_patterns_in_napari(viewer, self.FIB_IB, self.FIB_EB, self.patterns_protocol)

        #self.reset_ui_settings()
        viewer.layers.selection.active = self.eb_layer

    def save_filepath(self):
        """Opens file explorer to choose location to save image files
        """
        
        tkinter.Tk().withdraw()
        folder_path = filedialog.askdirectory()
        self.label_5.setText(folder_path)
        self.save_path = folder_path

        if self.experiment is not None:
            self.experiment.path = self.save_path

    def reset_ui_settings(self):

        self.hfw_box.setValue(int(self.image_settings.hfw*constants.SI_TO_MICRO))


if __name__ == "__main__":    

    # app = QtWidgets.QApplication(sys.argv)


    viewer = napari.Viewer()


    

    window = MainWindow()
   
    # window.show()
    widget = viewer.window.add_dock_widget(window)
    widget.setMinimumWidth(500)

    napari.run()    

    # sys.exit(app.exec())
 