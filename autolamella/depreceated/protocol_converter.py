# import pyyaml module
import yaml
from yaml.loader import SafeLoader

def protocol_converter(old_protocol_path: str, new_protocol_path: str):
    # Open the file and load the file
    with open(old_protocol_path) as f:
        old_protocol = yaml.load(f, Loader=SafeLoader)
        
    new_protocol = {
        'name': 'Autolamella',
        'stage_rotation': 230,
        'stage_tilt': 52,
        'application_file': "autolamella",
        'fiducial': {
            'length': float(old_protocol["fiducial"]["fiducial_length"]),
            'width': float(old_protocol["fiducial"]["fiducial_width"]),
            'depth': float(old_protocol["fiducial"]["fiducial_milling_depth"]),
            'milling_current': float(old_protocol["fiducial"]["fiducial_milling_current"]),
            'preset': "30 keV; 20 nA",
        },
        'lamella': {
            'beam_shift_attempts': 3,
            'lamella_width': float(old_protocol["lamella"]["lamella_width"]),
            'lamella_height': float(old_protocol["lamella"]["lamella_height"]),
            'protocol_stages': [],
            'alignment_current': "Imaging Current"
        }
    }

    try:
        height = float(
            (
                    2 * float(old_protocol["lamella"]["total_cut_height"])
                    * float(old_protocol["lamella"]["protocol_stages"][0]["percentage_roi_height"] + old_protocol["lamella"]["protocol_stages"][0]["percentage_from_lamella_surface"])
                    + float(old_protocol["lamella"]["lamella_height"])
            ) * float(old_protocol["lamella"]["protocol_stages"][0]["microexpansion_percentage_height"])
        )   
        distance = float(float(old_protocol["lamella"]["lamella_width"]) + float(old_protocol["lamella"]["protocol_stages"][0]["microexpansion_width"])) / 2 \
                + float(old_protocol["lamella"]["protocol_stages"][0]["microexpansion_distance_from_lamella"])
        new_protocol["microexpansion"] = {
            'width': float(old_protocol["lamella"]["protocol_stages"][0]["microexpansion_width"]),
            'height': height,
            'distance': distance
        }
    except Exception as e:
        print(f"Error: {e}")
        print("No microexpansion joint information found, moving on.")
    
    for i, protocol_stage in enumerate(old_protocol["lamella"]["protocol_stages"]):
        old_stage = old_protocol["lamella"]["protocol_stages"][i]
        if "milling_depth" not in old_stage:
            old_stage["milling_depth"] = float(old_protocol["lamella"]["milling_depth"])
        if "milling_current" not in old_stage:
            old_stage["milling_current"] = float(old_protocol["lamella"]["milling_current"])
        trench_height = float(
            float(old_protocol["lamella"]["total_cut_height"]) * float(old_stage["percentage_roi_height"])
        )
        offset = float(float(old_protocol["lamella"]["total_cut_height"]) * float(old_stage["percentage_from_lamella_surface"]))
        new_protocol["lamella"]["protocol_stages"].append(
            {
                'trench_height': trench_height,
                'milling_depth': float(old_stage["milling_depth"]),
                'offset': offset,
                'size_ratio': 1.0,
                'milling_current': float(old_stage["milling_current"]),
                'preset': "30 keV; 20 nA",
            }
        )
    
    with open(new_protocol_path, 'w') as f:
        yaml.dump(new_protocol, f)

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()

    parser.add_argument("-old_path")
    parser.add_argument("-new_path")

    args = parser.parse_args()

    try:
        print(f"Old Protocol Path: {args.old_path}")
        print(f"New Protocol Path: {args.new_path}")
        protocol_converter(args.old_path, args.new_path)
    except Exception as e:
        print(f"Error: {e}")
        print("To use: \npython protocol_converter.py -old_path example_old.yaml -new_path example_new.yaml\nFor ease of use, place old protocol file in this directory.")

    

