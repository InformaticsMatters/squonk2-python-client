# Examples of using the Squonk2 Python client

## Setup
First create and activate a virtual environment: -

    python3 -m venv ~/venvs/squonk2-client
    ~/venvs/squonk2-client/bin/activate

If you are working from a clone of this repository you can use the Python code
directly  by setting PYTHONPATH (**this approach is discouraged**, unless
you're actually developing new Squonk2 client code): -

    export PYTHONPATH=./src

or, install the Squonk2 client from PyPI (**preferred**): -

    pip install squonk2-client~=2.0

Check it all works by running one of the examples: -

    ./examples/calc_rdkit_props.py --help

## Typical usage

1. Set the `SQUONK2_DMAPI_URL` environment variable to point to the Squonk2
   Data Manager API e.g. `https://data-manager.xchem-dev.diamond.ac.uk/data-manager-api`
   See https://data-manager-api.readthedocs.io/en/latest/url.html
2. Set the necessary environment variables for the example.
   See the documentation of the specific example you are running for details.
3. Run the example using the appropriate commandline options

## Examples

### get_token.py
Illustrates how to get an access token from Keycloak
(see the project `README.rst` on requiring a Keycloak password).
That token can then be passed or used in the other examples.

### calc_rdkit_props.py
Illustrates how to: -

- upload a file
- run a simple job (with options) using that file
- wait for the job to complete
- download the results and, finally...
- cleanup (delete) the job instance

### units_products_and_projects.py
Illustrates how to: -

- create an Account Server (AS) organisational unit
- create AS storage and data-tier products
- create a project using an AS project
