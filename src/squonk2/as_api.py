"""Python utilities to simplify calls to some parts of the Account Server API that
interact with **Organisations**, **Units**, **Products** and **Assets**.

.. note::
    The URL to the DM API is automatically picked up from the environment variable
    ``SQUONK2_ASAPI_URL``, expected to be of the form **https://example.com/account-server-api**.
    If the variable isn't set the user must set it programmatically
    using :py:meth:`AsApi.set_api_url()`.
"""

import contextlib
from dataclasses import dataclass
from datetime import date
from enum import Enum
import logging
import os
from pathlib import Path
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from munch import DefaultMunch
from wrapt import synchronized
import requests


@dataclass
class AsApiRv:
    """The return value from most of the the AsApi class public methods.

    :param success: True if the call was successful, False otherwise.
    :param msg: API request response content
    :param munch_msg: A DefaultMunch object for the API request response content
    :param http_status_code: An HTTPS status code (0 if not available)
    """

    success: bool
    msg: Dict[Any, Any]
    defaultmunch_msg: DefaultMunch
    http_status_code: int


class EventStreamFormat(Enum):
    """Enumeration of EventStream formats"""

    JSON_STRING = 1
    PROTOCOL_STRING = 2


class AssetScopeEnum(Enum):
    """Enumeration of Asset scopes"""

    USER = 1
    PRODUCT = 2
    UNIT = 3
    ORGANISATION = 4
    GLOBAL = 5


