import pytest
from app.rate_limit import RateLimiter
from fastapi import HTTPException, Request


def _fake_request(ip: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "client": (ip, 12345),
        "headers": headers,
    }
    return Request(scope)


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    request = _fake_request("1.1.1.1")
    for _ in range(3):
        limiter.check(request)  # should not raise


def test_blocks_the_request_that_exceeds_the_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    request = _fake_request("1.1.1.1")
    limiter.check(request)
    limiter.check(request)
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(request)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_tracks_different_ips_independently():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check(_fake_request("1.1.1.1"))
    limiter.check(_fake_request("2.2.2.2"))  # different IP, should not raise


def test_window_resets_after_it_elapses(monkeypatch):
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    request = _fake_request("1.1.1.1")

    times = iter([0.0, 0.0, 61.0])
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: next(times))

    limiter.check(request)  # t=0, consumes the slot
    with pytest.raises(HTTPException):
        limiter.check(request)  # t=0, still within window
    limiter.check(request)  # t=61, window has elapsed, should not raise


def test_missing_client_falls_back_to_a_shared_bucket():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    scope = {"type": "http", "client": None, "headers": []}
    request = Request(scope)
    limiter.check(request)  # should not raise


def test_tracks_clients_behind_the_same_proxy_independently_via_x_forwarded_for():
    # Both requests arrive from the same proxy IP (as they would on Railway/
    # HF Spaces), but distinct real clients set distinct X-Forwarded-For
    # values. Without honoring the header, these would collapse into one
    # shared bucket; with it, each real client gets its own.
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check(_fake_request("10.0.0.1", forwarded_for="9.9.9.9"))
    limiter.check(_fake_request("10.0.0.1", forwarded_for="8.8.8.8"))  # different real client


def test_uses_the_leftmost_x_forwarded_for_entry_as_the_original_client():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    request = _fake_request("10.0.0.1", forwarded_for="9.9.9.9, 10.0.0.2, 10.0.0.1")
    limiter.check(request)
    with pytest.raises(HTTPException):
        # Same leftmost entry again -> same bucket -> blocked.
        limiter.check(_fake_request("10.0.0.1", forwarded_for="9.9.9.9, 10.0.0.3"))


def test_falls_back_to_client_host_when_no_forwarded_header():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check(_fake_request("1.1.1.1"))
    with pytest.raises(HTTPException):
        limiter.check(_fake_request("1.1.1.1"))


def test_default_sweep_interval_is_1000():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    assert limiter.sweep_interval == 1000


def test_idle_keys_are_evicted_on_periodic_sweep(monkeypatch):
    # Use a small sweep_interval (constructor param) instead of looping 1000
    # times; the production default of 1000 is asserted separately above.
    limiter = RateLimiter(max_requests=5, window_seconds=60, sweep_interval=2)

    times = iter([0.0, 61.0])
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: next(times))

    limiter.check(_fake_request("1.1.1.1"))  # t=0, then goes idle
    limiter.check(_fake_request("2.2.2.2"))  # t=61, 2nd call triggers sweep

    # 1.1.1.1's last hit (t=0) is now 61s old, older than the 60s window,
    # so it must be evicted; 2.2.2.2 just hit and must be kept.
    assert "1.1.1.1" not in limiter._hits
    assert "2.2.2.2" in limiter._hits
