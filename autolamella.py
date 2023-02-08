import sys
import re
from pathlib import Path
from dataclasses import dataclass
from fibsem.structures import BeamType, FibsemImage, FibsemStagePosition
import UI
from fibsem import utils, acquire
import fibsem.movement as movement
from fibsem.structures import BeamType, FibsemImage, FibsemStagePosition, Point, MicroscopeState, FibsemRectangle
import fibsem.conversions as conversions
from enum import Enum
import os
import tkinter
from tkinter import filedialog
import fibsem.constants as constants
from qtpy import QtWidgets
from PyQt5.QtCore import QTimer
import numpy as np
import logging
import napari

class MovementMode(Enum):
    Stable = 1
    Eucentric = 2
    # Needle = 3

class MovementType(Enum):
    StableEnabled = 0 
    EucentricEnabled = 1
    TiltEnabled = 2

@dataclass
class Lamella:
    state: MicroscopeState
    reference_image: FibsemImage
    path: Path
    fiducial_centre: Point
    fiducial_area: FibsemRectangle
    lamella_centre: Point
    lamella_area: FibsemRectangle


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

        # Gamma and Image Settings

        self.FIB_IB = FibsemImage(data=np.zeros((1536,1024), dtype=np.uint8))
        self.FIB_EB = FibsemImage(data=np.zeros((1536,1024), dtype=np.uint8))

        self.CLog8.setText("Welcome to OpenFIBSEM! Begin by Connecting to a Microscope")

        # Initialise microscope object
        self.microscope = None
        self.microscope_settings = None
        self.connect_to_microscope()
        
        if self.microscope is not None:
            self.reset_ui_settings()
            self.update_displays()


        ### NAPARI settings and initialisation

        
        viewer.grid.enabled = True


    def setup_connections(self):

        # Buttons setup

        self.ConnectButton.clicked.connect(self.connect_to_microscope)
        self.DisconnectButton.clicked.connect(self.disconnect_from_microscope)
        self.RefImage.clicked.connect(self.take_reference_images)

        # Movement controls setup
  
   
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
        self.image_settings.hfw = self.hfw_box.value() / 1.0e6

           

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
        self.ResetImage.setEnabled(False)
        self.take_image.setEnabled(False)
        self.save_button.setEnabled(False)
        self.move_rel_button.setEnabled(False)
        self.move_abs_button.setEnabled(False)
        logging.info('Microscope Disconnected')
        self.microscope_status.setText("Microscope Disconnected")
        self.microscope_status.setStyleSheet("background-color: red")


###################################### Imaging ##########################################

    def take_reference_images(self):
        
        # take image with both beams
        eb_image, ib_image = acquire.take_reference_images(self.microscope, self.image_settings)

        self.FIB_IB = ib_image
        self.FIB_EB = eb_image

        logging.info("Reference Images Taken")
        
        self.update_displays()

    def update_displays(self):
       
        viewer.layers.clear()
        self.ib_layer = viewer.add_image(self.FIB_IB.data, name="IB Image")
        self.eb_layer = viewer.add_image(self.FIB_EB.data, name="EB Image")
      
        viewer.camera.zoom = 0.4

        self.ib_layer.mouse_double_click_callbacks.append(self._double_click)
        self.eb_layer.mouse_double_click_callbacks.append(self._double_click)
        viewer.layers.selection.active = self.eb_layer
        viewer.window.qt_viewer.dockLayerList.hide()

        self.reset_ui_settings()


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
 