from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from .paths import HUNTER_JOBS_DIR, WARHEAD_HUNTER_IMPORTS_DIR


SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
WARHEAD_FILE_SUFFIXES = (".pdb", ".sdf", ".svg", ".json")


class WarheadJobIdError(ValueError):
    pass


def normalize_job_id(job_id: str) -> str:
    clean = str(job_id or "").strip()
    if not SAFE_JOB_ID_RE.fullmatch(clean):
        raise WarheadJobIdError("Invalid job_id. Use only letters, numbers, underscores, and hyphens.")
    return clean


def _configured_dirs() -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    for env_name in ("TARGET_BUILDER_JOBS_DIR", "WARHEAD_HUNTER_JOBS_DIR"):
        value = os.environ.get(env_name, "").strip()
        if value:
            sources.append((env_name, Path(value).expanduser()))
    sources.append(("runtime_cache", WARHEAD_HUNTER_IMPORTS_DIR))
    sources.append(("static_hunter_jobs_dev_fallback", HUNTER_JOBS_DIR))
    return sources


def checked_source_names(include_remote: bool = True) -> list[str]:
    names = [name for name, _path in _configured_dirs()]
    if include_remote and os.environ.get("WARHEAD_HUNTER_JOB_API_BASE", "").strip():
        names.append("WARHEAD_HUNTER_JOB_API_BASE")
    return names


def available_local_job_ids(limit: int = 10) -> list[str]:
    ids: set[str] = set()
    for _name, base in _configured_dirs():
        if not base.is_dir():
            continue
        ids.update(item.name for item in base.iterdir() if item.is_dir() and SAFE_JOB_ID_RE.fullmatch(item.name))
    return sorted(ids)[:limit]


def _copy_job_files(source_dir: Path, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for root, _dirs, files in os.walk(source_dir):
        for filename in files:
            if filename in seen or not filename.lower().endswith(WARHEAD_FILE_SUFFIXES):
                continue
            source = Path(root) / filename
            destination = cache_dir / filename
            try:
                shutil.copy2(source, destination)
                seen.add(filename)
            except Exception:
                continue


def resolve_job_dir(job_id: str, *, cache_external: bool = True) -> dict[str, Any] | None:
    clean = normalize_job_id(job_id)
    cache_dir = WARHEAD_HUNTER_IMPORTS_DIR / clean
    for source_name, base in _configured_dirs():
        job_dir = base / clean
        if not job_dir.is_dir():
            continue
        if cache_external and source_name in {"TARGET_BUILDER_JOBS_DIR", "WARHEAD_HUNTER_JOBS_DIR"}:
            _copy_job_files(job_dir, cache_dir)
            if cache_dir.is_dir():
                return {"job_dir": cache_dir, "source": f"{source_name}:cached"}
        return {"job_dir": job_dir, "source": source_name}
    return None


def fetch_remote_job(job_id: str, timeout: float = 12.0) -> dict[str, Any] | None:
    clean = normalize_job_id(job_id)
    base = os.environ.get("WARHEAD_HUNTER_JOB_API_BASE", "").strip()
    if not base:
        return None

    url = urljoin(base.rstrip("/") + "/", clean)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise ValueError("Configured Warhead Hunter API did not return JSON.")

    payload = response.json()
    cache_dir = WARHEAD_HUNTER_IMPORTS_DIR / clean
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "remote_payload.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def missing_job_payload(job_id: str, *, debug: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "job_id": job_id,
        "error": "Job not found in configured Warhead Hunter / Target Builder handoff sources.",
        "sources_checked": checked_source_names(),
        "guidance": (
            "For online deployment, configure TARGET_BUILDER_JOBS_DIR, WARHEAD_HUNTER_JOBS_DIR, "
            "WARHEAD_HUNTER_JOB_API_BASE, or equivalent shared persistent storage. Local static/hunter_jobs "
            "is only a development fallback and does not prove whether an online job exists."
        ),
        "available": available_local_job_ids(),
    }
    if debug:
        payload["source_paths_checked"] = [str(path) for _name, path in _configured_dirs()]
    return payload
