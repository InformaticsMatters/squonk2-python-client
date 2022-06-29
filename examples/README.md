# Examples of using the Python client

## Authentication

These examples assume you have a account in Keycloak that has a username and password defined.
If you have only used federated logins (e.g. CAS, Orchid, GitHub etc.) then your Keycloak account may not
have a password defined. To create one go to your Keycloak account 
(e.g. https://<server-name>/auth/realms/<realm-name>/account), login with whatever mechanism you use
and then give yourself a password in the 'Password' section.

## Setup

First create a virtual environment using the [](../requirements.txt) file.
`python3 -m venv ~/venvs/dm-api-client`

Now activate that virtual environment
`~/venvs/dm-api-client/bin/activate`

Then either add the python modules from this repo to that environment (useful if you are changing these files):
`pip install -e .`
or pip install them from PyPi
`pip install im-data-manager-api`

Check it all works e.g.
`python examples/CalcRDkitProps.py --help`

## Typical usage

1. Set the necessary environment variables. See the documentation of the specific example you are running for details.
2. Run the example using the appropriate commandline options

## Examples

### GetToken.py
Illustrates how to get an access token from Keycloak (see the above note on requiring a Keycloak password).
That token can then be passed in to the other examples.

### CalcRDkitProps.py
Illustrates how to upload a file, run a simple job (with options) using that file wait for the job to complete,
download the results nd finally cleanup (delete) the job instance.