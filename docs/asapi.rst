######################
The Account Server API
######################
A module providing simplified assess to the Squonk2 Account Server API.

***********
The API URL
***********
The URL to the Account Server API is taken from the environment variable
``SQUONK2_ASAPI_URL`` if it exists. If you do not want to verify the
SSL certificate you can also set ``SQUONK2_ASAPI_VERIFY_SSL_CERT`` to
anything other than ``"yes"``, its default value.

If you haven't set the API URL variables you need
to set the Account Server API URL before you can use any API method.

.. code-block:: python

    url = 'https://example.com/account-server-api'
    AsApi.set_api_url(url)

If the Account Server API is not secure (e.g. you're developing locally)
you can disable the automatic SSL authentication when you set the URL.

.. code-block:: python

    AsApi.set_api_url(url, verify_ssl_cert=False)

*******
The API
*******

.. automodule:: squonk2.as_api
    :members:
