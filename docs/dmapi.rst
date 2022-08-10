####################
The Data Manager API
####################
A module providing simplified assess to the Squonk2 Data Manager API.

***********
The API URL
***********
The URL to the Data Manager API is taken from the environment variable
``SQUONK2_DMAPI_URL`` if it exists. If you haven't set this variable you need
to set the Data Manager API URL before you can use any API method.

.. code-block:: python

    url = 'https://example.com/data-manager-api'
    DmApi.set_api_url(url)

If the Data Manager API is not secure (e.g. you're developing locally)
you can disable the automatic SSL authentication when you set the URL.

.. code-block:: python

    DmApi.set_api_url(url, verify_ssl_cert=False)

*******
The API
*******

.. automodule:: squonk2.dm_api
    :members:
