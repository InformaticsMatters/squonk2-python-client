#!/usr/bin/env python
"""Get and print a Squonk2 access token.
"""
import argparse
import os

from squonk2.auth import Auth

# Username and password are taken from environment variables...
keycloak_user: str = os.environ["SQUONK2_KEYCLOAK_USER"]
keycloak_user_password: str = os.environ["SQUONK2_KEYCLOAK_USER_PASSWORD"]

# Less sensitive information is extracted from the command-line...
parser = argparse.ArgumentParser(
    description="Get a user token. SQUONK2_KEYCLOAK_USER and"
    " SQUONK2_KEYCLOAK_USER_PASSWORD must be set."
)
parser.add_argument(
    "--keycloak-hostname", "-k", help='The API URL, i.e. "example.com"', required=True
)
parser.add_argument(
    "--keycloak-realm", "-r", help='The Keycloak realm, i.e. "blob"', required=True
)
parser.add_argument(
    "--keycloak-client-id",
    "-i",
    help='The Keycloak client ID, i.e. "data-manager-api-dev"'
    ' or "account-server-api-dev"',
    required=True,
)
args = parser.parse_args()

# Now get an API token.
# It should be valid for the remainder of the utility...
token: str = Auth.get_access_token(
    keycloak_url="https://" + args.keycloak_hostname + "/auth",
    keycloak_realm=args.keycloak_realm,
    keycloak_client_id=args.keycloak_client_id,
    username=keycloak_user,
    password=keycloak_user_password,
)

assert token
print(token)
