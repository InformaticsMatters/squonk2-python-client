"""Python utilities to simplify calls to some parts of the Account Server API that
interact with **Organisations**, **Units**, **Products** and **Assets**.

.. note::
    The URL to the DM API is automatically picked up from the environment variable
    ``SQUONK2_ASAPI_URL``, expected to be of the form **https://example.com/account-server-api**.
    If the variable isn't set the user must set it programmatically
    using :py:meth:`AsApi.set_api_url()`.
"""
from collections import namedtuple
import logging
import os
import time
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


class AsApi:
    """The AsAPI class provides high-level, simplified access to the AS API.
    You can use the request module directly for finer control. This module
    provides a wrapper around the handling of the request, returning a simplified
    namedtuple response value ``AsApiRv``
    """

    # The default AS API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    __as_api_url: str = os.environ.get(_API_URL_ENV_NAME, "")
    # Do we expect the AS API to be secure?
    # Normally yes, but this can be disabled using 'set_api_url()'
    __verify_ssl_cert: bool = True

    @classmethod
    def __request(
        cls,
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

        if not AsApi.__as_api_url:
            return AsApiRv(success=False, msg={"error": "No API URL defined"}), None

        url: str = AsApi.__as_api_url + endpoint

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
            print(f"# verify={AsApi.__verify_ssl_cert}")

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
                verify=AsApi.__verify_ssl_cert,
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

    @classmethod
    @synchronized
    def set_api_url(cls, url: str, *, verify_ssl_cert: bool = True) -> None:
        """Replaces the API URL value, which is otherwise set using
        the ``SQUONK2_ASAPI_URL`` environment variable.

        :param url: The API endpoint, typically **https://example.com/account-server-api**
        :param verify_ssl_cert: Use False to avoid SSL verification in request calls
        """
        assert url
        AsApi.__as_api_url = url
        AsApi.__verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @classmethod
    @synchronized
    def get_api_url(cls) -> Tuple[str, bool]:
        """Return the API URL and whether validating the SSL layer."""
        return AsApi.__as_api_url, AsApi.__verify_ssl_cert

    @classmethod
    @synchronized
    def ping(cls, *, timeout_s: int = _READ_TIMEOUT_S) -> AsApiRv:
        """A handy API method that calls the AS API to ensure the server is
        responding.

        :param timeout_s: The underlying request timeout
        """

        return AsApi.get_version(timeout_s=timeout_s)

    @classmethod
    @synchronized
    def get_version(cls, *, timeout_s: int = _READ_TIMEOUT_S) -> AsApiRv:
        """Returns the AS-API service version.

        :param timeout_s: The underlying request timeout
        """

        return AsApi.__request(
            "GET",
            "/version",
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]
