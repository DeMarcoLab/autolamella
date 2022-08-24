import logging
import os
from datetime import datetime

import click
import yaml

import autolamella


@click.command()
@click.argument("config_filename")
def main_cli(config_filename):
    """Run the main command line interface.

    Parameters
    ----------
    config_filename : str
        Path to protocol file with input parameters given in YAML (.yml) format
    """
    settings = autolamella.user_input.load_config(config_filename)
    settings["save_directory"] = autolamella.user_input.choose_directory()
    main(settings)


def main(settings):
    """Main function for autolamella.

    Parameters
    ----------
    settings : dictionary
        Dictionary containing user input parameters.
    """

    microscope = autolamella.autoscript.initialize(settings["system"]["ip_address"])
    # microscope.beams.ion_beam.turn_on()
    original_tilt = microscope.specimen.stage.current_position.t
    autolamella.user_input.validate_user_input(microscope, settings)
    start_logging(settings, log_level=logging.INFO)
    protocol_stages = autolamella.user_input.protocol_stage_settings(settings)
    # add samples
    rect_app_file = settings["system"]["application_file_rectangle"]
    autolamella.autoscript.reset_state(
        microscope, settings, application_file=rect_app_file
    )
    lamella_list = autolamella.add_samples.add_samples(microscope, settings)
    message = "Do you want to mill all samples? y/n\n"
    if autolamella.user_input.ask_user(message, default=None):
        autolamella.milling.mill_all_stages(
            microscope,
            protocol_stages,
            lamella_list,
            settings,
            output_dir=settings["save_directory"],
        )
        microscope.beams.ion_beam.turn_off()
    else:
        print("Cancelling ion milling.")
    print("Finished!")


def start_logging(settings, log_level=logging.INFO, log_filename="logfile"):
    """Starts logging, outputs to the terminal and file simultaneously."""
    logging.getLogger(__name__)
    log_directory = settings["save_directory"]
    timestamp = datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
    full_filename = os.path.join(log_directory, log_filename+timestamp+'.log')
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=log_level,
        handlers=[logging.FileHandler(full_filename), logging.StreamHandler()],
    )
    logging.info(yaml.dump(settings))


if __name__ == "__main__":
    main_cli()
