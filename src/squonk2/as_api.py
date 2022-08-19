"""Python utilities to simplify calls to some parts of the Account Server API that
interact with **Organisations**, **Units**, **Products** and **Assets**.

.. note::
    The URL to the DM API is automatically picked up from the environment variable
    ``SQUONK2_ASAPI_URL``, expected to be of the form **https://example.com/account-server-api**.
    If the variable isn't set the user must set it programmatically
    using :py:meth:`AsApi.set_api_url()`.
"""
from collections import namedtuple
from datetime import date
import logging
import os
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from wrapt import synchronized
import requests

AsApiRv: namedtuple = namedtuple("AsApiRv", "success msg")
"""The return value from most of the the AsApi class public methods.

:param success: True if the call was successful, False otherwise.
:param msg: API request response content
"""

# The Account Server API URL environment variable,
# You can set the API manually with set_apu_url() if this is not defined.
_API_URL_ENV_NAME: str = "SQUONK2_ASAPI_URL"
_API_VERIFY_SSL_CERT_ENV_NAME: str = "SQUONK2_ASAPI_VERIFY_SSL_CERT"

# How old do tokens need to be to re-use them?
# If less than the value provided here, we get a new one.
# Used in get_access_token().
_PRIOR_TOKEN_MIN_AGE_M: int = 1

# A common read timeout
_READ_TIMEOUT_S: int = 4
# A longer timeout
_READ_LONG_TIMEOUT_S: int = 12

# Debug request times?
# If set the duration of each request call is logged.
_DEBUG_REQUEST_TIME: bool = False
# Debug request calls?
# If set the arguments and response of each request call is logged.
_DEBUG_REQUEST: bool = False

_LOGGER: logging.Logger = logging.getLogger(__name__)

# A regular expression for an AS UUID,
# i.e. a UUID for org/unit/product/assets etc.
_RE_UUID: re.Pattern = re.compile(
    "^[a-z]{3,}-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
)


