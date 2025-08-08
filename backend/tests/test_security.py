import os
import time
from fastapi.testclient import TestClient


def test_security_headers(client):
    """Test that security headers are present."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("Strict-Transport-Security") == "max-age=63072000; includeSubDomains; preload"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert "Content-Security-Policy" in resp.headers


def test_request_size_limit(client):
    """Test that oversized requests are rejected."""
    large_payload = {"query": "x" * 20000, "k": 5}
    resp = client.post("/search", json=large_payload)
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_rate_limiting(client):
    """Test rate limiting functionality with isolated key."""
    # Make rate-limit test isolated and deterministic
    os.environ["RATE_LIMIT_SEARCH"] = "2/minute"
    os.environ["ALLOW_TEST_RATE_KEY"] = "true"
    headers = {"x-rate-key": "rl-test-unique-key"}

    # First two requests should pass
    for _ in range(2):
        r = client.post("/search", json={"query": "test", "k": 5}, headers=headers)
        assert r.status_code == 200

    # Third should be 429 for this key
    r3 = client.post("/search", json={"query": "test", "k": 5}, headers=headers)
    assert r3.status_code == 429
    assert "rate limit" in r3.json()["detail"].lower()


def test_admin_auth_required(client):
    """Test admin endpoints require authentication."""
    # If ADMIN_TOKEN set, should be 401; otherwise may be 200 or 429 (rate limit)
    resp = client.get("/admin/stats")
    if os.getenv("ADMIN_TOKEN"):
        assert resp.status_code == 401
    else:
        assert resp.status_code in (200, 429)


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert b"http_requests_total" in resp.content