
import sys
import re
import UI
from fibsem import utils, acquire
import fibsem.movement as movement
import fibsem.GIS as gis
import fibsem.milling as milling
from fibsem.structures import BeamType, FibsemImage, FibsemStagePosition, Point, MicroscopeState, FibsemRectangle, FibsemPatternSettings, FibsemMillingSettings
from fibsem.ui.utils import _draw_patterns_in_napari, message_box_ui
import fibsem.conversions as conversions
from structures import Lamella, LamellaState, AutoLamellaStage, MovementMode, Experiment

import os
from copy import deepcopy
import tkinter
from tkinter import filedialog
import fibsem.constants as constants
from qtpy import QtWidgets
from PyQt5.QtCore import QTimer
import numpy as np
import logging
from structures import LamellaState, Lamella, MovementMode, MovementType, AutoLamellaStage, Experiment
import napari


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
        self.experiment = Experiment(self.save_path, name = "test")

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

        self.ConnectButton.clicked.connect(self.connect_to_microscope)
        self.DisconnectButton.clicked.connect(self.disconnect_from_microscope)
        self.RefImage.clicked.connect(self.take_reference_images)
        self.show_lamella.stateChanged.connect(self.update_displays)
        self.hfw_box.valueChanged.connect(self.hfw_box_change)
        self.add_lamella_button.clicked.connect(self.add_lamella)
        self.save_path_button.clicked.connect(self.save_filepath)
        self.run_button.clicked.connect(self.run_autolamella)
        self.platinum.clicked.connect(self.splutter_platinum)


        # Movement controls setup
  
    def splutter_platinum(self):
        
        protocol = [] # TODO where do we get this from?

        gis.sputter_platinum(
            microscope = self.microscope,
            protocol = protocol,
            whole_grid = False,
            default_application_file = "autolamella",
            )

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

    def create_experiment(self, path, name):
        return Experiment(path=path, name=name)

    def load_experiment(self, path): 
        return Experiment.load(path)

    def add_lamella(self):

        if self.save_path is None:
            response_save = message_box_ui(
            title="Missing save path",
            text="Please select a save directory for the lamella data. The current lamella will not be saved",
            )
            return

        # check to mill fiducial
        response = message_box_ui(
            title="Begin milling fiducial?",
            text="If you are happy with the placement of the trench of fiducal, press yes.",
        )

        if response:
            pixelsize = self.image_settings.hfw / self.image_settings.resolution[0]
            initial_state = LamellaState(
                micrscope_state=self.microscope.get_current_microscope_state(),
                stage=AutoLamellaStage.Setup
            )
            lamella = Lamella(
                state = initial_state,
                reference_image = self.FIB_IB, # Should this include patterns?
                path = self.save_path, 
                fiducial_centre = Point((self.image_settings.resolution[0]/4)*pixelsize, 0),
                fiducial_area = FibsemRectangle(0,0,0,0), # TODO
                lamella_centre = Point(0,0), # Currently always at centre of image
                lamella_area = FibsemRectangle(0,0,0,0), # TODO 
            )

            index = len(self.experiment.positions)
            self.experiment.positions[index+1] = deepcopy(lamella)

            self.experiment.save() # TODO

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
                    fiducial_milling,
                )
                milling.run_milling(self.microscope, milling_current = fiducial_milling.milling_current) # specify milling current? TODO
                milling.finish_milling(self.microscope)

                lamella.state.stage = AutoLamellaStage.FiducialMilled
                lamella.save()

                # update UI lamella count
                index = int(self.lamella_number.text())
                index = index + 1
                self.lamella_number.setText(str(index)) 

            except Exception as e:
                logging.error(f"Unable to draw/mill the fiducial: {e}")
        else:
            return
    
    def run_autolamella(self):
        
        for i, protocol in enumerate(self.microscope_settings.protocol["lamella"]):
            for lamella in enumerate(self.experiment.positions):

                self.microscope.move_stage_absolute(lamella.state.stage_position)
                logging.info("Moving to lamella position")
                mill_settings = FibsemMillingSettings(
                    milling_current=protocol["milling_current"]
                ) 

                # TODO add alignment stuff

                try:

                    milling.setup_milling(self.microscope, application_file = "autolamella", patterning_mode = "Serial", hfw = self.image_settings.hfw, mill_settings = mill_settings)
                    milling.draw_trench(microscope = self.microscope, protocol = protocol, point = lamella.lamella_centre)
                    milling.run_milling(self.microscope, milling_current = protocol["milling_current"])
                    milling.finish_milling(self.microscope)

                    self.microscope_settings.image.save_path = lamella.path
                    self.microscope_settings.image.label = f"ref_mill_stage_{i}"
                    lamella.reference_image = acquire.new_image(self.microscope, self.microscope_settings.image)
                except Exception as e:
                    logging.error(f"Unable to draw/mill the lamella: {e}")
        
   
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
      

    def move_to_milling_angle(self):

        current_position = self.microscope.get_stage_position()

        stage_position = FibsemStagePosition(
            x=current_position.x,
            y=current_position.y,
            z=current_position.z,
            r=np.deg2rad(self.microscope_settings.protocol["stage_rotation"]),
            t=np.deg2rad(self.microscope_settings.protocol["stage_tilt"])
    )

        self.microscope.move_stage_absolute(stage_position)
        

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
        self.experiment.path = self.save_path

    def reset_ui_settings(self):

        self.hfw_box.setValue(int(self.image_settings.hfw*constants.SI_TO_MICRO))


if __name__ == "__main__":    

    app = QtWidgets.QApplication(sys.argv)


    viewer = napari.Viewer()


    

    window = MainWindow()
   
    # window.show()
    widget = viewer.window.add_dock_widget(window)
    widget.setMinimumWidth(500)

    

    sys.exit(app.exec())
 