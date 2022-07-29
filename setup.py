from setuptools import setup, find_packages

from autolamella._version import __version__


def parse_requirements_file(filename):
    with open(filename) as f:
        requires = [line.strip() for line in f.readlines() if line]

    return requires


DISTNAME = "autolamella"
DESCRIPTION = (
    "Automatated ion beam milling for cryo-electron microscopy sample preparation."
)
MAINTAINER = "Genevieve Buckley"
URL = "https://github.com/DeMarcoLab/autolamella"
DOWNLOAD_URL = "https://github.com/DeMarcoLab/autolamella"
VERSION = __version__
PYTHON_VERSION = (3, 10)
INST_DEPENDENCIES = parse_requirements_file("requirements.txt")

if __name__ == "__main__":
    setup(
        name=DISTNAME,
        version=__version__,
        url=URL,
        description=DESCRIPTION,
        author=MAINTAINER,
        packages=find_packages(),
        install_requires=INST_DEPENDENCIES,
        entry_points={"console_scripts": ["autolamella = autolamella.main:main_cli"]},
    )
