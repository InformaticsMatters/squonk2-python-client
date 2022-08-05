Informatics Matters Squonk2 Python Client
=========================================

.. image:: https://badge.fury.io/py/im-squonk2-client.svg
   :target: https://badge.fury.io/py/im-squonk2-client
   :alt: PyPI package (latest)

.. image:: https://readthedocs.org/projects/squonk2-python-client/badge/?version=latest
   :target: https://squonk2-python-client.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

A Python 3 package that provides simplified access to key parts of the
Informatics Matters Squonk2 service, consisting of the Authentication, and
Data Manager and Account Server REST interfaces. The functions provide
access to some of the key API methods, implemented initially to support
execution of Jobs from a Fragalysis stack `backend`_.

Simplified Authentication
=========================
The following Squonk2 Authentication functions are available: -

- ``Auth.get_access_token()``

Simplified Data Manager API
===========================
The following Squonk2 Data Manager API functions are available: -

- ``DmApi.set_api_url()``
- ``DmApi.get_api_url()``

- ``DmApi.ping()``

- ``DmApi.create_project()``
- ``DmApi.delete_instance()``
- ``DmApi.delete_instance_token()``
- ``DmApi.delete_project()``
- ``DmApi.delete_unmanaged_project_files()``
- ``DmApi.get_available_datasets()``
- ``DmApi.get_available_jobs()``
- ``DmApi.get_available_projects()``
- ``DmApi.get_job()``
- ``DmApi.get_job_exchange_rates()``
- ``DmApi.get_job_by_version()``
- ``DmApi.get_instance()``
- ``DmApi.get_project()``
- ``DmApi.get_project_instances()``
- ``DmApi.get_service_errors()``
- ``DmApi.get_task()``
- ``DmApi.get_unmanaged_project_file()``
- ``DmApi.get_unmanaged_project_file_with_token()``
- ``DmApi.get_version()``
- ``DmApi.list_project_files()``
- ``DmApi.put_unmanaged_project_files()``
- ``DmApi.set_admin_state()``
- ``DmApi.start_job_instance()``

A ``namedtuple`` is used as the return value for many of the methods: -

- ``DmApiRv``

It contains a boolean ``success`` field and a dictionary ``msg`` field. The
``msg`` typically contains the underlying REST API response content
(rendered as a Python dictionary), or an error message if the call failed.

Simplified Account Server API
=============================
The following Squonk2 Account Server API functions are available: -

- ``AsApi.set_api_url()``
- ``AsApi.get_api_url()``

- ``AsApi.ping()``

- ``AsApi.get_version()``

A ``namedtuple`` is used as the return value for many of the methods: -

- ``AsApiRv``

It contains a boolean ``success`` field and a dictionary ``msg`` field. The
``msg`` typically contains the underlying REST API response content
(rendered as a Python dictionary), or an error message if the call failed.

Installation
============
The Squonk2 package is published on `PyPI`_ and can be installed from
there::

    pip install im-squonk2-client

Documentation
=============
Documentation is available in the `squonk2-python-client`_ project on
**Read the Docs**

Get in touch
============

- Report bugs, suggest features or view the source code `on GitHub`_.

.. _on GitHub: https://github.com/informaticsmatters/squonk2-python-client
.. _backend: https://github.com/xchem/fragalysis-backend
.. _squonk2-python-client: https://squonk2-python-client.readthedocs.io/en/latest/
.. _PyPI: https://pypi.org/project/im-squonk2-client
