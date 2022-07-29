# Automatic cryoFIB lamella milling

![Build status](https://github.com/DeMarcoLab/autolamella/workflows/Python%20package/badge.svg)

`autolamella` is a python package for automated cryo-lamella preparation
with focused ion beam milling.

## Citation
If you find this useful, please cite our work.

Genevieve Buckley, Gediminas Gervinskas, Cyntia Taveneau, Hariprasad Venugopal, James C. Whisstock, Alex de Marco,
**Automated cryo-lamella preparation for high-throughput in-situ structural biology**,
*Journal of Structural Biology*,
Volume 210, Issue 2,
2020
https://doi.org/10.1016/j.jsb.2020.107488.

See [CITATION](CITATION.md) for more details.

## Software license
This software is released under the terms of the MIT license.
There is NO WARRANTY either express or implied.
See [LICENSE](LICENSE) for details.

## Installation
See [INSTALLATION](INSTALLATION.md) for a more detailed guide.

* Ensure you have Python 3.10 available
* Install Autoscript (a commercial product from FEI)
and configure it for use with your FEI microscope
* Download the latest `autolamella` release wheel from https://github.com/DeMarcoLab/autolamella/releases
* Pip install the wheel file (`.whl`) into your python environment

## Running the program
1. Create/edit the protocol file with details appropriate for your sample.
Protocols are YAML files with the format shown by `protocol_example.yml`
(see [USER_INPUT.md](USER_INPUT.md) for more details).
2. Activate the virtual environment where you have installed `autolamella` and
the dependencies (eg: if you are a conda user, open the Anaconda Prompt and
use "conda activate my-environment-name" or
"source activate my-environment-name", substituting the name of your own
virtual environment.)
3. Launch the program from the terminal by typing:
`autolamella path/to/your_protocol.yml`
4. Follow the user prompts to interactively select new lamella locations,
before beginning the batch ion milling.
