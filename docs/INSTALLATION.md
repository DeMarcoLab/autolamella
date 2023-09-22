# Installation Guide

## Dependencies
* Python 3.9+
* FIB/SEM microscope (a commercial product by ThermoFisher FEI or TESACN)
* Autoscript software (a commercial product by ThermoFisher FEI)
* tescanautomation software (a commercial product by TESCAN)

### Python
Python 3.9+ is required.
The [Anaconda distribution](https://www.anaconda.com/distribution/)
of python is recommended.

## Setting up your python virtual environment
It is also highly recommended to use virtual environments for development,
see [Managing Conda Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
for more information.
(Optionally, you could use `virtualenv` if you prefer.)

### Recommended Installation Guide

Create a new virtual environment from the Anaconda Prompt terminal:
```
$ conda create -n fibsem python=3.9 pip
$ conda activate fibsem
$ pip install autolamella 
```

### Installing from source

Clone this repository, and checkout v0.2-stable: 

```
$ git clone https://github.com/DeMarcoLab/autolamella.git
$ git checkout origin/v0.2-stable

```
Create an environment and install the package:

```
$ conda create -n fibsem python=3.9 pip
$ conda activate fibsem
$ pip install -e .
```

### Running Autolamella

Open the Anaconda Prompt terminal and run the following commands.

```
$ conda activate fibsem
$ autolamella_ui

```

## Installing the commercial microscope APIs

For instructions and trouble shooting tips for installing the microscope APIs, see [Installation Guide](extras.md).