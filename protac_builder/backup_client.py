from __future__ import annotations

import os
import time
from typing import Any

import requests


DEFAULT_TIMEOUT_SECONDS = 2.5
DEFAULT_READ_TIMEOUT_SECONDS = 3.5


def _env_float(name: str, default: float, minimum: float = 0.1) -> float:
    try:
        return max(float(os.environ.get(name, str(default))), minimum)
    except (TypeError, ValueError):
        return default


def _backup_token() -> str:
    return os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()


def _event_url() -> str:
    return os.environ.get("PROTAC_BACKUP_URL", "").strip().rstrip("/")




def _bulk_events_url() -> str:
    explicit = os.environ.get("PROTAC_BACKUP_BULK_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    event_url = _event_url()
    if event_url.endswith("/backup/protac-event"):
        return event_url[: -len("/backup/protac-event")] + "/backup/protac-events"
    return ""

def _summary_url() -> str:
    explicit = os.environ.get("PROTAC_BACKUP_SUMMARY_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    event_url = _event_url()
    if event_url.endswith("/backup/protac-event"):
        return event_url[: -len("/backup/protac-event")] + "/backup/summary"
    return ""


def _events_url() -> str:
    explicit = os.environ.get("PROTAC_BACKUP_EVENTS_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    event_url = _event_url()
    if event_url.endswith("/backup/protac-event"):
        return event_url[: -len("/backup/protac-event")] + "/backup/events"
    return ""


def _headers() -> dict[str, str]:
    token = _backup_token()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "protac-builder-heroku-backup/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def backup_enabled() -> bool:
    return bool(_event_url() and _backup_token())


def remote_counts_enabled() -> bool:
    raw = os.environ.get("PROTAC_BACKUP_USE_REMOTE_COUNTS", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def backup_event(payload: dict[str, Any]) -> bool:
    """Best-effort write-through event backup.

    This function must never break a user request. It returns False on any
    configuration, network, HTTP, or JSON error.
    """
    url = _event_url()
    token = _backup_token()
    if not url or not token:
        return False

    body = dict(payload or {})
    body.setdefault("app", "protac-builder")
    body.setdefault("runtime", os.environ.get("DYNO", "local"))
    body.setdefault("sent_at_unix", time.time())

    timeout = _env_float("PROTAC_BACKUP_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    try:
        response = requests.post(url, json=body, headers=_headers(), timeout=timeout)
        return 200 <= response.status_code < 300
    except Exception:
        if os.environ.get("PROTAC_BACKUP_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
            import traceback

            traceback.print_exc()
        return False


def get_remote_usage_summary() -> dict[str, Any] | None:
    """Return RANDY-backed usage summary if configured and reachable.

    Returns None when disabled/unconfigured/unreachable so callers can fall back
    to local Heroku runtime logs.
    """
    if not remote_counts_enabled():
        return None
    url = _summary_url()
    token = _backup_token()
    if not url or not token:
        return None

    timeout = _env_float("PROTAC_BACKUP_READ_TIMEOUT_SECONDS", DEFAULT_READ_TIMEOUT_SECONDS)
    try:
        response = requests.get(url, headers=_headers(), timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("ok"):
            return None
        return payload
    except Exception:
        if os.environ.get("PROTAC_BACKUP_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
            import traceback

            traceback.print_exc()
        return None


def get_remote_events(limit: int = 100) -> dict[str, Any] | None:
    url = _events_url()
    token = _backup_token()
    if not url or not token:
        return None

    timeout = _env_float("PROTAC_BACKUP_READ_TIMEOUT_SECONDS", DEFAULT_READ_TIMEOUT_SECONDS)
    try:
        response = requests.get(url, headers=_headers(), params={"limit": int(limit)}, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("ok"):
            return None
        return payload
    except Exception:
        return None


def backup_events(events: list[dict[str, Any]], *, chunk_size: int = 200) -> bool:
    """Best-effort bulk event backup.

    Uses RANDY's /backup/protac-events endpoint when available. This keeps
    batch/CLI runs from making thousands of individual HTTPS requests.
    Falls back to one-by-one backup_event calls only if the bulk URL is not
    configured or the bulk request fails.
    """
    clean_events = [dict(item or {}) for item in (events or []) if isinstance(item, dict)]
    if not clean_events:
        return False

    url = _bulk_events_url()
    token = _backup_token()
    if not url or not token:
        ok = False
        for item in clean_events:
            ok = backup_event(item) or ok
        return ok

    timeout = _env_float("PROTAC_BACKUP_BULK_TIMEOUT_SECONDS", 8.0)
    all_ok = True
    for start in range(0, len(clean_events), max(int(chunk_size), 1)):
        chunk = clean_events[start : start + max(int(chunk_size), 1)]
        wrapped = []
        for item in chunk:
            body = dict(item)
            body.setdefault("app", "protac-builder")
            body.setdefault("runtime", os.environ.get("DYNO", "local"))
            body.setdefault("sent_at_unix", time.time())
            wrapped.append(body)
        try:
            response = requests.post(url, json={"events": wrapped}, headers=_headers(), timeout=timeout)
            if not (200 <= response.status_code < 300):
                all_ok = False
        except Exception:
            all_ok = False
            if os.environ.get("PROTAC_BACKUP_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
                import traceback

                traceback.print_exc()
    return all_ok
