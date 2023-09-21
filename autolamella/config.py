import os
from pathlib import Path
import autolamella

BASE_PATH: Path = os.path.dirname(__file__)
LOG_PATH: Path = os.path.join(BASE_PATH, 'log')
CONFIG_PATH: Path = os.path.join(BASE_PATH)
PROTOCOL_PATH: Path = os.path.join(BASE_PATH, "protocol", "protocol.yaml")
SYSTEM_PATH: Path = os.path.join(CONFIG_PATH, "system.yaml")
DESKTOP_SHORTCUT_PATH= os.path.dirname(autolamella.__path__[0]) 

EXPERIMENT_NAME = "AutoLamella"
HFW_THRESHOLD = 0.005 # 0.5% of the image height

__AUTOLAMELLA_METHODS__ = ["Autolamella-Default", "Autolamella-Waffle"]#, "Autoliftout-Default", "Autoliftout-Serial-Liftout"]

DEFAULT_PROTOCOL = {

"main_headers" : {
            "name": "autolamella_demo",
            "application_file": "autolamella",
        },

"fiducial_headers" : {
    "height": 10.e-6,
    "width": 1.e-6,
    "depth": 1.0e-6,
    "rotation": 45.0,
    "milling_current": 28.e-9,
    "preset": "30 keV; 20 nA"
},

"lamella_headers" : {
    "alignment_attempts": 3,
    "lamella_width": 10.e-6,
    "lamella_length": 10.e-6,
},

"protocol_stage_1" : {
    "trench_height":10.e-6,
    "depth": 1.e-6,
    "offset": 2.e-6,
    "size_ratio": 1.0,
    "milling_current": 2.e-9,
    "preset": "30 keV; 2.5 nA"
},

"protocol_stage_2" : {
    "trench_height":2.e-6,
    "depth": 1.e-6,
    "offset": 0.5e-6,
    "size_ratio": 1.0,
    "milling_current": 0.74e-9,
    "preset": "30 keV; 2.5 nA"
},

"protocol_stage_3" : {
    "trench_height":0.5e-6,
    "depth": 0.4e-6,
    "offset": 0.0e-6,
    "size_ratio": 1.0,
    "milling_current": 60.0e-12,
    "preset": "30 keV; 2.5 nA"
},

"microexpansion_headers" : {
    "width": 0.5e-6,
    "height": 18.e-6,
    "distance": 10.e-6,
}
}


####### FEATURE FLAGS
_MINIMAP_VISUALISATION = True
_AUTO_SYNC_MINIMAP = True
_REGISTER_METADATA = True