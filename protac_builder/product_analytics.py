"""Anonymous, first-party product analytics sent to persistent RANDY storage."""
from __future__ import annotations

import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from flask import request

COOKIE_VISITOR = "protac_vid"
COOKIE_SESSION = "protac_sid"
EXCLUDED_PREFIXES = ("/admin", "/api", "/static", "/health", "/robots", "/sitemap", "/llms", "/openapi")


def _base_url() -> str:
    explicit = os.environ.get("PROTAC_ANALYTICS_RANDY_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    current = os.environ.get("ANALYTICS_RANDY_URL", "").strip().rstrip("/")
    return current[: -len("/analytics")] + "/product-analytics" if current.endswith("/analytics") else ""


def _token() -> str:
    return os.environ.get("ANALYTICS_RANDY_TOKEN", "").strip() or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()


def enabled() -> bool:
    return bool(_base_url() and _token())


def _device() -> str:
    ua = request.user_agent.string.lower()
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    return "mobile" if any(value in ua for value in ("mobi", "iphone", "android")) else "desktop"


def _browser() -> str:
    ua = request.user_agent.string
    if "Firefox" in ua: return "Firefox"
    if "Edg" in ua: return "Edge"
    if "Chrome" in ua: return "Chrome"
    if "Safari" in ua: return "Safari"
    return "other"


def _referrer() -> str:
    return (urlparse(request.referrer or "").hostname or "direct").lower()[:255]


def _ids(response):
    visitor = request.cookies.get(COOKIE_VISITOR) or secrets.token_urlsafe(18)
    session = request.cookies.get(COOKIE_SESSION) or secrets.token_urlsafe(18)
    if COOKIE_VISITOR not in request.cookies:
        response.set_cookie(COOKIE_VISITOR, visitor, max_age=60 * 60 * 24 * 400, secure=request.is_secure, httponly=True, samesite="Lax")
    if COOKIE_SESSION not in request.cookies:
        response.set_cookie(COOKIE_SESSION, session, secure=request.is_secure, httponly=True, samesite="Lax")
    return visitor, session


def _deliver(payload: dict[str, Any]) -> None:
    try:
        requests.post(_base_url() + "/event", json=payload, headers={"Authorization": f"Bearer {_token()}", "User-Agent": "protac-builder-product-analytics/1.0"}, timeout=3)
    except requests.RequestException:
        pass


def _emit(event_type: str, visitor_id: str, session_id: str, feature: str = "") -> None:
    if not enabled():
        return
    # Raw IP is transmitted only for optional immediate GeoIP enrichment on RANDY; it is never persisted.
    payload = {"event_id": secrets.token_urlsafe(24), "event_type": event_type, "occurred_at": datetime.now(timezone.utc).isoformat(), "visitor_id": visitor_id, "session_id": session_id, "path": request.path[:240], "referrer": _referrer(), "device": _device(), "browser": _browser(), "feature": feature[:80], "ip_address": request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip() or request.remote_addr or ""}
    threading.Thread(target=_deliver, args=(payload,), daemon=True, name="protac-product-analytics").start()


def track_response(response):
    if request.path.startswith(EXCLUDED_PREFIXES) or response.status_code >= 400:
        return response
    visitor, session = _ids(response)
    if request.method == "GET" and response.mimetype == "text/html":
        _emit("page_view", visitor, session)
        if request.path == "/builder":
            _emit("builder_opened", visitor, session)
    elif request.method == "POST" and request.path in {"/api/protac/generate", "/copy/generate_protac"} and response.status_code < 300:
        _emit("candidate_constructed", visitor, session, "protac_construction")
    return response
