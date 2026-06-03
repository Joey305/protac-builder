from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from flask import current_app

_E3_PATH_SUFFIX = "/backup/e3"
_PDB_LIST_CACHE_TTL = float(os.environ.get("E3_PDB_LIST_CACHE_TTL_SECONDS", "120") or "120")
_VARIANT_FALLBACK_LIMIT = max(1, int(os.environ.get("E3_PDB_VARIANT_FALLBACK_LIMIT", "4") or "4"))
_PDB_LIST_CACHE: dict[tuple[str, str], tuple[float, list[str]]] = {}


class E3HandoffRequestError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _remote_token() -> str:
    return (
        os.environ.get("E3_RANDY_TOKEN", "").strip()
        or os.environ.get("RANDY_E3_TOKEN", "").strip()
        or os.environ.get("RANDY_BACKUP_TOKEN", "").strip()
        or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()
    )


def _remote_headers() -> dict[str, str]:
    headers = {"User-Agent": "protac-builder-e3-proxy/1.0"}
    token = _remote_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def normalize_e3_base_url(base: str) -> str:
    raw = str(base or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""

    path = (parsed.path or "").rstrip("/")
    path = re.sub(r"(?:/backup/e3)+$", "", path, flags=re.IGNORECASE)
    path = f"{path}{_E3_PATH_SUFFIX}" if path else _E3_PATH_SUFFIX
    return parsed._replace(path=path, params="", query="", fragment="").geturl().rstrip("/")


def _base_label(base: str) -> str:
    parsed = urlparse(base)
    return parsed.netloc or base


def _validate_ligase_name(ligase: str) -> str:
    clean = str(ligase or "").strip()
    if not clean or not re.fullmatch(r"[A-Za-z0-9_.-]+", clean):
        raise E3HandoffRequestError("Invalid ligase name.")
    return clean


def _validate_pdb_filename(filename: str) -> str:
    clean = str(filename or "").strip()
    if not clean:
        raise E3HandoffRequestError("Missing filename.")
    rel = Path(clean)
    if rel.is_absolute() or ".." in rel.parts or "\\" in clean:
        raise E3HandoffRequestError("Invalid filename.")
    if any(part in {"", "."} for part in rel.parts):
        raise E3HandoffRequestError("Invalid filename.")
    if rel.suffix.lower() != ".pdb":
        raise E3HandoffRequestError("Unsupported file type: only .pdb is allowed.")
    return rel.name


def _stem_without_variant(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"_\d+$", "", stem)


def pdb_candidate_filenames(filename: str) -> list[str]:
    requested = _validate_pdb_filename(filename)
    stem = Path(requested).stem
    ext = Path(requested).suffix.lower()
    variant_match = re.match(r"^(?P<base>.+)_(?P<variant>\d+)$", stem)

    candidates = [requested]
    if variant_match:
        base_stem = variant_match.group("base")
        candidates.append(f"{base_stem}{ext}")
    else:
        base_stem = stem

    for variant in range(1, _VARIANT_FALLBACK_LIMIT + 1):
        candidates.append(f"{base_stem}_{variant}{ext}")

    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)
    return ordered


def _candidate_remote_bases() -> list[str]:
    bases: list[str] = []
    for value in (
        os.environ.get("E3_RANDY_API_BASE", "").strip(),
        os.environ.get("E3_DATA_API_BASE", "").strip(),
        os.environ.get("E3_LIGANDALYZER_API_BASE", "").strip(),
        os.environ.get("PROTAC_CONVERTED_SESSION_BASE", "").strip(),
        "https://e3ligandalyzer-adb8adfde220.herokuapp.com",
        "https://stan.rove-vernier.ts.net",
    ):
        clean = normalize_e3_base_url(value)
        if clean and clean not in bases:
            bases.append(clean)
    return bases


