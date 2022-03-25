Informatics Matters Data Manager API Utilities
==============================================

.. image:: https://badge.fury.io/py/im-data-manager-api.svg
   :target: https://badge.fury.io/py/im-data-manager-api
   :alt: PyPI package (latest)

A Python 3 package that provides simplified access to key parts of the
Data Manager API REST interface. The functions provide access to some of the
key API methods, implemented initially to support execution of Jobs from a
Fragalysis stack `backend`_.

The following API functions are available: -

- ``DmApi.get_access_token()``
- ``DmApi.set_api_url()``

- ``DmApi.ping()``

- ``DmApi.get_version()``
- ``DmApi.get_available_jobs()``
- ``DmApi.get_job()``
- ``DmApi.upload_unmanaged_project_files()``
- ``DmApi.list_project_files()``
- ``DmApi.download_unmanaged_project_file()``
- ``DmApi.start_job_instance()``
- ``DmApi.get_instance()``
- ``DmApi.get_task()``
- ``DmApi.delete_instance()``

A ``namedtuple`` is used as the return value for many of the methods: -

- ``DmApiRv``

it contains a boolean ``success`` field and a dictionary ``msg`` filed,
that typically contains the underlying REST API response content, or an error
message on failure.

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
    >>> rv = DmApi.upload_unmanaged_project_files(token, project_id, 'data.sdf')
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
to set the URL before you use any API method::

    >>> url = 'https://example.com/data-manager-api'
    >>> DmApi.set_api_url(url)

If the Data Manager API is not secure (e.g. you're developing locally)
you can disable the automatic SSL authentication when setting the URL::

    >>> DmApi.set_api_url(url, verify_ssl_cert=False)

.. _backend: https://github.com/xchem/fragalysis-backend
.. _PyPI: https://pypi.org/project/im-data-manager-api

Get in touch
============

- Report bugs, suggest features or view the source code `on GitHub`_.

.. _on GitHub: https://github.com/informaticsmatters/data-manager-api