#################
Developer testing
#################
From a clone of the repository and access to a suitable DM-API deployment user
and project you should be able to run a set of basic API tests with the
``test.py`` module in the project root.

First, you need to provide the test code with a configuration that it expects
via a number of environment variables. These are the Data Manager API,
the Keycloak server, its realm and client and a user's credentials.

.. note::
    The test code relies on a user with administrative capabilities.

.. code-block:: bash

    export SQUONK_API_URL='https://example.com/data-manager-api'
    export SQUONK_API_URL_VALIDATION='false'
    export SQUONK_API_KEYCLOAK_URL='https://example.com/auth'
    export SQUONK_API_KEYCLOAK_REALM='squonk'
    export SQUONK_API_KEYCLOAK_CLIENT_ID='data-manager-api'
    export SQUONK_API_KEYCLOAK_USER='user1'
    export SQUONK_API_KEYCLOAK_USER_PASSWORD='blob1234'


With these set you can run the basic tests.

.. code-block:: bash

    export PYTHONPATH=src
    ./test.py
    DM-API connected (https://example.com/data-manager-api)
    DM-API version=0.7.1
    [...]
    Done

And here the developer is testing a project that already exists: -

.. code-block:: bash

    export PYTHONPATH=src
    ./test.py -p project-e1ce441e-c4d1-4ad1-9057-1a11dbdccebe
    DM-API connected (https://example.com/data-manager-api)
    DM-API version=0.7.1
    [...]
    Done
