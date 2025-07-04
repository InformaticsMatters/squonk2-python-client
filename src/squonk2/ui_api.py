"""Python utilities to simplify calls to some parts of the Data Manager UI.
"""

import contextlib
from dataclasses import dataclass
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from munch import DefaultMunch
from wrapt import synchronized
import requests


@dataclass
class UiApiRv:
    """The return value from most of the the UiApi class public methods.

    :param success: True if the call was successful, False otherwise.
    :param msg: API request response content
    :param munch_msg: A DefaultMunch object for the API request response content
    :param http_status_code: An HTTPS status code (0 if not available)
    """

    success: bool
    msg: Dict[Any, Any]
    defaultmunch_msg: DefaultMunch
    http_status_code: int


# A common read timeout
_READ_TIMEOUT_S: int = 4

# The UI API URL environment variable,
# You can set the API manually with set_aiu_url() if this is not defined.
_API_URL_ENV_NAME: str = "SQUONK2_UIAPI_URL"
_API_VERIFY_SSL_CERT_ENV_NAME: str = "SQUONK2_UIAPI_VERIFY_SSL_CERT"

# Debug request times?
# If set the duration of each request call is logged.
_DEBUG_REQUEST_TIME: bool = False
# Debug request calls?
# If set the arguments and response of each request call is logged.
_DEBUG_REQUEST: bool = (
    os.environ.get("SQUONK2_API_DEBUG_REQUESTS", "no").lower() == "yes"
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class UiApi:
    """The UiAPI class provides high-level, simplified access to the UI's API.
    You can use the request module directly for finer control. This module
    provides a wrapper around the handling of the request, returning a simplified
    namedtuple response value ``UiApiRv``
    """

    # The default DM API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    __ui_api_url: str = os.environ.get(_API_URL_ENV_NAME, "")
    # Do we expect the DM API to be secure?
    # Normally yes, but this can be disabled using 'set_api_url()'
    __verify_ssl_cert: bool = (
        os.environ.get(_API_VERIFY_SSL_CERT_ENV_NAME, "yes").lower() == "yes"
    )
    # An object to return in DefaultMunch objects
    __undefined: object = object()

    @classmethod
    def __request(
        cls,
        method: str,
        endpoint: str,
        *,
        error_message: str,
        expected_response_codes: Optional[List[int]] = None,
        headers: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        expect_json: bool = False,
        timeout: int = _READ_TIMEOUT_S,
    ) -> Tuple[UiApiRv, Optional[requests.Response]]:
        """Sends a request to the UI API endpoint.

        All the public API methods pass control to this method,
        returning its result to the user.
        """
        assert method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert endpoint
        assert isinstance(expected_response_codes, (type(None), list))

        msg: Dict[Any, Any] = {}
        if not UiApi.__ui_api_url:
            msg = {"error": "No API URL defined"}
            return (
                UiApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, UiApi.__undefined),
                    http_status_code=0,
                ),
                None,
            )

        url: str = UiApi.__ui_api_url + endpoint

        # if we have it, add the access token to the headers,
        # or create a headers block
        use_headers = headers.copy() if headers else {}

        if _DEBUG_REQUEST:
            print("# ---")
            print(f"# method={method}")
            print(f"# url={url}")
            print(f"# headers={use_headers}")
            print(f"# params={params}")
            print(f"# data={data}")
            print(f"# timeout={timeout}")
            print(f"# verify={UiApi.__verify_ssl_cert}")

        expected_codes = expected_response_codes or [200]
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
                verify=UiApi.__verify_ssl_cert,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Request failed")

        # Try and decode the response,
        # replacing with empty dictionary on failure.
        if resp:
            if expect_json:
                with contextlib.suppress(Exception):
                    msg = resp.json()
            else:
                msg = {"text": resp.text}
        http_status_code: int = 0 if resp is None else resp.status_code

        if _DEBUG_REQUEST:
            if resp is not None:
                print(
                    f"# request() status_code={resp.status_code} msg={msg}"
                    f" resp.text={resp.text}"
                )
            else:
                print("# request() resp=None")

        if _DEBUG_REQUEST_TIME:
            assert request_start
            request_finish: float = time.perf_counter()
            print(f"# request() duration={request_finish - request_start} seconds")

        if resp is None or resp.status_code not in expected_codes:
            msg = {"error": f"{error_message} (resp={resp})"}
            return (
                UiApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, UiApi.__undefined),
                    http_status_code=http_status_code,
                ),
                resp,
            )

        return (
            UiApiRv(
                success=True,
                msg=msg,
                defaultmunch_msg=DefaultMunch.fromDict(msg, UiApi.__undefined),
                http_status_code=http_status_code,
            ),
            resp,
        )

    @classmethod
    @synchronized
    def set_api_url(cls, url: str, *, verify_ssl_cert: bool = True) -> None:
        """Sets the API URL value. The user is required to call this before using the
        object.

        :param url: The API endpoint, typically **https://example.com/api**
        :param verify_ssl_cert: Use False to avoid SSL verification in request calls
        """
        assert url
        UiApi.__ui_api_url = url
        UiApi.__verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @classmethod
    @synchronized
    def get_api_url(cls) -> Tuple[str, bool]:
        """Return the API URL and whether validating the SSL layer."""
        return UiApi.__ui_api_url, UiApi.__verify_ssl_cert

    @classmethod
    @synchronized
    def get_version(cls, *, timeout_s: int = _READ_TIMEOUT_S) -> UiApiRv:
        """Returns the UI service version.

        :param timeout_s: The underlying request timeout
        """

        return UiApi.__request(
            "GET",
            "/configuration/ui-version",
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]
