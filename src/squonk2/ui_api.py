"""Python utilities to simplify calls to some parts of the Data Manager UI.
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

UiApiRv: namedtuple = namedtuple("UiApiRv", "success msg")
"""The return value from most of the the UiApi class public methods.

:param success: True if the call was successful, False otherwise.
:param msg: API request response content
"""

# A common read timeout
_READ_TIMEOUT_S: int = 4

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

    def __init__(self):
        """Constructor"""

        # Set using 'set_api_url()'
        self.__ui_api_url: str = ""
        # Do we expect the DM API to be secure?
        # Normally yes, but this can be disabled using 'set_api_url()'
        self.__verify_ssl_cert: bool = True

    def __request(
        self,
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
        assert method in ["GET", "POST", "PUT", "PATCH", "DELETE"]
        assert endpoint
        assert isinstance(expected_response_codes, (type(None), list))

        if not self.__ui_api_url:
            return UiApiRv(success=False, msg={"error": "No API URL defined"}), None

        url: str = self.__ui_api_url + endpoint

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
            if expect_json:
                try:
                    msg = resp.json()
                except:
                    pass
            else:
                msg = {"text": resp.text}

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
            return (
                UiApiRv(success=False, msg={"error": f"{error_message} (resp={resp})"}),
                resp,
            )

        return UiApiRv(success=True, msg=msg), resp

    @synchronized
    def set_api_url(self, url: str, *, verify_ssl_cert: bool = True) -> None:
        """Sets the API URL value. The user is required to call this before using the
        object.

        :param url: The API endpoint, typically **https://example.com/api**
        :param verify_ssl_cert: Use False to avoid SSL verification in request calls
        """
        assert url
        self.__ui_api_url = url
        self.__verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @synchronized
    def get_api_url(self) -> Tuple[str, bool]:
        """Return the API URL and whether validating the SSL layer."""
        return self.__ui_api_url, self.__verify_ssl_cert

    @synchronized
    def get_version(self, *, timeout_s: int = _READ_TIMEOUT_S) -> UiApiRv:
        """Returns the UI service version.

        :param timeout_s: The underlying request timeout
        """

        return self.__request(
            "GET",
            "/configuration/ui-version",
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]