# The Account Server API URL environment variable,
# You can set the API manually with set_apu_url() if this is not defined.
# The Account Server API URL environment variable,
# You can set the API manually with set_apu_url() if this is not defined.
_API_URL_ENV_NAME: str = "SQUONK2_ASAPI_URL"
_API_VERIFY_SSL_CERT_ENV_NAME: str = "SQUONK2_ASAPI_VERIFY_SSL_CERT"

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

    # The default AS API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    __as_api_url: str = os.environ.get(_API_URL_ENV_NAME, "")
    # Do we expect the AS API to be secure?
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
        assert method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert endpoint
        assert isinstance(expected_response_codes, (type(None), list))

        msg: Dict[Any, Any] = {}
        if not AsApi.__as_api_url:
            msg = {"error": "No API URL defined"}
            return (
                AsApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, AsApi.__undefined),
                    http_status_code=0,
                ),
                None,
            )

        url: str = AsApi.__as_api_url + endpoint

        # if we have it, add the access token to the headers,
        # or create a headers block
        use_headers = headers.copy() if headers else {}
        if access_token:
            if headers:
                use_headers["Authorization"] = f"Bearer {access_token}"
            else:
                use_headers = {"Authorization": f"Bearer {access_token}"}

        if _DEBUG_REQUEST:
            print("# ---")
            print(f"# method={method}")
            print(f"# url={url}")
            print(f"# headers={use_headers}")
            print(f"# params={params}")
            print(f"# data={data}")
            print(f"# files={files}")
            print(f"# timeout={timeout}")
            print(f"# verify={AsApi.__verify_ssl_cert}")

        expected_codes = expected_response_codes or [200]
        resp: Optional[requests.Response] = None

        # For the AS we rely on setting headers
        # and that is achieved with 'json'.
        # But when sending files requests ignores 'json'
        # so if we're sending files we switch to 'data'.
        if files:
            data_payload = data
            json_payload = None
        else:
            data_payload = None
            json_payload = data

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
                data=data_payload,
                json=json_payload,
                files=files,
                timeout=timeout,
                verify=AsApi.__verify_ssl_cert,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Request failed")

        # Try and decode the response,
        # replacing with empty dictionary on failure.
        if resp:
            with contextlib.suppress(Exception):
                msg = resp.json()
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
                AsApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, AsApi.__undefined),
                    http_status_code=http_status_code,
                ),
                resp,
            )

        return (
            AsApiRv(
                success=True,
                msg=msg,
                defaultmunch_msg=DefaultMunch.fromDict(msg, AsApi.__undefined),
                http_status_code=http_status_code,
            ),
            resp,
        )

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

    @classmethod
    @synchronized
    def get_event_stream_version(cls, *, timeout_s: int = _READ_TIMEOUT_S) -> AsApiRv:
        """Returns the AS-API Event Stream Service version.

        :param timeout_s: The underlying request timeout
        """

        return AsApi.__request(
            "GET",
            "/event-stream/version",
            error_message="Failed getting event stream version",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_event_stream(
        cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> AsApiRv:
        """Returns the AS-API Event Stream for a user (if there is one).

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """

        return AsApi.__request(
            "GET",
            "/event-stream",
            access_token=access_token,
            error_message="Failed getting event stream",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_event_stream(
        cls,
        access_token: str,
        *,
        event_format: EventStreamFormat,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates an Event Stream.

        :param access_token: A valid AS API access token
        :param format: The event format enumeration
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert event_format

        data: Dict[str, Any] = {
            "format": event_format.name,
        }

        return AsApi.__request(
            "POST",
            "/event-stream",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed to create event stream",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_event_stream(
        cls,
        access_token: str,
        *,
        event_stream_id: int,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates an Event Stream.

        :param access_token: A valid AS API access token
        :param format: The event format enumeration
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert event_stream_id

        return AsApi.__request(
            "DELETE",
            f"/event-stream/{event_stream_id}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to delete event stream",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_products(
        cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> AsApiRv:
        """Returns Products you have access to.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/product",
            access_token=access_token,
            error_message="Failed getting products",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_units(
        cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> AsApiRv:
        """Returns Units (and their Organisations) you have access to.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/unit",
            access_token=access_token,
            error_message="Failed getting units",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_assets(
        cls,
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

        return AsApi.__request(
            "GET",
            "/asset",
            access_token=access_token,
            params=params,
            error_message="Failed getting assets",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_asset(
        cls,
        access_token: str,
        *,
        name: str,
        description: str,
        scope: AssetScopeEnum,
        content_string: Optional[str] = None,
        content_file: Optional[Path] = None,
        scope_id: Optional[str] = None,
        is_secret: bool = False,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Create an Asset from a string or file (not both)."""

        data = {"name": name, "scope": scope.name, "secret": is_secret}
        if description:
            data["description"] = description
        if scope_id:
            data["scope_id"] = scope_id
        if content_string:
            data["content_string"] = content_string

        files = {}
        if content_file:
            assert content_file.is_file()
            files["content_file"] = (content_file.name, content_file.open(mode="rb"))
        else:
            # We are required to create RequestBody or connexion will barf!
            # But the design prevents the providing of 'content_file' and 'content_string'
            # so we 'trick' the test by providing a 'content_file' (which gives us a RequestBody)
            # but we do not give it a name, which our handler recognizes as 'no file'.
            files["content_file"] = (
                "",
                open(__file__, "rb"),  # pylint: disable=consider-using-with
            )

        return AsApi.__request(
            "POST",
            "/asset",
            access_token=access_token,
            expected_response_codes=[201],
            data=data,
            files=files,
            error_message="Failed creating asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def alter_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        description: Optional[str] = None,
        content_string: Optional[str] = None,
        content_file: Optional[Path] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Alters an Asset. An asset's value can be changed along with its description."""

        data = {}
        if description:
            data["description"] = description
        if content_string:
            data["content_string"] = content_string

        files = {}
        if content_file:
            assert content_file.is_file()
            files["content_file"] = (content_file.name, content_file.open(mode="rb"))
        else:
            # We are required to create RequestBody or connexion will barf!
            # But the design prevents the providing of 'content_file' and 'content_string'
            # so we 'trick' the test by providing a 'content_file' (which gives us a RequestBody)
            # but we do not give it a name, which our handler recognizes as 'no file'.
            files["content_file"] = (
                "",
                open(__file__, "rb"),  # pylint: disable=consider-using-with
            )

        return AsApi.__request(
            "PATCH",
            f"/asset/{asset_id}",
            access_token=access_token,
            expected_response_codes=[200],
            data=data,
            files=files,
            error_message="Failed altering asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Deletes an existing asset"""
        assert asset_id

        return AsApi.__request(
            "DELETE",
            f"/asset/{asset_id}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed deleting asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Disables an existing asset"""
        assert asset_id

        return AsApi.__request(
            "GET",
            f"/asset/{asset_id}",
            access_token=access_token,
            error_message="Failed getting asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def attach_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        m_id: int,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Disables an existing asset"""
        assert asset_id
        assert isinstance(m_id, int)
        assert m_id > 0

        params = {"m_id": m_id}

        return AsApi.__request(
            "PATCH",
            f"/asset/{asset_id}/attach",
            access_token=access_token,
            expected_response_codes=[204],
            params=params,
            error_message="Failed attaching asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def detach_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        m_id: int,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Disables an existing asset"""
        assert asset_id
        assert isinstance(m_id, int)
        assert m_id > 0

        params = {"m_id": m_id}

        return AsApi.__request(
            "PATCH",
            f"/asset/{asset_id}/detach",
            access_token=access_token,
            expected_response_codes=[204],
            params=params,
            error_message="Failed detaching asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def enable_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Disables an existing asset"""
        assert asset_id

        return AsApi.__request(
            "PATCH",
            f"/asset/{asset_id}/enable",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed enabling asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def disable_asset(
        cls,
        access_token: str,
        *,
        asset_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Disables an existing asset"""
        assert asset_id

        return AsApi.__request(
            "PATCH",
            f"/asset/{asset_id}/disable",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed disabling asset",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_merchants(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns Merchants known (registered) with the Account Server.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/merchant",
            access_token=access_token,
            error_message="Failed getting merchants",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_merchant(
        cls,
        access_token: str,
        merchant_id: int,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns the given Merchant.

        :param access_token: A valid AS API access token
        :param merchant_id: A merchant ID
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert merchant_id

        return AsApi.__request(
            "GET",
            f"/merchant/{merchant_id}",
            access_token=access_token,
            error_message="Failed getting merchant",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_product(
        cls,
        access_token: str,
        *,
        product_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns details for a given Product.

        :param access_token: A valid AS API access token
        :param product_id: The UUID of the Product
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_id

        return AsApi.__request(
            "GET",
            f"/product/{product_id}",
            access_token=access_token,
            error_message="Failed getting product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_product_default_storage_cost(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns the default product storage.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/product-default-storage-cost",
            access_token=access_token,
            error_message="Failed getting product default storage cost",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_product_types(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns known product types.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/product-type",
            access_token=access_token,
            error_message="Failed getting product types",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_products_for_unit(
        cls,
        access_token: str,
        *,
        unit_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns Products for a given Unit.

        :param access_token: A valid AS API access token
        :param unit_id: The UUID of the Unit
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id

        return AsApi.__request(
            "GET",
            f"/product/unit/{unit_id}",
            access_token=access_token,
            error_message="Failed getting products",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_products_for_organisation(
        cls,
        access_token: str,
        *,
        org_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns Products for a given Organisation.

        :param access_token: A valid AS API access token
        :param org_id: The UUID of the Organisation
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        return AsApi.__request(
            "GET",
            f"/product/organisation/{org_id}",
            access_token=access_token,
            error_message="Failed getting products",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_product_charges(
        cls,
        access_token: str,
        *,
        product_id: str,
        from_: Optional[date] = None,
        until: Optional[date] = None,
        pbp: Optional[int] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns charges for a given Product. If from and until are omitted
        charges for the current billing period are returned.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :param product_id: The UUID of the Product
        :param from_: An optional date where charges are to start (inclusive)
        :param until: An optional date where charges are to end (exclusive)
        :param pbp: An optional prior billing period
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_id

        params: Dict[str, Any] = {}
        if from_:
            params["from"] = str(from_)
        if until:
            params["until"] = str(until)
        if pbp:
            params["pbp"] = str(pbp)

        return AsApi.__request(
            "GET",
            f"/charges/product/{product_id}",
            access_token=access_token,
            params=params,
            error_message="Failed getting product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_unit(
        cls,
        access_token: str,
        *,
        unit_name: str,
        org_id: str,
        billing_day: int,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates a Unit for a given an Organisation. You need to provide a name
        and billing day - a day in the month to bill all the subscription-based
        products created for the Unit.

        You will need to be a member of the Organisation to use this method.

        :param access_token: A valid AS API access token
        :param unit_name: The name to give the Unit
        :param org_id: The Organisation UUID for the Unit
        :param billing_day: A billing day (1..28)
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_name
        assert org_id
        assert billing_day

        data: Dict[str, Any] = {
            "billing_day": billing_day,
            "name": unit_name,
        }

        return AsApi.__request(
            "POST",
            f"/organisation/{org_id}/unit",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed to create unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_personal_unit(
        cls,
        access_token: str,
        *,
        billing_day: int,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates a Personal Unit

        :param access_token: A valid AS API access token
        :param billing_day: A billing day (1..28)
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert billing_day

        data: Dict[str, Any] = {
            "billing_day": billing_day,
        }

        return AsApi.__request(
            "PUT",
            "/unit",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed to create personal unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_personal_unit(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Deletes a Personal Unit

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "DELETE",
            "/unit",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to delete personal unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def add_user_to_unit(
        cls,
        access_token: str,
        *,
        unit_id: str,
        username: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Adds a User to a Unit.

        You will need admin privileges or be a member of the organisation or unit to do this.

        :param access_token: A valid AS API access token
        :param unit_id: The Unit ID
        :param username: The user to add
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id
        assert username

        return AsApi.__request(
            "PUT",
            f"/unit/{unit_id}/user/{username}",
            access_token=access_token,
            expected_response_codes=[200, 201],
            error_message="Failed to add user to unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def remove_user_from_unit(
        cls,
        access_token: str,
        *,
        unit_id: str,
        username: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Removes a User from a Unit.

        You will need admin privileges or be a member of the organisation or unit to do this.

        :param access_token: A valid AS API access token
        :param unit_id: The Unit ID
        :param username: The user to add
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id
        assert username

        return AsApi.__request(
            "DELETE",
            f"/unit/{unit_id}/user/{username}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to remove user from unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_organisation(
        cls,
        access_token: str,
        *,
        org_name: str,
        org_owner: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates an Organisation. You need to provide a name and an owner.

        You will need admin privileges to do this.

        :param access_token: A valid AS API access token
        :param org_name: The name to give the Organisation
        :param org_owner: The Organisation owner
        :param billing_day: A billing day (1..28)
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_name
        assert org_owner

        data: Dict[str, Any] = {
            "name": org_name,
            "owner": org_owner,
        }

        return AsApi.__request(
            "POST",
            "/organisation",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed to create organisation",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def add_user_to_organisation(
        cls,
        access_token: str,
        *,
        org_id: str,
        username: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Adds a User to an Organisation.

        You will need admin privileges or be a member of the organisation to do this.

        :param access_token: A valid AS API access token
        :param org_id: The Organisation ID
        :param username: The user to add
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id
        assert username

        return AsApi.__request(
            "PUT",
            f"/organisation/{org_id}/user/{username}",
            access_token=access_token,
            expected_response_codes=[200, 201],
            error_message="Failed to add user to organisation",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def remove_user_from_organisation(
        cls,
        access_token: str,
        *,
        org_id: str,
        username: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Removes a User from an Organisation.

        You will need admin privileges or be a member of the organisation to do this.

        :param access_token: A valid AS API access token
        :param org_id: The Organisation ID
        :param username: The user to add
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id
        assert username

        return AsApi.__request(
            "DELETE",
            f"/organisation/{org_id}/user/{username}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to remove user from organisation",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_organisation(
        cls,
        access_token: str,
        *,
        org_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Deletes an Organisation.

        You will need admin privileges to do this.

        :param access_token: A valid AS API access token
        :param org_id: The UUID of the organisation
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        return AsApi.__request(
            "DELETE",
            f"/organisation/{org_id}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to delete organisation",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_organisation(
        cls,
        access_token: str,
        *,
        org_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets an Organisation.

        You will need to be a member of the Organisation to use this method.

        :param access_token: A valid AS API access token
        :param org_id: The Organisation UUID
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        return AsApi.__request(
            "GET",
            f"/organisation/{org_id}",
            access_token=access_token,
            error_message="Failed to get organisation",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_unit(
        cls,
        access_token: str,
        *,
        unit_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets a Unit.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param unit_id: The UUID for the Unit
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id

        return AsApi.__request(
            "GET",
            f"/unit/{unit_id}",
            access_token=access_token,
            error_message="Failed to get unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_organisation_units(
        cls,
        access_token: str,
        *,
        org_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets all Units available to you for an organisation.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param org_id: The Organisation UUID for the Unit
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        return AsApi.__request(
            "GET",
            f"/organisation/{org_id}/unit",
            access_token=access_token,
            error_message="Failed to get organisation units",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_units(
        cls,
        access_token: str,
        *,
        unit_name: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets all Units available to you or by name.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param org_id: The Organisation UUID for the Unit
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if unit_name:
            params["name"] = unit_name

        return AsApi.__request(
            "GET",
            "/unit",
            access_token=access_token,
            params=params,
            error_message="Failed to get organisation units",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_organisations(
        cls,
        access_token: str,
        *,
        org_name: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets all the Organisations you can see. if you provide a name
        the Organisation you name will be returned (if you are a member of it).

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if org_name:
            params["name"] = org_name

        return AsApi.__request(
            "GET",
            "/organisation",
            access_token=access_token,
            params=params,
            error_message="Failed to get organisations",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_organisation_charges(
        cls,
        access_token: str,
        *,
        org_id: str,
        from_: Optional[date] = None,
        until: Optional[date] = None,
        pbp: Optional[int] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Returns charges for a given Organisation. If from and until are omitted
        charges for the current billing period are returned.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :param org_id: The UUID of the Organisation
        :param from_: An optional date where charges are to start (inclusive)
        :param until: An optional date where charges are to end (exclusive)
        :param pbp: An optional prior billing period
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        params: Dict[str, Any] = {}
        if from_:
            params["from"] = str(from_)
        if until:
            params["until"] = str(until)
        if pbp:
            params["pbp"] = str(pbp)

        return AsApi.__request(
            "GET",
            f"/charges/organisation/{org_id}",
            access_token=access_token,
            params=params,
            error_message="Failed getting product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_organisation_users(
        cls,
        access_token: str,
        *,
        org_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets users in an Organisation.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :param org_id: The UUID of the Organisation
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert org_id

        return AsApi.__request(
            "GET",
            f"/organisation/{org_id}/user",
            access_token=access_token,
            error_message="Failed getting users",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_unit_users(
        cls,
        access_token: str,
        *,
        unit_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets users in a Unit.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :param unit_id: The UUID of the Unit
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id

        return AsApi.__request(
            "GET",
            f"/unit/{unit_id}/user",
            access_token=access_token,
            error_message="Failed getting users",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_product(
        cls,
        access_token: str,
        *,
        product_name: str,
        unit_id: str,
        product_type: str,
        allowance: int = 0,
        limit: int = 0,
        flavour: str = "",
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Creates a Product in a Unit.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param product_name: The name to assign to the Product
        :param unit_id: The Unit UUID for the Product
        :param product_type: The product type, e.g. "DATA_MANAGER_PROJECT_TIER_SUBSCRIPTION"
        :param allowance: The coin allowance for the product
        :param limit: The coin limit for the product
        :param flavour: The product flavour (for products that support flavours)
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_name
        assert unit_id
        assert product_type
        assert allowance >= 0
        assert limit >= 0

        data: Dict[str, Any] = {
            "type": product_type,
            "name": product_name,
        }
        if flavour:
            data["flavour"] = flavour
        if allowance:
            data["allowance"] = allowance
        if limit:
            data["limit"] = limit

        return AsApi.__request(
            "POST",
            f"/product/unit/{unit_id}",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed to create product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def alter_product(
        cls,
        access_token: str,
        *,
        product_id: str,
        product_name: Optional[str] = None,
        allowance: Optional[int] = None,
        limit: Optional[int] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Alters an existing a Product."""

        data: Dict[str, Any] = {}
        if product_name is not None:
            data["name"] = product_name
        if allowance is not None:
            data["allowance"] = allowance
        if limit is not None:
            data["limit"] = limit

        return AsApi.__request(
            "PATCH",
            f"/product/{product_id}",
            access_token=access_token,
            data=data,
            expected_response_codes=[200],
            error_message="Failed to alter product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_product(
        cls,
        access_token: str,
        *,
        product_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Deletes a Product in a Unit.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param product_id: The Unit UUID for the Product
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert product_id

        return AsApi.__request(
            "DELETE",
            f"/product/{product_id}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to delete product",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_unit(
        cls,
        access_token: str,
        *,
        unit_id: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Deletes a Product in a Unit.

        You will need to be a member of the Organisation or Unit to use this method.

        :param access_token: A valid AS API access token
        :param unit_id: The Unit UUID for the Product
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert unit_id

        return AsApi.__request(
            "DELETE",
            f"/unit/{unit_id}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed to delete unit",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_account(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> AsApiRv:
        """Gets your User account.

        You will need admin rights on the Account Server to use this method.

        :param access_token: A valid AS API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return AsApi.__request(
            "GET",
            "/user/account",
            access_token=access_token,
            error_message="Failed getting users",
            timeout=timeout_s,
        )[0]
