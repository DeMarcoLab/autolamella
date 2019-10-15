import logging
import os

import click
import yaml

import autolamella
from autolamella.interactive import ask_user


def configure_logging(
    *, log_level=logging.INFO, log_filename="logfile.log", log_directory=""
):
    """Log to the terminal and to file simultaneously."""
    logging.getLogger(__name__)
    full_filename = os.path.join(log_directory, log_filename)
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=log_level,
        handlers=[logging.FileHandler(full_filename), logging.StreamHandler()],
    )


def start_logging(settings, log_level=logging.INFO):
    configure_logging(log_directory=settings["save_directory"], log_level=log_level)
    logging.info(yaml.dump(settings))


@click.command()
@click.argument("config_filename")
def run_main_cmd(config_filename):
    settings = autolamella.user_input.load_config(config_filename)
    settings["save_directory"] = autolamella.interactive.choose_directory()
    main(settings)


def main(settings):
    microscope = autolamella.autoscript.initialize(settings["system"]["ip_address"])
    autolamella.validate.validate_user_input(microscope, settings)
    start_logging(settings, log_level=logging.INFO)
    protocol_stages = autolamella.user_input.protocol_stage_settings(settings)
    # add samples
    rect_app_file = settings["system"]['application_file_rectangle']
    autolamella.autoscript.reset_state(microscope, settings,
                                       application_file=rect_app_file)
    lamella_list = autolamella.add_samples.add_samples(microscope, settings)
    message = "Do you want to mill all samples? yes/no\n"
    if ask_user(message, default=None) == True:
        autolamella.milling.mill_all_stages(
            microscope,
            protocol_stages,
            lamella_list,
            settings,
            output_dir=settings["save_directory"],
        )
    else:
        print("Cancelling ion milling.")
    print("Finished!")


if __name__ == "__main__":
    run_main_cmd()
