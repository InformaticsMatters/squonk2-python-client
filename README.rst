Informatics Matters Squonk2 Python Client
=========================================

.. image:: https://badge.fury.io/py/im-squonk2-client.svg
   :target: https://badge.fury.io/py/im-squonk2-client
   :alt: PyPI package (latest)

.. image:: https://readthedocs.org/projects/squonk2-python-client/badge/?version=latest
   :target: https://squonk2-python-client.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/InformaticsMatters/squonk2-python-client/actions/workflows/build.yaml/badge.svg
   :target: https://github.com/InformaticsMatters/squonk2-python-client/actions/workflows/build.yaml
   :alt: Build

.. image:: https://github.com/InformaticsMatters/squonk2-python-client/actions/workflows/publish.yaml/badge.svg
   :target: https://github.com/InformaticsMatters/squonk2-python-client/actions/workflows/publish.yaml
   :alt: Publish

A Python 3 package that provides simplified access to key parts of the
Informatics Matters Squonk2 applications, consisting of Authentication,
Data Manager, Account Server and UI REST interfaces. The functions provide
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

- ``DmApi.add_project_editor()``
- ``DmApi.add_project_observer()``
- ``DmApi.create_project()``
- ``DmApi.delete_instance()``
- ``DmApi.delete_instance_token()``
- ``DmApi.delete_project()``
- ``DmApi.delete_unmanaged_project_files()``
- ``DmApi.dry_run_job_instance()``
- ``DmApi.get_account_server_namespace()``
- ``DmApi.get_account_server_registration()``
- ``DmApi.get_available_instances()``
- ``DmApi.get_available_datasets()``
- ``DmApi.get_available_jobs()``
- ``DmApi.get_available_projects()``
- ``DmApi.get_available_tasks()``
- ``DmApi.get_job()``
- ``DmApi.get_job_definition_schema_version()``
- ``DmApi.get_job_exchange_rates()``
- ``DmApi.get_job_by_version()``
- ``DmApi.get_instance()``
- ``DmApi.get_project()``
- ``DmApi.get_project_instances()``
- ``DmApi.get_service_errors()``
- ``DmApi.get_task()``
- ``DmApi.get_tasks()``
- ``DmApi.get_unmanaged_project_file()``
- ``DmApi.get_unmanaged_project_file_with_token()``
- ``DmApi.get_version()``
- ``DmApi.get_workflow_engine_version()``
- ``DmApi.list_project_files()``
- ``DmApi.put_unmanaged_project_files()``
- ``DmApi.put_job_manifest()``
- ``DmApi.remove_project_editor()``
- ``DmApi.remove_project_observer()``
- ``DmApi.set_admin_state()``
- ``DmApi.set_job_exchange_rates()``
- ``DmApi.start_job_instance()``

A ``dataclass`` is used as the return value for many of the methods: -

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

- ``AsApi.get_account()``
- ``AsApi.add_user_to_organisation()``
- ``AsApi.add_user_to_unit()``
- ``AsApi.alter_asset()``
- ``AsApi.alter_product()``
- ``AsApi.attach_asset()``
- ``AsApi.create_asset()``
- ``AsApi.create_event_stream()``
- ``AsApi.create_organisation()``
- ``AsApi.create_personal_unit()``
- ``AsApi.create_product()``
- ``AsApi.create_unit()``
- ``AsApi.delete_asset()``
- ``AsApi.delete_event_stream()``
- ``AsApi.delete_organisation()``
- ``AsApi.delete_personal_unit()``
- ``AsApi.delete_product()``
- ``AsApi.delete_unit()``
- ``AsApi.detach_asset()``
- ``AsApi.disable_asset()``
- ``AsApi.enable_asset()``
- ``AsApi.get_asset()``
- ``AsApi.get_available_assets()``
- ``AsApi.get_available_units()``
- ``AsApi.get_available_products()``
- ``AsApi.get_event_stream_version()``
- ``AsApi.get_event_stream()``
- ``AsApi.get_merchant()``
- ``AsApi.get_merchants()``
- ``AsApi.get_organisation()``
- ``AsApi.get_product()``
- ``AsApi.get_product_default_storage_cost()``
- ``AsApi.get_product_types()``
- ``AsApi.get_products_for_unit()``
- ``AsApi.get_products_for_organisation()``
- ``AsApi.get_product_charges()``
- ``AsApi.get_organisation_units()``
- ``AsApi.get_organisation_users()``
- ``AsApi.get_organisations()``
- ``AsApi.get_unit()``
- ``AsApi.get_unit_users()``
- ``AsApi.get_units()``
- ``AsApi.get_version()``
- ``AsApi.remove_user_from_organisation()``
- ``AsApi.remove_user_from_unit()``

