from __future__ import annotations

import os
import threading
import time
from typing import Any

import requests


DEFAULT_TIMEOUT_SECONDS = 2.5
DEFAULT_READ_TIMEOUT_SECONDS = 3.5
DEFAULT_BULK_TIMEOUT_SECONDS = 3.0
DEFAULT_BULK_CHUNK_SIZE = 1000


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(int(os.environ.get(name, str(default))), minimum)
    except (TypeError, ValueError):
        return default



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


def _detail_backup_mode() -> str:
    """Return sync/async/off for high-volume detailed component backups.

    Default is async so batch ZIP responses are not held hostage by RANDY/Funnel
    network time. Set PROTAC_BACKUP_DETAIL_MODE=sync only for debugging.
    """
    mode = os.environ.get("PROTAC_BACKUP_DETAIL_MODE", "async").strip().lower()
    if mode in {"0", "false", "no", "off", "disabled"}:
        return "off"
    if mode in {"sync", "synchronous", "blocking"}:
        return "sync"
    return "async"


def _prepare_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean_events = []
    for item in events or []:
        if not isinstance(item, dict):
            continue
        body = dict(item)
        body.setdefault("app", "protac-builder")
        body.setdefault("runtime", os.environ.get("DYNO", "local"))
        body.setdefault("sent_at_unix", time.time())
        clean_events.append(body)
    return clean_events


def backup_events(events: list[dict[str, Any]], *, chunk_size: int | None = None) -> bool:
    """Best-effort bulk event backup.

    Uses RANDY's /backup/protac-events endpoint when available. This function is
    still synchronous, so high-volume request handlers should call
    backup_events_async() instead.
    """
    clean_events = _prepare_events(events)
    if not clean_events:
        return False

    url = _bulk_events_url()
    token = _backup_token()
    if not url or not token:
        return False

    actual_chunk_size = chunk_size or _env_int("PROTAC_BACKUP_BULK_CHUNK_SIZE", DEFAULT_BULK_CHUNK_SIZE)
    timeout = _env_float("PROTAC_BACKUP_BULK_TIMEOUT_SECONDS", DEFAULT_BULK_TIMEOUT_SECONDS)
    all_ok = True

    for start in range(0, len(clean_events), max(int(actual_chunk_size), 1)):
        chunk = clean_events[start : start + max(int(actual_chunk_size), 1)]
        try:
            response = requests.post(url, json={"events": chunk}, headers=_headers(), timeout=timeout)
            if not (200 <= response.status_code < 300):
                all_ok = False
        except Exception:
            all_ok = False
            if os.environ.get("PROTAC_BACKUP_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
                import traceback

                traceback.print_exc()
    return all_ok


def backup_events_async(events: list[dict[str, Any]], *, chunk_size: int | None = None) -> bool:
    """Fire-and-forget detailed backup for large batch/CLI runs.

    Returns immediately after starting a daemon thread. The live ZIP/API response
    should not wait for RANDY. If async is disabled by config, this can fall back
    to sync or off.
    """
    mode = _detail_backup_mode()
    if mode == "off":
        return False

    clean_events = _prepare_events(events)
    if not clean_events:
        return False

    if mode == "sync":
        return backup_events(clean_events, chunk_size=chunk_size)

    thread = threading.Thread(
        target=backup_events,
        kwargs={"events": clean_events, "chunk_size": chunk_size},
        name="protac-randy-backup",
        daemon=True,
    )
    try:
        thread.start()
        return True
    except Exception:
        if os.environ.get("PROTAC_BACKUP_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
            import traceback

            traceback.print_exc()
        return False
