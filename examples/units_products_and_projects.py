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

from squonk2.dm_api import DmApi, DmApiRv
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

if dm_token:
    print("DM token present")
else:
    print("No DM token provided")
    sys.exit(1)

if org_id:
    print("ORG_ID present")
else:
    print("No ORG_ID provided")
    sys.exit(1)

# Create the unit.
as_rv: AsApiRv = AsApi.create_unit(
    as_token,
    org_id=org_id,
    billing_day=8,
    unit_name="Example unit",
)
if not as_rv.success:
    print("Failed to create unit")
    print(as_rv)
    sys.exit(1)
unit_id = as_rv.msg["id"]
print(f"Created Unit '{unit_id}'")

# Create the storage product.
as_rv = AsApi.create_product(
    as_token,
    product_name="Example storage",
    unit_id=unit_id,
    product_type="DATA_MANAGER_STORAGE_SUBSCRIPTION",
    allowance=10,
    limit=10,
)
if not as_rv.success:
    print("Failed to create storage product")
    sys.exit(1)
storage_product_id = as_rv.msg["id"]
print(f"Created Storage Product '{storage_product_id}'")

# Create the Data Tier product.
# We do not set allowances on DT products.
as_rv = AsApi.create_product(
    as_token,
    product_name="Example data tier",
    unit_id=unit_id,
    product_type="DATA_MANAGER_PROJECT_TIER_SUBSCRIPTION",
    flavour="BRONZE",
)
if not as_rv.success:
    print("Failed to create data tier product")
    sys.exit(1)
dt_product_id = as_rv.msg["id"]
print(f"Created DataTier Product '{dt_product_id}'")

# Create a Data Manger Project using the AS DT Product.
dm_rv: DmApiRv = DmApi.create_project(
    dm_token,
    project_name="Example project",
    as_tier_product_id=dt_product_id,
)
if not dm_rv.success:
    print("Failed to create DM project")
    sys.exit(1)
project_id = dm_rv.msg["project_id"]
print(f"Created Project '{project_id}'")

# Now delete the Project, Products and unit

dm_rv = DmApi.delete_project(dm_token, project_id=project_id)
if as_rv.success:
    print("Project deleted")
else:
    print("Failed to delete product")
    sys.exit(1)

as_rv = AsApi.delete_product(as_token, product_id=dt_product_id)
if as_rv.success:
    print("Data Tier Product deleted")
else:
    print("Failed to delete data tier product")
    sys.exit(1)

as_rv = AsApi.delete_product(as_token, product_id=storage_product_id)
if as_rv.success:
    print("Storage Product deleted")
else:
    print("Failed to delete storage product")
    sys.exit(1)

as_rv = AsApi.delete_unit(as_token, unit_id=unit_id)
if as_rv.success:
    print("Unit deleted")
else:
    print("Failed to delete unit")
    sys.exit(1)
