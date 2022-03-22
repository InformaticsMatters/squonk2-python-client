Informatics Matters Data Manager API Utilities
==============================================

.. image:: https://badge.fury.io/py/im-data-manager-api.svg
   :target: https://badge.fury.io/py/im-data-manager-api
   :alt: PyPI package (latest)

A Python 3 package that provides simplified access to key parts of the
Data Manager API REST interface. The functions provide access to some of the
key API methods, implemented initially to support execution of Jobs from a
Fragalysis stack.

The following utilities are available: -

- ``DmApi.get_access_token()``
- ``DmApi.set_api_url()``
- ``DmApi.put_project_files()``
- ``DmApi.post_job_instance()``

Installation (Python)
=====================

The API utilities are published on `PyPI`_ and can be installed from
there::

    pip install im-data-manager-api

Once installed you can use the available classes to upload files to a project
(as an example)::

    >>> from dm_api.dm_api import DmApi
    >>> project_id = 'project-12345678-1234-1234-1234-123456781234'
    >>> result = DmApi.put_project_files(token, project_id, 'data.sdf')

And start Jobs in a Data Manager Project::

    >>> spec = {"collection": "im-test", "job": "nop", "version": "1.0.0"}
    >>> rv = DmApi.post_job_instance(token, project_id, 'My Job', specification=spec)

If you do not have a token the method ``DmApi.get_access_token()`` will
return one from an appropriate keycloak instance. Every API method will need
an access token.

The DM API URL is obtained using the environment variable ``SQUONK_API_URL``.
If you haven't set this variable you can set the URL using a class method::

    >>> DmApi.set_api_url('https://example/com/data-manager-api')

.. _PyPI: https://pypi.org/project/im-data-manager-api

Get in touch
============

- Report bugs, suggest features or view the source code `on GitHub`_.

.. _on GitHub: https://github.com/informaticsmatters/data-manager-api
