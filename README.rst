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
- ``DmApi.delete_project()``
- ``DmApi.get_version()``
- ``DmApi.get_available_projects()``
- ``DmApi.get_project()``
- ``DmApi.get_project_instances()``
- ``DmApi.get_available_jobs()``
- ``DmApi.get_job()``
- ``DmApi.put_unmanaged_project_files()``
- ``DmApi.list_project_files()``
- ``DmApi.delete_unmanaged_project_files()``
- ``DmApi.get_unmanaged_project_file()``
- ``DmApi.get_unmanaged_project_file_with_token()``
- ``DmApi.start_job_instance()``
- ``DmApi.get_instance()``
- ``DmApi.get_task()``
- ``DmApi.delete_instance()``
- ``DmApi.delete_instance_token()``

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

Once installed you can use the available classes to upload files to a Data
Manager **Project** (as an example)::

    >>> from dm_api.dm_api import DmApi, DmApiRv
    >>> rv = DmApi.ping(token)
    >>> assert rv.success
    >>> project_id = 'project-12345678-1234-1234-1234-123456781234'
    >>> rv = DmApi.put_unmanaged_project_files(token, project_id, 'data.sdf')
    >>> assert rv.success

Or start Jobs::

    >>> spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    >>> rv = DmApi.start_job_instance(token, project_id, 'My Job', specification=spec)
    >>> assert rv.success

Depending on which API method is used, when successful,
the Data Manager response payload (its JSON content) is returned in the
``DmApiRv.msg`` property as a Python dictionary.

For example, when successful the ``DmApi.start_job_instance()`` will return
the assigned **Task** and **Instance** identities::

    >>> rv.msg
    {'task_id': 'task-...', 'instance_id': 'instance-...'}

Consult the DM API for up-to-date details of the payloads you can expect.

**Access Tokens**

If you do not have a token the method ``DmApi.get_access_token()`` will
return one from an appropriate keycloak instance and user credentials.
Every API method will need an access token.

**The Data Manager API URL**

The URL to the Data Manager API is taken from the environment variable
``SQUONK_API_URL`` if it exists. If you haven't set this variable you need
to set the Data Manager API URL before you use any API method::

    >>> url = 'https://example.com/data-manager-api'
    >>> DmApi.set_api_url(url)

If the Data Manager API is not secure (e.g. you're developing locally)
you can disable the automatic SSL authentication when you set the URL::

    >>> DmApi.set_api_url(url, verify_ssl_cert=False)

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
