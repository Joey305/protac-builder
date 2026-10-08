"""Anonymous, first-party product analytics sent to persistent RANDY storage."""
from __future__ import annotations

import os
import re
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

# These events describe workflow progress only.  They intentionally never carry
# structures, SMILES, identifiers, filenames, or user-entered scientific data.
EVENTS_BY_REQUEST = {
    ("POST", "/api/protac/generate"): ("candidate_constructed", "candidate_construction"),
    ("POST", "/copy/generate_protac"): ("candidate_constructed", "candidate_construction"),
    ("POST", "/api/protac/download-smiles"): ("candidate_exported", "smiles_export"),
    ("POST", "/copy/download_smiles"): ("candidate_exported", "smiles_export"),
    ("POST", "/api/protac/builder/batch"): ("batch_constructed", "batch_builder"),
    ("POST", "/copy/api/protac/builder/batch"): ("batch_constructed", "batch_builder"),
    ("POST", "/api/deeppk/run"): ("deeppk_completed", "deeppk"),
    ("POST", "/run-drug-analysis"): ("deeppk_completed", "deeppk"),
    ("POST", "/api/admet/run"): ("admet_completed", "admet"),
}

# Browser events are deliberately narrow: they record a completed interface
# action, never a structure, atom index, form value, or scientific identifier.
CLIENT_EVENTS = {
    "component_saved": {"warhead", "linker", "recruiter"},
    "attachment_prepared": {"warhead", "linker", "recruiter"},
    "linker_selected": {"curated", "custom"},
}
HANDOFF_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
HANDOFF_SOURCES = {"warhead_hunter", "e3_ligandalyzer", "vlisemod"}


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
    hostname = (urlparse(request.referrer or "").hostname or "").lower()
    if not hostname:
        return "direct"
    public_hostname = (urlparse(os.environ.get("PROTAC_PUBLIC_BASE_URL", "https://protacbuilder.com")).hostname or "").lower()
    current_hostname = (request.host or "").split(":", 1)[0].lower()
    internal_hosts = {public_hostname, f"www.{public_hostname}" if public_hostname else "", current_hostname}
    return "internal" if hostname in internal_hosts else hostname[:255]


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


def _emit(event_type: str, visitor_id: str, session_id: str, feature: str = "", handoff_id: str = "") -> None:
    if not enabled():
        return
    # Raw IP is transmitted only for optional immediate GeoIP enrichment on RANDY; it is never persisted.
    payload = {"event_id": handoff_id or secrets.token_urlsafe(24), "event_type": event_type, "occurred_at": datetime.now(timezone.utc).isoformat(), "visitor_id": visitor_id, "session_id": session_id, "path": request.path[:240], "referrer": _referrer(), "device": _device(), "browser": _browser(), "feature": feature[:80], "handoff_id": handoff_id, "ip_address": request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip() or request.remote_addr or ""}
    threading.Thread(target=_deliver, args=(payload,), daemon=True, name="protac-product-analytics").start()


def track_response(response):
    if request.path.startswith(EXCLUDED_PREFIXES) or response.status_code >= 400:
        return response
    visitor, session = _ids(response)
    if request.method == "GET" and response.mimetype == "text/html":
        _emit("page_view", visitor, session)
        if request.path == "/builder":
            _emit("builder_opened", visitor, session)
            handoff_id = request.args.get("handoff_id", "").strip()
            source = request.args.get("utm_source", "").strip().lower()
            if HANDOFF_ID.fullmatch(handoff_id) and source in HANDOFF_SOURCES:
                _emit("builder_handoff_arrived", visitor, session, source, handoff_id)
    else:
        event = EVENTS_BY_REQUEST.get((request.method, request.path))
        if event and response.status_code < 300:
            _emit(event[0], visitor, session, event[1])
        elif request.method == "GET" and request.path.startswith(("/api/deeppk/download/", "/api/admet/download/")):
            _emit("report_downloaded", visitor, session, "analysis_report")
        elif request.method == "GET" and request.path in {"/api/protac/builder/template/linkers", "/copy/api/protac/builder/template/linkers"}:
            _emit("template_downloaded", visitor, session, "linker_template")
    return response


def track_client_event(response, event_type: str, feature: str) -> bool:
    """Record an allow-listed browser milestone without accepting user data."""
    allowed_features = CLIENT_EVENTS.get(event_type)
    if not allowed_features or feature not in allowed_features:
        return False
    visitor, session = _ids(response)
    _emit(event_type, visitor, session, feature)
    return True
