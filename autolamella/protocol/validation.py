import logging
from typing import List
from copy import deepcopy


MILL_ROUGH_KEY = "mill_rough"
MILL_POLISHING_KEY = "mill_polishing"
MICROEXPANSION_KEY = "microexpansion"
FIDUCIAL_KEY = "fiducial"
NOTCH_KEY = "notch"
TRENCH_KEY = "trench"
UNDERCUT_KEY = "undercut"

# milling
MILLING_KEYS = [
    "dwell_time",
    "hfw",
    "milling_current",
    "milling_voltage",
    "patterning_mode",
    "preset",
    "rate",
    "spacing",
    "spot_size",
    "application_file",
    "milling_channel",
]

# strategy
STRATEGY_KEYS = [
    "strategy"
]

# required milling keys
REQUIRED_MILLING_KEYS = [MILL_ROUGH_KEY, MILL_POLISHING_KEY, 
                         MICROEXPANSION_KEY, FIDUCIAL_KEY, NOTCH_KEY]

# default configuration
DEFAULT_ALIGNMENT_AREA = {"left": 0.7, "top": 0.3, "width": 0.25, "height": 0.4}
DEFAULT_FIDUCIAL_PROTOCOL = {
    "height": 10.e-6,
    "width": 1.e-6,
    "depth": 1.0e-6,
    "rotation": 45,
    "milling_current": 2.0e-9,
    "application_file": "Si",
    "hfw": 80.e-6,
    "type": "Fiducial",
    }


DEFAULT_PROTOCOL = {
    MILL_ROUGH_KEY: {
        "stages": [
            {
                "application_file": "Si-ccs",
                "cross_section": "CleaningCrossSection",
                "depth": 6.5e-07,
                "hfw": 50.0e-06,
                "lamella_height": 6.0e-07,
                "lamella_width": 10.0e-06,
                "milling_current": 7.4e-10,
                "offset": 2.0e-06,
                "patterning_mode": "Serial",
                "size_ratio": 1.0,
                "trench_height": 3.5e-06,
                "name": "Rough Mill 01",
                "type": "Trench"
            },
            {
                "application_file": "Si-ccs",
                "cross_section": "CleaningCrossSection",
                "depth": 6.5e-07,
                "hfw": 50.0e-06,
                "lamella_height": 6.0e-07,
                "lamella_width": 9.5e-06,
                "milling_current": 2.0e-10,
                "offset": 5.0e-07,
                "patterning_mode": "Serial",
                "size_ratio": 1.0,
                "trench_height": 2.0e-06,
                "name": "Rough Mill 02",
                "type": "Trench"
            }
        ]
    },
    MILL_POLISHING_KEY: {
        "stages": [
            {
                "application_file": "Si-ccs",
                "cross_section": "CleaningCrossSection",
                "depth": 4.0e-07,
                "hfw": 50.0e-6,
                "lamella_height": 450.0e-9,
                "lamella_width": 9.0e-06,
                "milling_current": 6.0e-11,
                "offset": 0.0,
                "patterning_mode": "Serial",
                "size_ratio": 1.0,
                "trench_height": 7.0e-07,
                "name": "Polishing Mill 01",
                "type": "Trench"
            },
            {
                "application_file": "Si-ccs",
                "cross_section": "CleaningCrossSection",
                "depth": 4.0e-07,
                "hfw": 50.0e-6,
                "lamella_height": 300.0e-9,
                "lamella_width": 9.0e-06,
                "milling_current": 6.0e-11,
                "offset": 0.0,
                "patterning_mode": "Serial",
                "size_ratio": 1.0,
                "trench_height": 2.5e-07,
                "name": "Polishing Mill 02",
                "type": "Trench"
            }
        ]
    },
    MICROEXPANSION_KEY: {
        "width": 0.5e-6,
        "height": 18.e-6,
        "depth": 1.0e-6,
        "distance": 10.e-6,  # distance between microexpansion and lamella centre
        "milling_current": 2.e-9,
        "hfw": 80e-6,
        "application_file": "Si",
        "type": "MicroExpansion"
    },
    NOTCH_KEY: {
        "application_file": "Si",
        "depth": 2.5e-06,
        "distance": 2.0e-06,
        "flip": 0,
        "hfw": 80e-6,
        "hheight": 2.0e-07,
        "hwidth": 4.0e-06,
        "milling_current": 2.0e-09,
        "preset": "30 keV; 2.5 nA",
        "vheight": 2.0e-06,
        "vwidth": 2.0e-07,
        "type": "WaffleNotch"
    },
    FIDUCIAL_KEY: DEFAULT_FIDUCIAL_PROTOCOL,
}

