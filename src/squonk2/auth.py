"""Python utilities to simplify calls to the authentication mechanism
(Keycloak) for use with the Data Manager and Account Server APIs.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
import urllib

from authlib.jose import jwt
from wrapt import synchronized
import requests

# How old do tokens need to be to re-use them?
# If less than the value provided here, we get a new one.
# Used in get_access_token().
_PRIOR_TOKEN_MIN_AGE_M: int = 1

_LOGGER: logging.Logger = logging.getLogger(__name__)


class Auth:
    """The Auth class provides high-level, simplified access to the
    authentication service (Keycloak).
    """

    # The most recent access token Host and public key.
    # Set during token collection.
    __access_token_realm_url: str = ""
    __access_token_public_key: str = ""

    @classmethod
    @synchronized
    def get_access_token(
        cls,
        *,
        keycloak_url: str,
        keycloak_realm: str,
        keycloak_client_id: str,
        username: str,
        password: str,
        keycloak_client_secret: Optional[str] = None,
        prior_token: Optional[str] = None,
        timeout_s: int = 4,
    ) -> Optional[str]:
        """Gets an access token from the given Keycloak server, realm
        and client ID. The returned token can then be used on the client
        typically providing it in the client's REST header byt setting
        the header's "Authorization" value, e.g. "Authorization: Bearer <token>".

        If keycloak fails to yield a token None is returned, with messages
        written to the log.

        The caller can (is encouraged to) provide a prior token in order to
        reduce token requests on the server. When a ``prior_token`` is provided
        the code only calls keycloak to obtain a new token if the current
        one looks like it will expire (in less than 60 seconds).

        :param keycloak_url: The keycloak server URL, typically **https://example.com/auth**
        :param keycloak_realm: The keycloak realm
        :param keycloak_client_id: The keycloak client ID (Data Manager or Account Server)
        :param keycloak_client_secret: The keycloak client secret (if required by the client)
        :param username: A valid username
        :param password: A valid password
        :param prior_token: An optional prior token. If supplied it will be used
            unless it is about to expire
        :param timeout_s: The underlying request timeout
        """
        assert keycloak_url
        assert keycloak_realm
        assert keycloak_client_id
        assert username
        assert password

        # Do we have the public key for this host/realm?
        # if not grab it now.
        realm_url: str = f"{keycloak_url}/realms/{keycloak_realm}"
        if prior_token and Auth.__access_token_realm_url != realm_url:
            # New realm URL, remember and get the public key
            Auth.__access_token_realm_url = realm_url
            with urllib.request.urlopen(realm_url) as realm_stream:
                response = realm_stream.read()
                public_key = json.loads(response)["public_key"]
            assert public_key
            key = (
                "-----BEGIN PUBLIC KEY-----\n"
                + public_key
                + "\n-----END PUBLIC KEY-----"
            )
            Auth.__access_token_public_key = key.encode("ascii")

        # If a prior token's been supplied,
        # re-use it if there's still time left before expiry.
        if prior_token:
            assert Auth.__access_token_public_key
            decoded_token: Dict[str, Any] = jwt.decode(
                prior_token, Auth.__access_token_public_key
            )
            utc_timestamp: int = int(datetime.now(timezone.utc).timestamp())
            token_remaining_seconds: int = decoded_token["exp"] - utc_timestamp
            if token_remaining_seconds >= _PRIOR_TOKEN_MIN_AGE_M * 60:
                # Plenty of time left on the prior token,
                # return it to the user
                return prior_token

        # No prior token, or not enough time left on the one given.
        # Get a new token.
        data: str = (
            f"client_id={keycloak_client_id}"
            f"&grant_type=password"
            f"&username={username}"
            f"&password={password}"
        )
        if keycloak_client_secret:
            data += f"&client_secret={keycloak_client_secret}"
        headers: Dict[str, Any] = {"Content-Type": "application/x-www-form-urlencoded"}
        url = f"{realm_url}/protocol/openid-connect/token"

        try:
            resp: requests.Response = requests.post(
                url, headers=headers, data=data, timeout=timeout_s
            )
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Failed to get response from Keycloak")
            return None

        if resp.status_code not in [200]:
            _LOGGER.error(
                "Failed to get token status_code=%s text=%s",
                resp.status_code,
                resp.text,
            )
            return None

        assert "access_token" in resp.json()
        return resp.json()["access_token"]
