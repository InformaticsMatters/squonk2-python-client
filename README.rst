Informatics Matters Data Manager API Client
===========================================

.. image:: https://badge.fury.io/py/im-data-manager-api.svg
   :target: https://badge.fury.io/py/im-data-manager-api
   :alt: PyPI package (latest)

A Python 3 package that provides simplified access to key parts of the
Informatics Matters Data Manager API REST interface. The functions provide
access to some of the key API methods, implemented initially to support
execution of Jobs from a Fragalysis stack `backend`_.

The following API functions are available: -

- ``DmApi.get_access_token()``
- ``DmApi.set_api_url()``
- ``DmApi.get_api_url()``

- ``DmApi.ping()``

- ``DmApi.create_project()``
- ``DmApi.delete_instance()``
- ``DmApi.delete_instance_token()``
- ``DmApi.delete_project()``
- ``DmApi.delete_unmanaged_project_files()``
- ``DmApi.get_available_jobs()``
- ``DmApi.get_available_projects()``
- ``DmApi.get_job()``
- ``DmApi.get_job_by_name()``
- ``DmApi.get_instance()``
- ``DmApi.get_project()``
- ``DmApi.get_project_instances()``
- ``DmApi.get_task()``
- ``DmApi.get_unmanaged_project_file()``
- ``DmApi.get_unmanaged_project_file_with_token()``
- ``DmApi.get_version()``
- ``DmApi.list_project_files()``
- ``DmApi.put_unmanaged_project_files()``
- ``DmApi.start_job_instance()``
- ``DmApi.set_admin_state()``

A ``namedtuple`` is used as the return value for many of the methods: -

- ``DmApiRv``

It contains a boolean ``success`` field and a dictionary ``msg`` field. The
``msg`` typically contains the underlying REST API response content
(rendered as a Python dictionary), or an error message if the call failed.

Installation (Python)
=====================

The API utilities are published on `PyPI`_ and can be installed from
there::

    pip install im-data-manager-api

**Access Tokens**

If you do not have a token the method ``DmApi.get_access_token()`` will
return one from an appropriate keycloak instance and user credentials.
Every API method will need an access token.

In this example we use the Python argparse module to extract sensitive keycloak
material form the command line and the os.environ module to get a username
and password::

    import argparse
    import os

    from dm_api.dm_api import DmApi, DmApiRv

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
    token: str = DmApi.get_access_token(
        'https://' + args.keycloak_hostname + '/auth',
        args.keycloak_realm,
        args.keycloak_client_id,
        keycloak_user,
        keycloak_user_password,
    )

**The Data Manager API URL**

The URL to the Data Manager API is taken from the environment variable
``SQUONK_API_URL`` if it exists. If you haven't set this variable you need
to set the Data Manager API URL before you use any API method::

    url = 'https://example.com/data-manager-api'
    DmApi.set_api_url(url)

If the Data Manager API is not secure (e.g. you're developing locally)
you can disable the automatic SSL authentication when you set the URL::

    DmApi.set_api_url(url, verify_ssl_cert=False)

**Using the API**

With an API URL and access token you can use the API. Here, as an example,
we upload files to a Data Manager **Project**::

    rv: DmApiRv = DmApi.ping(token)
    assert rv.success
    project_id = 'project-12345678-1234-1234-1234-123456781234'
    rv = DmApi.put_unmanaged_project_files(token, project_id, 'data.sdf')
    assert rv.success

Or start Jobs::

    spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    rv = DmApi.start_job_instance(token, project_id, 'My Job', specification=spec)
    assert rv.success

Depending on which API method is used, when successful,
the Data Manager response payload (its JSON content) is returned in the
``DmApiRv.msg`` property as a Python dictionary.

For example, when successful the ``DmApi.start_job_instance()`` will return
the assigned **Task** and **Instance** identities::

    rv.msg
    {'task_id': 'task-...', 'instance_id': 'instance-...'}

Consult the DM API for up-to-date details of the payloads you can expect.

.. _backend: https://github.com/xchem/fragalysis-backend
.. _PyPI: https://pypi.org/project/im-data-manager-api

Developer testing
=================
From a clone of the repository and access to a suitable DM-API deployment user
and project you should be able to run a set of basic API tests with the
``test`` module in the project root.

First, you need to provide the test code with a suitable configuration
via the environment::

    export SQUONK_API_URL='https://example.com/data-manager-api'
    export SQUONK_API_KEYCLOAK_URL='https:/example.com/auth'
    export SQUONK_API_KEYCLOAK_REALM='squonk'
    export SQUONK_API_KEYCLOAK_CLIENT_ID='data-manager-api'
    export SQUONK_API_KEYCLOAK_USER='user1'
    export SQUONK_API_KEYCLOAK_USER_PASSWORD='blob1234'

With these set you can run the basic ests, here using a project that already
exists on the chosen Data Manager service::

    export PYTHONPATH=src
    ./test.py -p project-e1ce441e-c4d1-4ad1-9057-1a11dbdccebe
    DM-API connected (https://example.com/data-manager-api)
    DM-API version=0.7.1
    [...]

Get in touch
============

- Report bugs, suggest features or view the source code `on GitHub`_.

.. _on GitHub: https://github.com/informaticsmatters/data-manager-api
