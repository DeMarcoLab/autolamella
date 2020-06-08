# Installation Guide

## Dependencies
* Python 3.6
* FIB/SEM microscope (a commercial product by ThermoFisher FEI)
* Autoscript software (a commercial product by ThermoFisher FEI)

### Python
Python 3.6 is required.
The [Anaconda distribution](https://www.anaconda.com/distribution/)
of python is recommended.

### Setting up your python virtual environment
It is also highly recommended to use virtual environments for development,
see [Managing Conda Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
for more information.
(Optionally, you could use `virtualenv` if you prefer.)

Create a new virutal environment from the Anaconda Prompt terminal:
```
conda create -n autolamella python=3.6 pip
conda activate autolamella
```

### Installing Autoscript
Autoscript provides an API (application programming interface) for scripting
control of compatible FEI microscope systems.
This is a commercial product by Thermo Fisher FEI, please visit their website
at https://fei.com for information on pricing and installation.

We use Autoscript version 4.1.0

The version numbers of the python packages autoscript installs were:
* autoscript-core 5.1.0
* autoscript-sdb-microscope-client 4.1.0
* autoscript-sdb-microscope-client-tests 4.1.0
* autoscript-toolkit 4.1.0
* thermoscientific-logging 5.1.0

## Install `autolamella`
Download the latest `autolamella` release wheel from https://github.com/DeMarcoLab/autolamella/releases

Pip install the wheel file (`.whl`) into your python virtual environment.
```
conda activate autolamella
pip install $AUTOLAMELLA_WHEEL_FILENAME.whl
```

## Python package dependencies
All the python package dependencies you need should be installed automatically,
with the exception of Autoscript which requires a special license key.

If you do encounter an issue with missing package dependencies,
you can always try reinstalling them with:
```
pip install -r requirements.txt
```

## Having problems?
* Check to see if Autoscript is correctly installed and configured.
* Check to see if your python environment contains all packages listed in
the requirements.txt
* Check that when you call python from the terminal, you get the python
environment containing the dependencies listed above
(i.e. you are not using a different python environment)
* Try cloning the repository and running the unit tests,
you may want to try installing from the source code.

