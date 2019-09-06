from setuptools import setup, find_packages

from lamella._version import __version__


DISTNAME = "lamella"
DESCRIPTION = "DeMarco lab package for automated lamella milling."
MAINTAINER = "Genevieve Buckley"
URL = "https://github.com/DeMarcoLab/lamella"
DOWNLOAD_URL = "https://github.com/DeMarcoLab/lamella"
VERSION = __version__
PYTHON_VERSION = (3, 6, 7)
INST_DEPENDENCIES = []

if __name__ == "__main__":
    setup(
        name=DISTNAME,
        version=__version__,
        url=URL,
        description=DESCRIPTION,
        author=MAINTAINER,
        packages=find_packages(),
        install_requires=INST_DEPENDENCIES,
    )
