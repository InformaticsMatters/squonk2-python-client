Informatics Matters Data Manager API Client
===========================================

.. image:: https://badge.fury.io/py/im-data-manager-api.svg
   :target: https://badge.fury.io/py/im-data-manager-api
   :alt: PyPI package (latest)

.. image:: https://readthedocs.org/projects/data-manager-api/badge/?version=latest
   :target: https://data-manager-api.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

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

Documentation
=============

Project documentation is available in the `data-manager-api`_ project on
**Read the Docs**

Get in touch
============

- Report bugs, suggest features or view the source code `on GitHub`_.

.. _on GitHub: https://github.com/informaticsmatters/data-manager-api
.. _backend: https://github.com/xchem/fragalysis-backend
.. _data-manager-api: https://data-manager-api.readthedocs.io/en/latest/
.. _PyPI: https://pypi.org/project/im-data-manager-api
