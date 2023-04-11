from pathlib import Path
import os
import fibsem.config as config

# PPP: remove this and use the fibsem one with a default path in experiment
def make_logging_directory(path: Path = None, name="run"):
    if path is None:
        path = os.path.join(config.BASE_PATH, "log")
    directory = os.path.join(path, name)
    os.makedirs(directory, exist_ok=True)
    return directory