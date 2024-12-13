
import argparse
import os

import matplotlib.pyplot as plt
import yaml
from fibsem.milling import get_milling_stages
from fibsem.milling.patterning.plotting import (
    draw_milling_patterns,
    generate_blank_image,
)
from autolamella.protocol.validation import validate_and_convert_protocol

def convert_protocol_and_save_changes(protocol_path: str):

    validated_protocol = validate_and_convert_protocol(protocol_path)

    MILLING_PROTOCOL = validated_protocol["milling"]
    for KEY in validated_protocol["milling"].keys():

        stages = []
        stages.extend(get_milling_stages(KEY, MILLING_PROTOCOL))

        image = generate_blank_image(hfw=stages[0].milling.hfw)
        fig = draw_milling_patterns(image, stages)
        plt.title(f"Patterns: {KEY}")
        plt.show()

    ret = input("Save new protocol? (y/n): ")

    if ret.lower() == "y":

        NEW_PROTOCOL_PATH = protocol_path.replace(".yaml", "-new.yaml")
        with open(os.path.join(NEW_PROTOCOL_PATH), "w") as f:
            yaml.safe_dump(validated_protocol, f, indent=4)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=str, help="Path to protocol file.")
    args = parser.parse_args()

    if args.protocol:
        convert_protocol_and_save_changes(args.protocol)

if __name__ == "__main__":
    main()