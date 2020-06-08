# Automatic FIBSEM lamella milling

![Build status](https://ci.appveyor.com/api/projects/status/x1drgqi4528q2yg9/branch/master?svg=true)

`autolamella` is a python package for automated cryo-lamella preparation
with focused ion beam milling.

## Citation
If you find this useful, please cite our work.
There is a bioRxiv preprint available at: https://doi.org/10.1101/797506
See [CITATION](CITATION.md) for details.

## Software license
This software is released under the terms of the MIT license.
There is NO WARRANTY either express or implied.
See [LICENSE](LICENSE) for details.

## Installation
See [INSTALLATION](INSTALLATION.md) for a more detailed guide.

* Ensure you have Python 3.6 available
* Install Autoscript (a commercial product from FEI)
and configure it for use with your FEI microscope
* Download the latest `autolamella` release wheel from https://github.com/DeMarcoLab/autolamella/releases
* Pip install the wheel file (`.whl`) into your python environment

## Running the program
1. Create/edit the protocol file with details appropriate for your sample.
Protocols are YAML files with the format shown by `protocol_example.yml` (see [USER_INPUT.md](USER_INPUT.md) for more details).
2.  Launch the program from the terminal by typing:
`autolamella path/to/your_protocol.yml`
3. Follow the user prompts to interactively select new lamella locations,
before beginning the batch ion milling.
