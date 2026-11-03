"""Deployment settings: per-IP rate limit on Gemini endpoints, demo flag, serving the frontend."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import rate_limit


def limited_client(monkeypatch, per_minute=2, per_day=3, trust_proxy=False):
    monkeypatch.setattr(rate_limit, "LIMITER", rate_limit.RateLimiter(True, per_minute, per_day, trust_proxy))
    app = FastAPI()
    rate_limit.install(app)
    app.post("/api/ask")(lambda: {"ok": True})
    app.post("/api/documents/abc/summarize")(lambda: {"ok": True})
    app.post("/api/schemes/match")(lambda: {"ok": True})
    return TestClient(app)


def test_off_by_default(monkeypatch):
    for name in ("RATE_LIMIT_ENABLED", "RATE_LIMIT_PER_MINUTE", "RATE_LIMIT_PER_DAY", "RATE_LIMIT_TRUST_PROXY"):
        monkeypatch.delenv(name, raising=False)
    assert rate_limit.RateLimiter.from_env().enabled is False


def test_settings_come_from_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "7")
    monkeypatch.setenv("RATE_LIMIT_PER_DAY", "70")
    limiter = rate_limit.RateLimiter.from_env()
    assert (limiter.enabled, limiter.per_minute, limiter.per_day) == (True, 7, 70)


def test_per_minute_limit_returns_a_friendly_429(monkeypatch):
    client = limited_client(monkeypatch)
    assert client.post("/api/ask").status_code == 200
    assert client.post("/api/documents/abc/summarize").status_code == 200  # same IP, shared budget
    blocked = client.post("/api/ask")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == rate_limit.MINUTE_MESSAGE
    assert blocked.headers["Retry-After"] == "60"
    assert client.post("/api/schemes/match").status_code == 200  # no Gemini: never limited


def test_per_day_limit():
    limiter = rate_limit.RateLimiter(True, per_minute=10, per_day=3, trust_proxy=False)
    assert [limiter.check("1.2.3.4", now=t) for t in (0, 100, 200)] == [None, None, None]
    assert limiter.check("1.2.3.4", now=300) == rate_limit.DAY_MESSAGE
    assert limiter.check("5.6.7.8", now=300) is None  # per IP
    assert limiter.check("1.2.3.4", now=86400 + 1) is None  # the day window moves on


def test_forwarded_for_is_used_only_when_trusted(monkeypatch):
    client = limited_client(monkeypatch, per_minute=1, trust_proxy=False)
    assert client.post("/api/ask", headers={"X-Forwarded-For": "9.9.9.1"}).status_code == 200
    assert client.post("/api/ask", headers={"X-Forwarded-For": "9.9.9.2"}).status_code == 429  # header ignored

    client = limited_client(monkeypatch, per_minute=1, trust_proxy=True)
    assert client.post("/api/ask", headers={"X-Forwarded-For": "9.9.9.1, 10.0.0.1"}).status_code == 200
    assert client.post("/api/ask", headers={"X-Forwarded-For": "9.9.9.2"}).status_code == 200


def test_main_app_limits_its_gemini_endpoints(monkeypatch):
    monkeypatch.setattr(rate_limit, "LIMITER", rate_limit.RateLimiter(True, per_minute=1, per_day=100, trust_proxy=False))
    client = TestClient(main.app)
    client.post("/api/scam-check", json={})
    assert client.post("/api/scam-check", json={}).status_code == 429
    assert client.get("/api/health").status_code == 200
    for path in ("/api/ask", "/api/transcribe", "/api/scam-check", "/api/documents/extract-facts", "/api/documents/x1/summarize"):
        assert rate_limit.is_limited("POST", path), path


def test_site_config_reports_the_demo_flag(monkeypatch):
    client = TestClient(main.app)
    monkeypatch.delenv("DEMO_DEPLOYMENT", raising=False)
    assert client.get("/api/site-config").json() == {"demoDeployment": False}
    monkeypatch.setenv("DEMO_DEPLOYMENT", "true")
    assert client.get("/api/site-config").json() == {"demoDeployment": True}


def test_frontend_is_served_only_when_enabled(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>Legal Aid AI</title>", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    monkeypatch.setenv("SERVE_FRONTEND", "true")
    served = importlib.reload(main)
    try:
        client = TestClient(served.app)
        assert "Legal Aid AI" in client.get("/").text
        assert client.get("/api/health").json()["status"] == "ok"  # API routes keep priority
    finally:
        monkeypatch.delenv("SERVE_FRONTEND")
        importlib.reload(main)
    assert TestClient(main.app).get("/").status_code == 404  # default: not served
