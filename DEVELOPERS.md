# Developer guide
This software was developed for use in our own research lab.
We've chosen to make the source code available so that other people
can adapt it for their own use.
If you find the project useful, please cite our paper
(see [CITATION.md](CITATION.md)).

There is no express or implied warranty of any kind,
see the [LICENSE](LICENSE) terms for details.

## Setup your development environment
### Install the pre-requisites

1. Autoscript 4.2.2 server and client from ThermoFisher Scientific FEI.

Autoscript is a commercial product for use with ThermoFisher Scientific
microscopes.
Autoscript has a number of its own dependencies, including OpenCV.
See the installation instructions from ThermoFisher Scientific.

For offline development and testing you will need to install a copy of the
Autoscript server on the same computer as the Autoscript client,
which can then be connected to using localhost.

2. Python 3.6
(the [Anaconda distribution](https://www.anaconda.com/distribution/)
is recommended).

It is also highly recommended to use virtual environments for development,
see [Managing Conda Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
for more information.

### Fork then clone the `autolamella` GitHub repository
If you don't already have a GitHub account, you can create one here:
<https://github.com/join>

**First, fork the `autolamella` repository** at
<https://github.com/DeMarcoLab/autolamella>
by clicking the "Fork" button in the upper right hand corner of the web page.
See [GitHub help: Forking a repository](https://help.github.com/en/articles/fork-a-repo)
for details.

**Then, clone your new forked repository to your local computer.**
You can do this using the GitHub webpage interface
(see [GitHub help: Cloning a repository](https://help.github.com/en/articles/cloning-a-repository)),
or from the terminal using the `git clone` command
(remember to replace `$YOUR_GITHUB_USERNAME` with your own GitHub username):

```
git clone https://github.com/$YOUR_GITHUB_USERNAME/autolamella.git
cd autolamella
git remote add upstream https://github.com/DeMarcoLab/autolamella.git
```

**Switch to the "develop" branch of the repository.**

To switch to the `develop` branch of the repository, type:
```
git fetch upstream develop
git checkout develop
```
You can confirm you are on the correct `develop` branch of the autolamella repository by using the command `git branch`.

### Create your virtual environment
It is recommended that you use conda virtual environments for development.
See [Managing Conda Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) for more information.
(Optionally, you could use `virtualenv` if you prefer.)

Run these commands in your terminal to create a new development environment:
```
conda create -n autolamella-dev python=3.6 pip
conda activate autolamella-dev
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Add the autoscript python packages to your `site-packages`

To add the AutoScript python packages to your new conda environment, follow these three steps:

1. Find the python environment that was created with your AutoScript installation.
Typically, you can expect the environment is named 'Autoscript', and its installed packages should be found at: 
`C:\Program Files\Python35\envs\AutoScript\Lib\site-packages\`

***Troubleshooting:** If you're having trouble finding the location AutoScript chose to install its python packages into,*
*you can open the *default terminal* on your machine (eg: `cmd` for Windows) and type `where python` (Windows) or `which python` (Unix).*
*The result will be something like `C:\Program Files\Python35\envs\AutoScript\python.exe`.*
*Navigate to the environment location (in the example here, that's `C:\Program Files\Python35\envs\AutoScript\` *
*then change directories into `Lib`, and then the `site-packages` directory. This is where the python packages live.*

2. Find the conda environment location you just made called `autolamella-dev`. 
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


### Check the AutoScript python packages work in your environment
You can check that this has worked by opening the *Anaconda terminal*, then typing:

```
conda activate autolamella-dev
python
```

And then at the python prompt:

```python
from autoscript_sdb_microscope_client import SdbMicroscopeClient
microscope = SdbMicroscopeClient()
```

If there is no `ImportError` raised, then you have been sucessful.

### Install autolamella as an editable installation

Last, pip install `autolamella` as an editable installation:
```
conda activate autolamella-dev
pip install -e .
```

**Troubleshooting:** If you haven't added the autoscript python packages
properly to your conda environment, you may see this error:

```python
ModuleNotFoundError: No module named 'autoscript_sdb_microscope_client'
```

If this is the case re-try the previous step again, 
and check which packages (and versions) are in your conda environment using `conda list`.

## Make your changes
1. Activate the development environment
```
conda activate autolamella-dev
```

2. Check and update for any recent changes
```
git checkout master
git pull upstream
```

3. Make a new branch
```
git checkout -b new-feature-branch-name
```

4. Make your changes to the code. Use
[git commit](https://www.atlassian.com/git/tutorials/saving-changes/git-commit)
to track your changes in the repository.

5. Add tests and check they pass. See the section on "Running the tests" below.

6. Make a [pull request](https://help.github.com/en/articles/creating-a-pull-request)
to the upstream repository https://github.com/DeMarcoLab/autolamella

## Running the tests
We use [pytest](https://docs.pytest.org/en/latest/) as our testing framework.
To run the test suite:
```
pytest
```

*Note: You can ignore the warning about pytest not recognising `pytest.mark.mpl_image_compare`, this hasn't been causing a problem before.*

To generate new baseline test image results with the
[pytest-mpl plugin](https://github.com/matplotlib/pytest-mpl), run:
```
pytest --mpl-generate-path=tests\baseline
```

## Building the docs
If you are updating existing docs, skip ahead to the next section on
"Updating existing documentation".
If there are no existing docs, then read the section "Building from scratch".

### Building from scratch
This part is only necessary if you are building the documentation from scratch.
To update existing docs, skip ahead to the next section.

1. Run `sphinx-quickstart` from within the `docs/` folder:

```
mkdir docs
cd docs
sphinx-quickstart
```
Answer the questions for package name, author, etc. Use the default values.

2. Configure the path to the root directory
Open `docs/source/conf.py` and configure the path to the root directory.

From this...
```python
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
```

To this instead...
```python
import os
import sys
sys.path.insert(0, os.path.abspath('..'))  # <--- THIS BIT ALSO CHANGED!
```

3. Add sphinx extensions
Open `docs/source/conf.py` and add these sphinx extensions to the list:

```python
extensions = ['m2r',
              'sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'sphinx.ext.napoleon',
              'sphinx.ext.todo',
              'sphinx.ext.viewcode',
]
```

### Updating existing documentation
1. (Re-)build the html documentation
```
cd docs/
sphinx-apidoc -o source/ ../mypackage
make html
```

2. Optional, host the docs on GitHub pages
GitHub pages is enabled un the DeMarcoLab autolamella repository settings.
```
git commit docs/_build/*
git push upstream gh-pages
```

Read more about sphinx:
* https://medium.com/@eikonomega/getting-started-with-sphinx-autodoc-part-1-2cebbbca5365
* https://medium.com/@richdayandnight/a-simple-tutorial-on-how-to-document-your-python-project-using-sphinx-and-rinohtype-177c22a15b5b
* https://sphinx-rtd-tutorial.readthedocs.io/en/latest/index.html
* https://romanvm.pythonanywhere.com/post/autodocumenting-your-python-code-sphinx-part-ii-6/

## Creating a new release
All current releases can be found at
https://github.com/DeMarcoLab/autolamella/releases

For a maintainer to make a new release:
1. Increment the version number in `_version.py`

2. Go to the 'Releases' tab on GitHub and create a new release tag

3. Make the binary files to upload:
```
python setup.py sdist bdist_wheel
```
