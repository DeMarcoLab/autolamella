import logging


# required milling keys
REQUIRED_MILLING_KEYS = ["mill_rough", "mill_polishing", "microexpansion", "fiducial", "notch"]

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
    "mill_rough": {
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
    "mill_polishing": {
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
    "microexpansion": {
        "width": 0.5e-6,
        "height": 18.e-6,
        "depth": 1.0e-6,
        "distance": 10.e-6,  # distance between microexpansion and lamella centre
        "milling_current": 2.e-9,
        "hfw": 80e-6,
        "application_file": "Si",
        "type": "MicroExpansion"
    },
    "notch": {
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
    "fiducial": DEFAULT_FIDUCIAL_PROTOCOL,
}

def validate_protocol(protocol: dict):
    """Converts the protocol to the new format if necessary and validates it."""
    # upconvert to new protocol
    if "lamella" in protocol["milling"]:
        
        # get the number of polishing, if specified
        num_polishing_stages = protocol["options"].get("num_polishing_stages", 1)
        lamella_protocol = protocol["milling"]["lamella"]["stages"]
            
        protocol["milling"]["mill_rough"] = {"stages": lamella_protocol[:-num_polishing_stages]}
        protocol["milling"]["mill_polishing"] = {"stages": lamella_protocol[-num_polishing_stages:]}

        # del protocol["milling"]["lamella"] # TODO: refactor the rest of the methods so we can remove this... don't remove just yet

    for key in REQUIRED_MILLING_KEYS:
        if key not in protocol["milling"]:
            # add default values if missing
            logging.info(f"Adding default milling stage for {key}")
            protocol["milling"][key] = DEFAULT_PROTOCOL[key]
    
    # TODO: validate that the protocol is correct, and has all the required keys for each milling stage

    return protocol