class AsApi:
    """The AsApi class provides high-level, simplified access to the AS REST API.
    You can use the request module directly for finer control. This module
    provides a wrapper around the handling of the request, returning a simplified
    namedtuple response value ``AsApiRv``
    """

    def __init__(self):
        """Constructor"""

        # The default AS API is extracted from the environment,
        # otherwise it can be set using 'set_api_url()'
        self.__as_api_url: str = os.environ.get(_API_URL_ENV_NAME, "")
        # Do we expect the AS API to be secure?
        # Normally yes, but this can be disabled using 'set_api_url()'
        self.__verify_ssl_cert: bool = (
            os.environ.get(_API_VERIFY_SSL_CERT_ENV_NAME, "yes").lower() == "yes"
        )

    def __request(
        self,
        method: str,
        endpoint: str,
        *,
        error_message: str,
        access_token: Optional[str] = None,
        expected_response_codes: Optional[List[int]] = None,
        headers: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = _READ_TIMEOUT_S,
    ) -> Tuple[AsApiRv, Optional[requests.Response]]:
        """Sends a request to the AS API endpoint. The caller normally has to provide
        an oauth-like access token but this is not mandated.

        All the public API methods pass control to this method,
        returning its result to the user.
        """
        assert method in ["GET", "POST", "PUT", "PATCH", "DELETE"]
        assert endpoint
        assert isinstance(expected_response_codes, (type(None), list))

        if not self.__as_api_url:
            return AsApiRv(success=False, msg={"error": "No API URL defined"}), None

        url: str = self.__as_api_url + endpoint

        # if we have it, add the access token to the headers,
        # or create a headers block
        use_headers = headers.copy() if headers else {}
        if access_token:
            if headers:
                use_headers["Authorization"] = "Bearer " + access_token
            else:
                use_headers = {"Authorization": "Bearer " + access_token}

        if _DEBUG_REQUEST:
            print("# ---")
            print(f"# method={method}")
            print(f"# url={url}")
            print(f"# headers={use_headers}")
            print(f"# params={params}")
            print(f"# data={data}")
            print(f"# timeout={timeout}")
            print(f"# verify={self.__verify_ssl_cert}")

        expected_codes = expected_response_codes if expected_response_codes else [200]
        resp: Optional[requests.Response] = None

        if _DEBUG_REQUEST_TIME:
            request_start: float = time.perf_counter()
        try:
            # Send the request (displaying the request/response)
            # and returning the response, whatever it is.
            resp = requests.request(
                method.upper(),
                url,
                headers=use_headers,
                params=params,
                data=data,
                files=files,
                timeout=timeout,
                verify=self.__verify_ssl_cert,
            )
        except:
            _LOGGER.exception("Request failed")

        # Try and decode the response,
        # replacing with empty dictionary on failure.
        msg: Optional[Dict[Any, Any]] = None
        if resp:
            try:
                msg = resp.json()
            except:
                pass

        if _DEBUG_REQUEST:
            if resp is not None:
                print(f"# request() status_code={resp.status_code} msg={msg}")
            else:
                print("# request() resp=None")

        if _DEBUG_REQUEST_TIME:
            assert request_start
            request_finish: float = time.perf_counter()
            print(f"# request() duration={request_finish - request_start} seconds")

        if resp is None or resp.status_code not in expected_codes:
            return (
                AsApiRv(success=False, msg={"error": f"{error_message} (resp={resp})"}),
                resp,
            )

        return AsApiRv(success=True, msg=msg), resp

    @synchronized
    def set_api_url(self, url: str, *, verify_ssl_cert: bool = True) -> None:
        """Replaces the API URL value, which is otherwise set using
        the ``SQUONK2_ASAPI_URL`` environment variable.

        :param url: The API endpoint, typically **https://example.com/account-server-api**
        :param verify_ssl_cert: Use False to avoid SSL verification in request calls
        """
        assert url
        self.__as_api_url = url
        self.__verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @synchronized
    def get_api_url(self) -> Tuple[str, bool]:
        """Return the API URL and whether validating the SSL layer."""
        return self.__as_api_url, self.__verify_ssl_cert

    @synchronized
    def ping(self, *, timeout_s: int = _READ_TIMEOUT_S) -> AsApiRv:
        """A handy API method that calls the AS API to ensure the server is
        responding.

        :param timeout_s: The underlying request timeout
        """

        return self.get_version(timeout_s=timeout_s)

    @synchronized
    def get_version(self, *, timeout_s: int = _READ_TIMEOUT_S) -> AsApiRv:
        """Returns the AS-API service version.

        :param timeout_s: The underlying request timeout
        """

        return self.__request(
            "GET",
            "/version",
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_available_products(
        self, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> AsApiRv:
        """Returns Products you have access to.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return self.__request(
            "GET",
            "/product",
            access_token=access_token,
            error_message="Failed getting products",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_available_units(
        self, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> AsApiRv:
        """Returns Units (and their Organisations) you have access to.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return self.__request(
            "GET",
            "/unit",
            access_token=access_token,
            error_message="Failed getting units",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_available_assets(
        self,
        access_token: str,
        *,
        scope_id: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns Assets you have access to. If you provide a scope ID
        (a username or a product, unit or org UUID) only assets available in that
        scope will be returned.

        :param access_token: A valid AS API access token
        :param scope_id: Optional scope identity (User or Product, Unit or Org UUID)
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        # Has the user provided a scope ID for the Asset search?
        params: Dict[str, str] = {}
        if scope_id:
            scope: Optional[str] = None
            if _RE_UUID.match(scope_id):
                if scope_id.startswith("product-"):
                    scope = "product_id"
                elif scope_id.startswith("unit-"):
                    scope = "unit_id"
                elif scope_id.startswith("org-"):
                    scope = "org_id"
            else:
                scope = "user_id"
            assert scope
            params[scope] = scope_id

        return self.__request(
            "GET",
            "/asset",
            access_token=access_token,
            params=params,
            error_message="Failed getting assets",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_merchants(
        self,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns Merchants known (registered) with the Account Server.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return self.__request(
            "GET",
            "/merchant",
            access_token=access_token,
            error_message="Failed getting merchants",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_product(
        self,
        access_token: str,
        *,
        product_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns details for a given Product.

        :param access_token: A valid AS API access token
        :product_id: The UUID of the Product
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_id

        return self.__request(
            "GET",
            f"/product/{product_id}",
            access_token=access_token,
            error_message="Failed getting product",
            timeout=timeout_s,
        )[0]

    @synchronized
    def get_product_charges(
        self,
        access_token: str,
        *,
        product_id: str,
        from_: Optional[date] = None,
        until: Optional[date] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns charges for a given Product. If from and until are omitted
        charges for the current billing period are returned.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :product_id: The UUID of the Product
        :from_: An option date where charges are to start (inclusive)
        :until: An option date where charges are to end (exclusive)
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_id

        params: Dict[str, Any] = {}
        if from_:
            params["from"] = str(from_)
        if until:
            params["until"] = str(until)

        return self.__request(
            "GET",
            f"/product/{product_id}/charges",
            access_token=access_token,
            params=params,
            error_message="Failed getting product",
            timeout=timeout_s,
        )[0]
