import pytest
from fastapi import HTTPException

from app.tenant_guard import ensure_tenant_is_writable, is_protected_tenant


def test_demo_tenants_are_protected():
    assert is_protected_tenant("demo-acme-legal") is True
    assert is_protected_tenant("demo-techcorp") is True


def test_scratch_tenant_is_not_protected():
    assert is_protected_tenant("scratch-abc123") is False


def test_ensure_tenant_is_writable_raises_403_for_protected_tenant():
    with pytest.raises(HTTPException) as exc_info:
        ensure_tenant_is_writable("demo-acme-legal")

    assert exc_info.value.status_code == 403
    assert "demo-acme-legal" in exc_info.value.detail


def test_ensure_tenant_is_writable_is_silent_for_scratch_tenant():
    ensure_tenant_is_writable("scratch-abc123")  # must not raise
