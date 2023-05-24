## Overview

AutoLamella is a python package for automated cryo-lamella preparation with focused ion beam milling. It is based on [openFIBSEM](https://github.com/DeMarcoLab/fibsem), and currently supports the [TESCAN Automation SDK](https://www.tescan.com/en/products/automation-sdk/) and [ThermoFisher AutoScript](https://www.tescan.com/en/products/autoscript/). Support for other FIBSEM systems is planned.

## Documentation
[Documentation Site](https://demarcolab.github.io/autolamella/)


## Install

### Install OpenFIBSEM
Clone this repository: 

```
$ git clone https://github.com/DeMarcoLab/fibsem.git
```

Install dependencies and package
```bash
$ cd fibsem
$ conda env create -f environment.yml
$ conda activate fibsem
$ pip install -e .

```
### Install autolamella package
Clone this repository: 

```
$ git clone https://github.com/DeMarcoLab/autolamella.git
```

Install dependencies and package
```bash
$ conda activate fibsem
$ cd autolamella
$ pip install -e .
$ pip install pywin32==228
$ conda install -c conda-forge petname

```

### Install AutoScript
You will also need to install AutoScript 4.6+. 

Please see the [Installation Guide](INSTALLATION.md) for detailed instructions.

Copy AutoScript /into home/user/miniconda3/envs/fibsem/lib/python3.9/site-packages/

### Install TESCAN Automation SDK

Ideally, please install and set up the conda environment first before proceeding to install this SDK

Run the Tescan-Automation-SDK-Installer-3.x.x.exe file

When asked for the python interpretor, select the existing conda environment for FIBSEM, if this python interpretor is not available, see detailed installation guide for a work around

See [Installation Guide](INSTALLATION.md) for full details


### Getting started 
To run autolamella:
```bash
$ conda activate autolamella
$ autolamella
```
![UI](docs/img/ui.png)


## Citation
If you find this useful, please cite our work.

Genevieve Buckley, Gediminas Gervinskas, Cyntia Taveneau, Hariprasad Venugopal, James C. Whisstock, Alex de Marco,
**Automated cryo-lamella preparation for high-throughput in-situ structural biology**,
*Journal of Structural Biology*,
Volume 210, Issue 2,
2020
https://doi.org/10.1016/j.jsb.2020.107488.

See [CITATION](CITATION.md) for more details.

