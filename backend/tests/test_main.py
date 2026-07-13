"""CORS wiring and the lifespan-managed scratch-tenant expiry loop."""

import asyncio

import app.main as main_module
import pytest
from app.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# FRONTEND_ORIGIN is read once at process startup (see main.py) — these tests
# verify CORS behavior against whatever origin is actually configured for this
# process, not dynamic reconfiguration, which this app doesn't support (a
# restart is required for env changes, like everywhere else in this project).
def test_cors_allows_configured_frontend_origin():
    api = TestClient(app)

    resp = api.get("/health", headers={"Origin": "http://localhost:3000"})

    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unconfigured_origin():
    api = TestClient(app)

    resp = api.get("/health", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in resp.headers


def test_lifespan_starts_and_stops_cleanly():
    with TestClient(app) as api:
        resp = api.get("/health")
        assert resp.status_code == 200


def test_run_expiry_sweep_logs_and_survives_exceptions(monkeypatch, caplog):
    def _boom(*args, **kwargs):
        raise RuntimeError("qdrant unreachable")

    monkeypatch.setattr(main_module, "expire_scratch_tenants", _boom)

    with caplog.at_level("ERROR"):
        asyncio.run(main_module._run_expiry_sweep())

    assert "expiry sweep failed" in caplog.text.lower()


def test_expiry_loop_runs_sweep_repeatedly_with_the_configured_interval(monkeypatch):
    call_count = 0
    sleep_calls: list[float] = []

    async def _fake_sweep() -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError

    async def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(main_module, "_run_expiry_sweep", _fake_sweep)
    monkeypatch.setattr(main_module.asyncio, "sleep", _fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main_module._expiry_loop())

    assert call_count == 3
    assert sleep_calls == [
        main_module.EXPIRY_INTERVAL_SECONDS,
        main_module.EXPIRY_INTERVAL_SECONDS,
    ]
