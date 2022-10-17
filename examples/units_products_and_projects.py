#!/usr/bin/env python
"""An example that illustrates how to use the client to create AS
Units and Products and then to create a DM project from the Product.

Required environment: -

    SQUONK2_DMAPI_URL
    SQUONK2_ASAPI_URL
    KEYCLOAK_TOKEN
    KEYCLOAK_TOKEN_AS
    ORG_ID
"""
import os
import sys

from squonk2.as_api import AsApi, AsApiRv

# Squonk2 authentication token and the organisation id
# are taken from environment variables...
as_token: str = os.environ.get("KEYCLOAK_TOKEN_AS")
dm_token: str = os.environ.get("KEYCLOAK_TOKEN")
org_id: str = os.environ.get("ORG_ID")

if as_token:
    print("AS token present")
else:
    print("No AS token provided")
    sys.exit(1)

# if dm_token:
#     print("DM token present")
# else:
#     print("No DM token provided")
#     sys.exit(1)

if org_id:
    print("ORG_ID present")
else:
    print("No ORG_ID provided")
    sys.exit(1)

# Create the unit.
rv: AsApiRv = AsApi.create_unit(as_token, org_id=org_id, billing_day=8, name="Example")
if not rv.success:
    print("Failed to create unit")
    print(rv)
    sys.exit(1)
unit_id = rv.msg["id"]
print(f"Created Unit '{unit_id}'")

# Create the storage product.
rv = AsApi.create_product(
    as_token,
    name="Example storage",
    unit_id=unit_id,
    product_type="DATA_MANAGER_STORAGE_SUBSCRIPTION",
    allowance=10,
    limit=10,
)
if not rv.success:
    print("Failed to create product")
    sys.exit(1)
product_id = rv.msg["id"]
print(f"Created Product '{product_id}'")

# Now delete the Product and unit

rv = AsApi.delete_product(as_token, product_id=product_id)
if rv.success:
    print("Product deleted")
else:
    print("Failed to delete product")
    sys.exit(1)

rv = AsApi.delete_unit(as_token, unit_id=unit_id)
if rv.success:
    print("Unit deleted")
else:
    print("Failed to delete unit")
    sys.exit(1)
