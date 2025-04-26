# Options to install and use the ASG Runtime library

When you work with the prepackaged SFDPs, the usage options are already wrapped into the SFDP packaging (see documentation there). These instructions are only needed if you want to work locally with SFDP code and images without relying on packaging included in the official SFDP distributions.

## Local usage from cloned sources

Clone the repository, go into the cloned directory, create and activate fresh virtual environment for Python 3.12. Then, depending on what you want to achieve, do:

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
```sh
pil install -e .[test-app]

fastapi dev test/app.py
```
- Pulling and building as part of creating the SFDP imange

## Local usage from remote repo reference

If your local machine has access to the asg-runtime repository and you don't want to pull in the sources, just do this in your SFDP's virtual environment:

```sh
TODO modify to use the real link to TEADAL gitlab
git+http://git@github.com/<user-or-org>/asg-runtime.git
```