# TODO: this is validate milling protocol, extend to full protocol
def validate_protocol(protocol: dict):
    """Converts the protocol to the new format if necessary and validates it."""
    # upconvert to new protocol
    if "lamella" in protocol["milling"]:
        
        # get the number of polishing, if specified
        num_polishing_stages = protocol["options"].get("num_polishing_stages", 1)
        lamella_protocol = protocol["milling"]["lamella"]["stages"]
            
        protocol["milling"][MILL_ROUGH_KEY] = {"stages": lamella_protocol[:-num_polishing_stages]}
        protocol["milling"][MILL_POLISHING_KEY] = {"stages": lamella_protocol[-num_polishing_stages:]}

        del protocol["milling"]["lamella"] # TODO: refactor the rest of the methods so we can remove this... don't remove just yet

    for key in REQUIRED_MILLING_KEYS:
        if key not in protocol["milling"]:
            # add default values if missing
            logging.info(f"Adding default milling stage for {key}")
            protocol["milling"][key] = DEFAULT_PROTOCOL[key]
    
    # TODO: validate that the protocol is correct, and has all the required keys for each milling stage

    return protocol

# TRENCH
# we need to convert it to the new protocol
# spacing = lamella_height + 2 * offset
# upper_trench_height = trench_height / max(size_ratio, 1.0)
# lower_trench_height = trench_height * min(size_ratio, 1.0)

# convert 
def _convert_trench_protocol(pattern_config: dict) -> dict:
    # convert the old protocol to the new protocol
    pattern_config["width"] = pattern_config["lamella_width"]
    pattern_config["spacing"] = pattern_config["lamella_height"] + 2 * pattern_config.get("offset", 0)
    pattern_config["upper_trench_height"] = pattern_config["trench_height"] / max(pattern_config.get("size_ratio", 1.0), 1.0)
    pattern_config["lower_trench_height"] = pattern_config["trench_height"] * min(pattern_config.get("size_ratio", 1.0), 1.0)

    del pattern_config["lamella_width"]
    del pattern_config["lamella_height"]
    del pattern_config["offset"]
    del pattern_config["size_ratio"]
    del pattern_config["trench_height"]

    return pattern_config

def convert_protocol_to_stage_config(pprotocol: dict, pkey: str) -> dict:

    # get all the milling keys
    milling_config = {k: pprotocol[k] for k in MILLING_KEYS if k in pprotocol}
    strategy_config = {k: pprotocol.get(k, {}) for k in STRATEGY_KEYS if k in pprotocol}

    # pattern
    name = pprotocol.get("type", None)
    # some old protocols don't have type and we need to look it up from the protocol key... best effort only
    if name is None:
        from fibsem.milling.patterning.patterns2 import PROTOCOL_MILL_MAP
        name = PROTOCOL_MILL_MAP.get(pkey, None) # support legacy mapping
        if name is None:
            raise ValueError("Protocol must have a 'type' key for the pattern name")

    # get all the keys that arent in STRATEGY_KEYS or MILLING_KEYS
    pattern_config = {k: v for k, v in pprotocol.items() if k not in STRATEGY_KEYS + MILLING_KEYS + ["name", "type"]}
    pattern_config["name"] = name

    # the keys for these protocol are different, so we need to convert them
    if name in ["Trench", "Horseshoe"]:
        pattern_config = _convert_trench_protocol(pattern_config)

    STAGE_CONFIG = {}
    STAGE_CONFIG["name"] = pprotocol.get("name", name)
    STAGE_CONFIG["milling"] = milling_config
    STAGE_CONFIG["strategy"] = strategy_config
    STAGE_CONFIG["pattern"] = pattern_config

    return STAGE_CONFIG

def convert_old_milling_protocol_to_new_protocol(milling_protocol: dict) -> dict:
    # convert from old protocol to new protocol
    # only support loading new protocol
    # support auto-conversion of old protocol to new protocol

    NEW_PROTOCOL = {}
    for k, v in milling_protocol.items():
        configs: List[dict] = []

        if "stages" in v:
            # LIST[DICT]
            for stage in v["stages"]:
                config = convert_protocol_to_stage_config(stage, k)
                configs.append(deepcopy(config))
        else:
            # DICT
            config = convert_protocol_to_stage_config(v, k)
            configs.append(deepcopy(config))

        NEW_PROTOCOL[k] = configs

    return deepcopy(NEW_PROTOCOL)

def validate_and_convert_protocol(path: str):
    from fibsem import utils
    protocol = utils.load_protocol(path)
    protocol = validate_protocol(protocol)
    protocol["milling"] = convert_old_milling_protocol_to_new_protocol(protocol["milling"])

    return protocol