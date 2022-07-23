#!/usr/bin/env python
"""Get and print a Squonk2 access token.
"""
import argparse
import os

from squonk2.auth import Auth

# Less sensitive information is extracted from the command-line...
parser = argparse.ArgumentParser(description="Delete All DM Project Instances")
parser.add_argument(
    "--keycloak-hostname", "-k", help='The API URL, i.e. "example.com"', required=True
)
parser.add_argument(
    "--keycloak-realm", "-r", help='The Keycloak realm, i.e. "blob"', required=True
)
parser.add_argument(
    "--keycloak-client-id",
    "-i",
    help='The Keycloak client ID, i.e. "data-manager-api-dev"',
    required=True,
)
args = parser.parse_args()

# Username and password are taken from environment variables...
keycloak_user: str = os.environ["DMAPI_USERNAME"]
keycloak_user_password: str = os.environ["DMAPI_PASSWORD"]

# Now get an API token.
# It should be valid for the remainder of the utility...
token: str = Auth.get_access_token(
    "https://" + args.keycloak_hostname + "/auth",
    args.keycloak_realm,
    args.keycloak_client_id,
    keycloak_user,
    keycloak_user_password,
)

assert token
print(token)
