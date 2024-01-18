import os
from pathlib import Path
import autolamella

BASE_PATH: Path = os.path.dirname(__file__)
LOG_PATH: Path = os.path.join(BASE_PATH, 'log')
CONFIG_PATH: Path = os.path.join(BASE_PATH)
PROTOCOL_PATH: Path = os.path.join(BASE_PATH, "protocol", "protocol-base.yaml")
SYSTEM_PATH: Path = os.path.join(CONFIG_PATH, "system.yaml")
DESKTOP_SHORTCUT_PATH= os.path.dirname(autolamella.__path__[0]) 

os.makedirs(LOG_PATH, exist_ok=True)

EXPERIMENT_NAME = "AutoLamella"

HFW_THRESHOLD = 0.005 # 0.5% of the image height

__AUTOLAMELLA_METHODS__ = ["Autolamella-Default", "Autolamella-Waffle"]#, "Autoliftout-Default", "Autoliftout-Serial-Liftout"]
__AUTOLIFTOUT_METHODS__ = ["autoliftout-default", "autoliftout-serial-liftout"]
__AUTOLIFTOUT_LIFTOUT_JOIN_METHODS__ = ["None", "Weld"]
__AUTOLIFTOUT_LANDING_JOIN_METHODS__ = ["Weld"]



####### FEATURE FLAGS
_MINIMAP_VISUALISATION = False
_AUTO_SYNC_MINIMAP = True
_REGISTER_METADATA = True