##########
Connecting
##########
To use the Squonk2 Data Manager or Accoutn Server API you will need a user
**access token**.

If you do not have a token the method ``Auth.get_access_token()`` will
return one from an appropriate keycloak instance and user credentials.
Every API method will need an access token.

In this example we use the Python ``argparse`` module to extract sensitive keycloak
material form the command line and the ``os.environ`` module to get a username
and password from a pair of environment variables.

.. code-block:: python

    import argparse
    import os

    from squonk2.auth import Auth

    # Username and password are taken from environment variables...
    keycloak_user: str = os.environ['DMAPI_USERNAME']
    keycloak_user_password: str = os.environ['DMAPI_USERNAME_PASSWORD']

    # Less sensitive information is extracted from the command-line...
    parser = argparse.ArgumentParser(description='Delete All DM Project Instances')
    parser.add_argument('--keycloak-hostname', '-k',
                        help='The API URL, i.e. "example.com"',
                        required=True)
    parser.add_argument('--keycloak-realm', '-r',
                        help='The Keycloak realm, i.e. "blob"',
                        required=True)
    parser.add_argument('--keycloak-client-id', '-i',
                        help='The Keycloak client ID, i.e. "data-manager-api-dev"',
                        required=True)
    args = parser.parse_args()

    # Now get an API token.
    # It should be valid for the remainder of the utility...
    token: str = Auth.get_access_token(
        'https://' + args.keycloak_hostname + '/auth',
        args.keycloak_realm,
        args.keycloak_client_id,
        keycloak_user,
        keycloak_user_password,
    )

.. note::
    That this assumes you hav a Keycloak account with a username and password.
    If you have only used a federated login (e.g. CAS, GitHub etc.) then you
    may not have a password. To create one go to your Keycloak account
    (e.g. ``https://<server-name>/auth/realms/<realm-name>/account``),
    login with whatever mechanism you use and then give yourself a password
    in the **Password** section.

*****************
API response data
*****************
Depending on which API method is used, when successful,
the Data Manager response payload (its JSON content) is returned
as a Python dictionary in the ``DmApiRv.msg`` property.

For example, when successful the ``DmApi.start_job_instance()`` will return
the assigned **Task** and **Instance** identities.

.. code-block:: python

    spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    rv: DmApiRv = DmApi.start_job_instance(token, project_id, 'My Job', specification=spec)
    assert rv.success
    rv.msg
    {'task_id': 'task-...', 'instance_id': 'instance-...'}

Consult the DM API for up-to-date details of the payloads you can expect.

******
Errors
******
If the result of an API call fails (``DmApiRv.success`` is ``False``)
an error message can typically be found in the ``DmApiRv.msg``, a dictionary,
using the key ``error``.

.. code-block:: python

    rv.msg
    {'error': 'No API URL defined'}
