"""Shared write-protection check for the read-only demo tenants.

The protected set is a config value (app.config.Settings.protected_tenant_ids),
not hardcoded here or in any router — every write endpoint (document upload
today, document delete once it exists) calls ensure_tenant_is_writable
before mutating anything.
"""

from fastapi import HTTPException

from app.config import get_settings


def is_protected_tenant(tenant_id: str) -> bool:
    return tenant_id in get_settings().protected_tenant_ids


def ensure_tenant_is_writable(tenant_id: str) -> None:
    if is_protected_tenant(tenant_id):
        raise HTTPException(
            status_code=403,
            detail=f"Tenant '{tenant_id}' is a read-only demo tenant and cannot be written to.",
        )
