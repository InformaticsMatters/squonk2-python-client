#!/usr/bin/env python

# Example that illustrates how to use the client get a token that can be used in other examples.
# NOTE: this token has a limited lifespan and you may need to regenerate it at intervals.
#
# To run this set these environment variables (your parameters may differ):
#   export DMAPI_USERNAME=<keycloak username>
#   export DMAPI_PASSWORD=<keycloak password>
#
# Then run like this :
#
#   ./examples/GetToken.py \
#       --keycloak-hostname keycloak.xchem-dev.diamond.ac.uk \
#       --keycloak-realm xchem \
#       --keycloak-client-id data-manager-api-dev
#
# Or set the KEYCLOAK_TOKEN environment variable like this:
#
#   export KEYCLOAK_TOKEN=`./examples/GetToken.py --keycloak-hostname keycloak.xchem-dev.diamond.ac.uk --keycloak-realm xchem --keycloak-client-id data-manager-api-dev`

import argparse
import os

from dm_api.dm_api import DmApi

# Less sensitive information is extracted from the command-line...
parser = argparse.ArgumentParser(description='Delete All DM Project Instances')
parser.add_argument('--keycloak-hostname', '-k',
                    help='The API URL, i.e. "example.com"',
                    required=True)
parser.add_argument('--keycloak-realm', '-r',
                    help='The Keycloak realm, i.e. "blob"',
                    required=True)
parser.add_argument('--keycloak-client-id', '-i',
                    help='The Keycloak client ID, i.e. "data-manager-api-dev"',
                    required=True)
args = parser.parse_args()

# Username and password are taken from environment variables...
keycloak_user: str = os.environ['DMAPI_USERNAME']
keycloak_user_password: str = os.environ['DMAPI_PASSWORD']

# Now get an API token.
# It should be valid for the remainder of the utility...
token: str = DmApi.get_access_token(
    'https://' + args.keycloak_hostname + '/auth',
    args.keycloak_realm,
    args.keycloak_client_id,
    keycloak_user,
    keycloak_user_password,
)

assert token
print(token)
