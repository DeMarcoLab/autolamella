import os

import autolamella.liftout as liftout

BASE_PATH = os.path.dirname(liftout.__file__) # TODO: fix this to be the root directory of the project
CONFIG_PATH = os.path.join(BASE_PATH, "config")
SYSTEM_PATH = os.path.join(CONFIG_PATH, "system.yaml")
PROTOCOL_PATH = os.path.join(BASE_PATH, "protocol", "protocol.yaml")
LOG_PATH = os.path.join(BASE_PATH, "log")
EXPERIMENT_NAME = "AutoLiftout"

__AUTOLIFTOUT_METHODS__ = ["autoliftout-default", "autoliftout-serial-liftout"]
__AUTOLIFTOUT_LIFTOUT_JOIN_METHODS__ = ["None", "Weld"]
__AUTOLIFTOUT_LANDING_JOIN_METHODS__ = ["Weld"]


DISPLAY_REFERENCE_FNAMES = [
    "ref_lamella_low_res_ib",
    "ref_trench_high_res_ib",
    "ref_jcut_high_res_ib",
    "ref_liftout_sever_ib",
    "ref_landing_lamella_high_res_ib",
    "ref_reset_high_res_ib",
    "ref_thin_lamella_ultra_res_ib",
    "ref_polish_lamella_ultra_res_ib",
]