def get_remote_ligase_pdbs(base: str, ligase: str, timeout: float = 20.0) -> list[str] | None:
    cache_key = (base, ligase.lower())
    now = time.time()
    cached = _PDB_LIST_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    url = f"{base}/ligase-pdbs/{quote(ligase, safe='')}"
    try:
        response = requests.get(url, headers=_remote_headers(), timeout=timeout)
        current_app.logger.info(
            "[e3_handoff] listing base=%s ligase=%s status=%s",
            _base_label(base),
            ligase,
            response.status_code,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            current_app.logger.warning(
                "[e3_handoff] listing payload was not a list base=%s ligase=%s",
                _base_label(base),
                ligase,
            )
            return None
        files = [str(item).strip() for item in payload if str(item).strip()]
        _PDB_LIST_CACHE[cache_key] = (now + max(0.0, _PDB_LIST_CACHE_TTL), files)
        return files
    except requests.RequestException as exc:
        current_app.logger.warning(
            "[e3_handoff] listing request failed base=%s ligase=%s error=%s",
            _base_label(base),
            ligase,
            exc,
        )
        return None
    except ValueError as exc:
        current_app.logger.warning(
            "[e3_handoff] listing decode failed base=%s ligase=%s error=%s",
            _base_label(base),
            ligase,
            exc,
        )
        return None


def resolve_remote_pdb_filename(base: str, ligase: str, requested_filename: str, timeout: float = 20.0) -> str | None:
    remote_files = get_remote_ligase_pdbs(base, ligase, timeout=timeout)
    if not remote_files:
        return None

    requested_lower = requested_filename.lower()
    by_lower = {name.lower(): name for name in remote_files}
    if requested_lower in by_lower:
        return by_lower[requested_lower]

    for candidate in pdb_candidate_filenames(requested_filename):
        actual = by_lower.get(candidate.lower())
        if actual:
            return actual

    core = _stem_without_variant(requested_filename).lower()
    variant_matches = [
        name
        for name in remote_files
        if name.lower().endswith(".pdb") and _stem_without_variant(name).lower() == core
    ]
    if not variant_matches:
        return None

    for candidate in pdb_candidate_filenames(f"{core}.pdb"):
        actual = by_lower.get(candidate.lower())
        if actual:
            return actual
    return sorted(variant_matches, key=lambda item: item.lower())[0]


def fetch_remote_ligase_pdb(ligase: str, filename: str, timeout: float = 20.0) -> tuple[bytes, str]:
    clean_ligase = _validate_ligase_name(ligase)
    requested_filename = _validate_pdb_filename(filename)
    last_response: requests.Response | None = None
    last_error: requests.RequestException | None = None
    bases = _candidate_remote_bases()
    candidate_names = pdb_candidate_filenames(requested_filename)

    current_app.logger.info(
        "[e3_handoff] request ligase=%s filename=%s candidate_bases=%s candidates=%s token_present=%s",
        clean_ligase,
        requested_filename,
        [_base_label(base) for base in bases],
        candidate_names,
        bool(_remote_token()),
    )

    for base in bases:
        resolved_name = resolve_remote_pdb_filename(base, clean_ligase, requested_filename, timeout=timeout)
        names_to_try = [name for name in [resolved_name, *candidate_names] if name]
        deduped_names: list[str] = []
        seen_names: set[str] = set()
        for name in names_to_try:
            lowered = name.lower()
            if lowered in seen_names:
                continue
            seen_names.add(lowered)
            deduped_names.append(name)
        current_app.logger.info(
            "[e3_handoff] base=%s ligase=%s requested=%s resolved=%s candidates=%s",
            _base_label(base),
            clean_ligase,
            requested_filename,
            resolved_name,
            len(deduped_names),
        )

        for candidate_name in deduped_names:
            url = f"{base}/file/pdb/{quote(clean_ligase, safe='')}/{quote(candidate_name, safe='')}"
            try:
                response = requests.get(url, headers=_remote_headers(), timeout=timeout)
                last_response = response
                current_app.logger.info(
                    "[e3_handoff] fetch base=%s ligase=%s requested=%s candidate=%s status=%s",
                    _base_label(base),
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    response.status_code,
                )
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                return response.content, response.headers.get("content-type", "chemical/x-pdb")
            except requests.HTTPError:
                current_app.logger.warning(
                    "[e3_handoff] upstream http error base=%s ligase=%s requested=%s candidate=%s status=%s",
                    _base_label(base),
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    response.status_code if response is not None else None,
                )
                raise
            except requests.RequestException as exc:
                last_error = exc
                current_app.logger.warning(
                    "[e3_handoff] upstream request exception base=%s ligase=%s requested=%s candidate=%s error=%s",
                    _base_label(base),
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    exc,
                )
                break

    if last_response is not None and last_response.status_code == 404:
        current_app.logger.warning(
            "[e3_handoff] e3_pdb_not_found ligase=%s requested=%s candidates=%s bases=%s",
            clean_ligase,
            requested_filename,
            candidate_names,
            [_base_label(base) for base in bases],
        )
        raise requests.HTTPError("Remote ligase PDB not found.", response=last_response)
    if last_error is not None:
        current_app.logger.warning(
            "[e3_handoff] upstream request failed for all bases ligase=%s filename=%s error=%s",
            clean_ligase,
            requested_filename,
            last_error,
        )
        raise last_error
    current_app.logger.warning(
        "[e3_handoff] no remote base configured ligase=%s filename=%s",
        clean_ligase,
        requested_filename,
    )
    raise FileNotFoundError("No remote E3 ligase data source is configured.")
