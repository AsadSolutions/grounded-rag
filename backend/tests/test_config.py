"""app.config: env-driven Settings, plus the static demo-tenant metadata
GET /api/tenants/demo serves alongside live Qdrant document counts."""

import pytest

from app.config import DEMO_TENANTS, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_frontend_origin_defaults_to_localhost_3000(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)

    assert get_settings().frontend_origin == "http://localhost:3000"


def test_frontend_origin_reads_from_env(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://groundedrag.example.com")

    assert get_settings().frontend_origin == "https://groundedrag.example.com"


def test_demo_tenants_metadata_matches_protected_tenant_ids():
    ids = {meta.id for meta in DEMO_TENANTS}

    assert ids == set(get_settings().protected_tenant_ids)


def test_demo_tenant_metadata_is_non_empty():
    for meta in DEMO_TENANTS:
        assert meta.name
        assert meta.description
        assert meta.suggested_question
