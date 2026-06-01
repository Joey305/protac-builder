from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import requests

from .paths import WARHEAD_HUNTER_IMPORTS_DIR


SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
WARHEAD_FILE_SUFFIXES = (".pdb", ".sdf", ".svg", ".json")


class WarheadJobIdError(ValueError):
    pass


def normalize_job_id(job_id: str) -> str:
    clean = str(job_id or "").strip()
    if not SAFE_JOB_ID_RE.fullmatch(clean):
        raise WarheadJobIdError("Invalid job_id. Use only letters, numbers, underscores, and hyphens.")
    return clean


def normalize_safe_warhead_file_ref(value: str) -> str:
    clean = str(value or "").strip().replace("\\", "/")
    if not clean:
        raise WarheadJobIdError("Invalid hunter job file reference.")
    if clean.startswith("/") or clean.startswith("~") or clean.startswith("//"):
        raise WarheadJobIdError("Invalid hunter job file reference.")
    if re.match(r"^[A-Za-z]:", clean):
        raise WarheadJobIdError("Invalid hunter job file reference.")

    parts = clean.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise WarheadJobIdError("Invalid hunter job file reference.")

    suffix = Path(parts[-1]).suffix.lower()
    if suffix not in WARHEAD_FILE_SUFFIXES:
        raise WarheadJobIdError("Invalid hunter job file reference.")

    return "/".join(parts)


def extract_safe_warhead_file_ref(value: Any) -> str | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    candidate = raw.replace("\\", "/")
    parsed = urlparse(candidate)

    if parsed.scheme or parsed.netloc:
        candidate = parsed.path or ""
    if candidate.startswith("/"):
        marker = "/file/"
        lower = candidate.lower()
        idx = lower.find(marker)
        if idx >= 0:
            candidate = candidate[idx + len(marker):]
        else:
            candidate = candidate.lstrip("/")

    candidate = unquote(candidate)

    try:
        return normalize_safe_warhead_file_ref(candidate)
    except WarheadJobIdError:
        return None


def _remote_base() -> str:
    return os.environ.get("WARHEAD_HUNTER_JOB_API_BASE", "").strip().rstrip("/")


def _remote_token() -> str:
    return (
        os.environ.get("WARHEAD_HUNTER_JOB_API_TOKEN", "").strip()
        or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()
    )


def _remote_headers() -> dict[str, str]:
    headers = {
        "User-Agent": "protac-builder-warhead-import/1.0",
    }
    token = _remote_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def remote_job_api_configured() -> bool:
    return bool(_remote_base())

def fetch_remote_job(job_id: str, timeout: float = 12.0) -> dict[str, Any] | None:
    clean = normalize_job_id(job_id)
    base = _remote_base()

    if not base:
        return None

    url = urljoin(base.rstrip("/") + "/", clean)

    response = requests.get(
        url,
        headers=_remote_headers(),
        timeout=timeout,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise ValueError("Configured Warhead Hunter API did not return JSON.")

    payload = response.json()

    cache_dir = WARHEAD_HUNTER_IMPORTS_DIR / clean
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "remote_payload.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return payload


def fetch_remote_job_diagnostics(job_id: str, timeout: float = 12.0) -> dict[str, Any]:
    clean = normalize_job_id(job_id)
    base = _remote_base()
    result: dict[str, Any] = {
        "configured": bool(base),
        "attempted": False,
        "status_code": None,
        "payload": None,
        "error": None,
        "debug_hint": "",
    }

    if not base:
        result["error"] = "remote_not_configured"
        result["debug_hint"] = "WARHEAD_HUNTER_JOB_API_BASE is not configured."
        return result

    url = urljoin(base.rstrip("/") + "/", clean)
    result["attempted"] = True

    try:
        response = requests.get(
            url,
            headers=_remote_headers(),
            timeout=timeout,
        )
        result["status_code"] = response.status_code

        if response.status_code == 404:
            result["error"] = "remote_not_found"
            result["debug_hint"] = "Remote API returned 404 for this job ID."
            return result

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            result["error"] = "remote_non_json"
            result["debug_hint"] = "Configured Warhead Hunter API did not return JSON."
            return result

        payload = response.json()
        cache_dir = WARHEAD_HUNTER_IMPORTS_DIR / clean
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "remote_payload.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

        result["payload"] = payload
        result["debug_hint"] = "Remote API returned a JSON payload."
        return result
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        result["status_code"] = status_code
        result["error"] = "remote_http_error"
        result["debug_hint"] = f"Remote API returned HTTP {status_code or 502}."
        return result
    except requests.RequestException as exc:
        result["error"] = "remote_request_error"
        result["debug_hint"] = str(exc) or "Remote request failed."
        return result
    except ValueError as exc:
        result["error"] = "remote_payload_error"
        result["debug_hint"] = str(exc) or "Remote payload could not be parsed."
        return result


def fetch_remote_job_file(job_id: str, filename: str, timeout: float = 20.0) -> tuple[bytes, str]:
    clean = normalize_job_id(job_id)
    safe_name = normalize_safe_warhead_file_ref(filename)

    base = _remote_base()
    if not base:
        raise FileNotFoundError("WARHEAD_HUNTER_JOB_API_BASE is not configured.")

    quoted_name = quote(safe_name, safe="/")
    url = urljoin(base.rstrip("/") + "/", f"{clean}/file/{quoted_name}")

    response = requests.get(
        url,
        headers=_remote_headers(),
        timeout=timeout,
    )
    response.raise_for_status()

    return response.content, response.headers.get("content-type", "application/octet-stream")


def missing_job_payload(job_id: str, *, debug: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "job_id": job_id,
        "error": "Remote Warhead Hunter handoff is not configured on this server.",
        "status": "not_found",
        "source_policy": "remote_only",
        "local_lookup": "disabled",
        "sources_checked": ["WARHEAD_HUNTER_JOB_API_BASE"] if remote_job_api_configured() else [],
        "remote_configured": remote_job_api_configured(),
        "remote_attempted": False,
        "remote_status_code": None,
        "debug_hint": "WARHEAD_HUNTER_JOB_API_BASE is not configured.",
        "guidance": (
            "Configure WARHEAD_HUNTER_JOB_API_BASE and a matching WARHEAD_HUNTER_JOB_API_TOKEN "
            "or PROTAC_BACKUP_TOKEN for remote-only Target Builder / Warhead Hunter import."
        ),
        "available": [],
    }

    return payload
