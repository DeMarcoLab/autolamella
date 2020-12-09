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

The version numbers of the python packages Autoscript installs were:
* autoscript-core 5.1.0
* autoscript-sdb-microscope-client 4.1.0
* autoscript-sdb-microscope-client-tests 4.1.0
* autoscript-toolkit 4.1.0
* thermoscientific-logging 5.1.0

#### Add the autoscript python packages to your `site-packages`

To add the AutoScript python packages to your new conda environment, follow these three steps:

1. Find the python environment that was created with your AutoScript installation.
Typically, you can expect the environment is named 'Autoscript', and its installed packages should be found at: 
`C:\Program Files\Python35\envs\AutoScript\Lib\site-packages\`

***Troubleshooting:** If you're having trouble finding the location AutoScript chose to install its python packages into,*
*you can open the *default terminal* on your machine (eg: `cmd` for Windows) and type `where python` (Windows) or `which python` (Unix).*
*The result will be something like `C:\Program Files\Python35\envs\AutoScript\python.exe`.*
*Navigate to the environment location (in the example here, that's `C:\Program Files\Python35\envs\AutoScript\` *
*then change directories into `Lib`, and then the `site-packages` directory. This is where the python packages live.*

2. Find the conda environment location you just made called `autolamella`. 
`...conda/envs/autolamella/Lib/site-packages/`

***Troubleshooting:** If you're having trouble finding the conda environment location for `autolamella-dev`*
*you can open the *Anaconda terminal* on your machine and type `where python` (Windows) or `which python` (Unix).*
*The result will be something like `C:\Users\yourusername\.conda\envs\autolamella-dev\python.exe`*
*Navigate to the environment location (in the example here, that's `C:\Users\yourusername\.conda\envs\autolamella-dev\` *
*then change directories into `Lib`, and then the `site-packages` directory.*
*This is where you want to add copies of the AutoScript python packages.*

3. Make a copy of the relevant AutoScript python packages into the conda environment.
You will need to copy:

* autoscript_core
* autoscript_core-5.4.1.dist-info
* autoscript_sdb_microscope_client
* autoscript_sdb_microscope_client_tests
* autoscript_sdb_microscope_client_tests-4.2.2.dist-info
* autoscript_sdb_microscope_client-4.2.2.dist-info
* autoscript_toolkit
* autoscript_toolkit-4.2.2.dist-info
* thermoscientific_logging
* thermoscientific_logging-5.4.1.dist-info

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
conda activate autolamella
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

