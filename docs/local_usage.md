# Options to install and use the ASG Runtime library

When you work with the prepackaged SFDPs, the usage options are already wrapped into the SFDP packaging (see documentation there). These instructions are only needed if you want to work locally with SFDP code and images without relying on packaging included in the official SFDP distributions.

## Local usage from cloned sources

Clone the repository, go into the cloned directory, create and activate fresh virtual environment for Python 3.12. 
```sh
# make sure path points to Python 3.12
which python      

# create virtual environment
python -m venv .venv

# activate virtual environment
. .venv/Scripts/activate        # on windows
# or
. .venv/bin/activate            # on linux

# verify your python is now points to inside the clean .venv
which python    # should have your .venv in path
which pip       # should have your .venv in path
pip list        # should be empty for new environments

# update pip
python -m pip install --upgrade pip
```
Then, depending on what you want to achieve, do:

### To run your SFDP in the same virtual environment
```sh
pip install -e .        
```
This will install the asg-library with its basic prerequisites so your SFDP app can rely on it. Alternatively, you can refer to the cloned directory when installing the asg-library into the virtual environment of your SFDP with:

```sh
pip install -e <path to the cloned asg-library folder>
```

### To test the library
```sh
# update dependencies
pip install -e .[test]  

# run the test suite
pytest
```

### To develop the library
```sh
# this will bring in dev tools
pip install -e .[dev]   

# make changes

ruff check . --fix && ruff format .
```

### To run the included test SFDP

First, install the prerequisites for running FastAPI
```sh
pip install -e .[test-app]
```

Now, inspect the example [`.env`](../.env) file to see that the desired configuration settings are applied. Note here that you might have to install additional dependencies required by some combinations of parameters. All this is described inside the example `.env`.

After you have ensured the configuration is ok, you can start the test SDFP with:
```sh
fastapi dev test/app.py
```
In a case startup fails, modify `.env` to work in `DEBUG` mode, invoke the command again and try in inspect the reported failure reason or provide the log to the asg-library dev team.

If startup suceeds, you can now send requests to the test SFDP, either through curl or from browser. Note that the ASG-compatible app supports `/docs`, `/service/stats`, and , `/service/settings` endpoints in addition to the data endpoints required by the SFDP contract.

## Installing the library from the artifacts

If your environment has access to the asg-runtime repository and you don't want to pull in the sources, your options are:

1. Install the library by referencing the repo:
```sh
TODO modify to use the real link to TEADAL gitlab
pip install git+http://git@github.com/<user-or-org>/asg-runtime.git
```

1. Pull the build package published in the repository

1. Pull the image published in the repository