A ``dataclass`` is used as the return value for many of the methods: -

- ``AsApiRv``

It contains a boolean ``success`` field and a dictionary ``msg`` field. The
``msg`` typically contains the underlying REST API response content
(rendered as a Python dictionary), or an error message if the call failed.

Simplified UI API
=================
The following Squonk2 UI API functions are available: -

- ``UiApi.set_api_url()``

- ``UiApi.get_version()``

A ``dataclass`` is used as the return value for many of the methods: -

- ``UiApiRv``

It contains a boolean ``success`` field and a dictionary ``msg`` field. The
``msg`` typically contains the underlying REST API response content
(rendered as a Python dictionary), or an error message if the call failed.

Examples
========
The package ships with some API examples that might be useful for your own work.
They are located in the package ``examples`` module, where the following imports
should be available: -

- ``from squonk2.examples.data_manager import job_chain``

Debugging the API requests
==========================
For development purposes you can expose detailed debug information relating to
the underlying API requests by setting the environment variable
``SQUONK2_API_DEBUG_REQUESTS``::

    export SQUONK2_API_DEBUG_REQUESTS=yes

This will enable detailed debug of both the DM and AS API calls.

Installation
============
The Squonk2 package is published on `PyPI`_ and can be installed from
there::

    pip install im-squonk2-client

Environment module
==================
The API contains a convenient ``Environment`` module that allows you to
keep your environment variables in a file so that you don't need to
declare them in the shell. The default location of the file is
``~/.squonk2/environments``. If you have multiple installations this
allows you to keep all your environment settings together in one file.

You can use an alternative file  by setting ``SQUONK2_ENVIRONMENTS_FILE``,
e.g. ``export SQUONK2_ENVIRONMENTS_FILE=~/my-env'``

..  code-block:: yaml

    ---

    # An example Squeck environments file.
    #
    # It provides all the connection details for one or more Squonk2 environments.
    # It is expected to be found in the user's home directory
    # as '~/.squonk2/environments' or the user can 'point' to it by setting
    # 'SQUONK2_ENVIRONMENTS_FILE', e.g. 'export SQUONK2_ENVIRONMENTS_FILE=~/my-env'

    # The 'environments' block defines one or more environments.
    # Each has a name. Here we define an environment called 'site-a'
    # but environments can be called anything YAML accepts as a key,
    # although it would aid consistency if you restrict your names to letters
    # and hyphens.
    environments:
      site-a:
        # The hostname of the keycloak server, without a 'http' prefix
        # and without a '/auth' suffix.
        keycloak-hostname: example.com
        # The realm name used for the Squonk2 environment.
        keycloak-realm: squonk2
        # The Keycloak client IDs of the Account Server and Data Manager.
        # The Account Server client ID is optional.
        keycloak-as-client-id: account-server-api
        keycloak-dm-client-id: data-manager-api
        # The hostnames of the Account Server and Data Manager APIs,
        # without a 'http' prefix and without an 'api' suffix.
        # If you have not provided an Account Server client ID its
        # hostname value is not required.
        as-hostname: as.example.com
        dm-hostname: dm.example.com
        # The username and password of an admin user that has access
        # to the Account Server and Data Manager.
        # The user *MUST* have admin rights.
        admin-user: dlister
        admin-password: blob1234

    # The final part of the file is a 'default' property,
    # which Squeck (Squonk Deck) uses to select the an environment from the block above
    # when all else fails. It's simply the name of one of the environment
    # declarations above.
    default: site-a

To avoid placing ``admin-user`` and ``admin-password`` values into the Environment file
you can provide them through environment variables that are scoped to the
environment name. For example, in the above you could omit them both
and provide them as values using the following variables: -

- ``SQUONK2_ENVIRONMENT_SITE_A_ADMIN_USER``
- ``SQUONK2_ENVIRONMENT_SITE_A_ADMIN_PASSWORD``

**Using the Environment**

..  code-block:: python

    from squonk2.environment import Environment

    _ = Environment.load()
    environment: Environment = Environment('site-a')
    # Get the AS API for 'local'
    # The hostname is augmented so you will get (for the above example)
    # the value 'https://as.example.com/account-server-api'
    as_api: str = environment.as_api()

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
