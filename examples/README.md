# Examples of using the Python client

## Setup

First create and activate a virtual environment: -

    python3 -m venv ~/venvs/dm-api-client
    ~/venvs/dm-api-client/bin/activate

You can either use the Python code directly by setting PYTHONPATH: -

    export PYTHONPATH=./src

or, install them from PyPI (preferred): -

    pip install im-data-manager-api

Check it all works by running one of the examples: -

    ./examples/CalcRDkitProps.py --help

## Typical usage

1. Set the `SQUONK_API_URL` environment variable to point to the Squonk Data Manager API
   e.g. https://data-manager.xchem-dev.diamond.ac.uk/data-manager-api
   See https://data-manager-api.readthedocs.io/en/latest/url.html
2. Set the necessary environment variables for the example.
   See the documentation of the specific example you are running for details.
3. Run the example using the appropriate commandline options

## Examples

### GetToken.py
Illustrates how to get an access token from Keycloak
(see the project `README.rst` on requiring a Keycloak password).
That token can then be passed or used in the other examples.

### CalcRDkitProps.py
Illustrates how to: -

- upload a file
- run a simple job (with options) using that file
- wait for the job to complete
- download the results and, finally...
- cleanup (delete) the job instance
