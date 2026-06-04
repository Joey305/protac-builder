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
_PREFERRED_BASE_ENV_VARS = (
    "E3_RANDY_API_BASE",
    "E3_RANDY_BASE_URL",
    "E3_DATA_API_BASE",
    "E3_DATA_BASE_URL",
    "E3_LIGANDALYZER_API_BASE",
    "E3_LIGANDALYZER_BASE_URL",
)
_HARD_CODED_FALLBACK_BASES = (
    ("https://e3ligandalyzer-adb8adfde220.herokuapp.com", "hardcoded:e3ligandalyzer.heroku"),
    ("https://stan.rove-vernier.ts.net", "hardcoded:stan.rove-vernier"),
)


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


def _base_path(base: str) -> str:
    parsed = urlparse(base)
    return parsed.path or "/"


def _env_presence() -> dict[str, bool]:
    return {name: bool(os.environ.get(name, "").strip()) for name in _PREFERRED_BASE_ENV_VARS}


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


def _candidate_remote_base_entries() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    seen: set[str] = set()

    for env_name in _PREFERRED_BASE_ENV_VARS:
        clean = normalize_e3_base_url(os.environ.get(env_name, "").strip())
        if not clean or clean in seen:
            continue
        seen.add(clean)
        entries.append(
            {
                "base": clean,
                "source": env_name,
                "configured": True,
            }
        )

    configured_session_base = normalize_e3_base_url(os.environ.get("PROTAC_CONVERTED_SESSION_BASE", "").strip())
    if configured_session_base and configured_session_base not in seen:
        seen.add(configured_session_base)
        entries.append(
            {
                "base": configured_session_base,
                "source": "PROTAC_CONVERTED_SESSION_BASE",
                "configured": True,
            }
        )

    for raw_value, source in _HARD_CODED_FALLBACK_BASES:
        clean = normalize_e3_base_url(raw_value)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        entries.append(
            {
                "base": clean,
                "source": source,
                "configured": False,
            }
        )

    return entries


def _candidate_remote_bases() -> list[str]:
    return [str(entry["base"]) for entry in _candidate_remote_base_entries()]


def resolve_remote_pdb_filename_from_inventory(remote_files: list[str], requested_filename: str) -> str | None:
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
    return resolve_remote_pdb_filename_from_inventory(remote_files, requested_filename)


def _fetch_listing_diagnostic(base: str, ligase: str, timeout: float) -> dict[str, object]:
    cache_key = (base, ligase.lower())
    now = time.time()
    cached = _PDB_LIST_CACHE.get(cache_key)
    if cached and cached[0] > now:
        files = cached[1]
        return {
            "status_code": 200,
            "files": files,
            "count": len(files),
            "source": "cache",
            "error": None,
        }

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
            return {"status_code": 404, "files": [], "count": 0, "source": "listing", "error": None}
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return {
                "status_code": response.status_code,
                "files": None,
                "count": None,
                "source": "listing",
                "error": "listing payload was not a list",
            }
        files = [str(item).strip() for item in payload if str(item).strip()]
        _PDB_LIST_CACHE[cache_key] = (now + max(0.0, _PDB_LIST_CACHE_TTL), files)
        return {
            "status_code": response.status_code,
            "files": files,
            "count": len(files),
            "source": "listing",
            "error": None,
        }
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        current_app.logger.warning(
            "[e3_handoff] listing request failed base=%s ligase=%s status=%s error=%s",
            _base_label(base),
            ligase,
            status,
            exc,
        )
        return {"status_code": status, "files": None, "count": None, "source": "listing", "error": exc.__class__.__name__}
    except requests.RequestException as exc:
        current_app.logger.warning(
            "[e3_handoff] listing request exception base=%s ligase=%s error=%s",
            _base_label(base),
            ligase,
            exc,
        )
        return {"status_code": None, "files": None, "count": None, "source": "listing", "error": exc.__class__.__name__}
    except ValueError as exc:
        current_app.logger.warning(
            "[e3_handoff] listing decode failed base=%s ligase=%s error=%s",
            _base_label(base),
            ligase,
            exc,
        )
        return {"status_code": None, "files": None, "count": None, "source": "listing", "error": "ValueError"}


def inspect_remote_ligase_pdb(
    ligase: str,
    filename: str,
    timeout: float = 20.0,
    *,
    include_content: bool = False,
) -> dict[str, object]:
    clean_ligase = _validate_ligase_name(ligase)
    requested_filename = _validate_pdb_filename(filename)
    candidate_names = pdb_candidate_filenames(requested_filename)
    base_entries = _candidate_remote_base_entries()

    diagnostic: dict[str, object] = {
        "ok": False,
        "ligase": clean_ligase,
        "requested_filename": requested_filename,
        "token_present": bool(_remote_token()),
        "configured_env_vars": _env_presence(),
        "used_fallback_only": bool(base_entries) and not any(bool(entry["configured"]) for entry in base_entries),
        "candidate_filenames": candidate_names,
        "normalized_bases": [
            {
                "host": _base_label(str(entry["base"])),
                "base_path": _base_path(str(entry["base"])),
                "source": entry["source"],
                "configured": bool(entry["configured"]),
            }
            for entry in base_entries
        ],
        "per_base": [],
        "matched_filename": None,
        "source": "none",
        "listing_status": None,
        "listing_count": None,
        "final_upstream_status": None,
        "exception_type": None,
    }

    first_non404_status: int | None = None
    first_exception_type: str | None = None
    any_404 = False

    current_app.logger.info(
        "[e3_handoff] request ligase=%s filename=%s candidate_bases=%s candidates=%s token_present=%s configured_envs=%s",
        clean_ligase,
        requested_filename,
        [base["host"] for base in diagnostic["normalized_bases"]],
        candidate_names,
        diagnostic["token_present"],
        [name for name, present in diagnostic["configured_env_vars"].items() if present],
    )

    for entry in base_entries:
        base = str(entry["base"])
        listing = _fetch_listing_diagnostic(base, clean_ligase, timeout)
        files = listing.get("files") if isinstance(listing.get("files"), list) else None
        matched_filename = resolve_remote_pdb_filename_from_inventory(files or [], requested_filename) if files is not None else None
        names_to_try = [name for name in [matched_filename, *candidate_names] if name]
        seen_names: set[str] = set()
        deduped_names: list[str] = []
        for name in names_to_try:
            lowered = name.lower()
            if lowered in seen_names:
                continue
            seen_names.add(lowered)
            deduped_names.append(name)

        base_diag: dict[str, object] = {
            "host": _base_label(base),
            "base_path": _base_path(base),
            "source": entry["source"],
            "configured": bool(entry["configured"]),
            "listing_status": listing.get("status_code"),
            "listing_count": listing.get("count"),
            "listing_source": listing.get("source"),
            "matched_filename": matched_filename,
            "candidate_count": len(deduped_names),
            "direct_fetch_statuses": [],
            "result": "not_found",
        }
        diagnostic["per_base"].append(base_diag)

        if diagnostic["listing_status"] is None and listing.get("status_code") is not None:
            diagnostic["listing_status"] = listing.get("status_code")
            diagnostic["listing_count"] = listing.get("count")

        current_app.logger.info(
            "[e3_handoff] base=%s ligase=%s requested=%s listing_status=%s listing_count=%s matched=%s candidates=%s source=%s",
            base_diag["host"],
            clean_ligase,
            requested_filename,
            base_diag["listing_status"],
            base_diag["listing_count"],
            matched_filename,
            base_diag["candidate_count"],
            base_diag["source"],
        )

        for candidate_name in deduped_names:
            url = f"{base}/file/pdb/{quote(clean_ligase, safe='')}/{quote(candidate_name, safe='')}"
            try:
                response = requests.get(url, headers=_remote_headers(), timeout=timeout)
                status = response.status_code
                cast_list = base_diag["direct_fetch_statuses"]
                assert isinstance(cast_list, list)
                cast_list.append({"filename": candidate_name, "status": status})
                current_app.logger.info(
                    "[e3_handoff] fetch base=%s ligase=%s requested=%s candidate=%s status=%s",
                    base_diag["host"],
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    status,
                )
                if status == 404:
                    any_404 = True
                    continue
                response.raise_for_status()
                diagnostic["ok"] = True
                diagnostic["matched_filename"] = candidate_name
                diagnostic["source"] = "randy-listing" if matched_filename else "direct-fetch"
                diagnostic["listing_status"] = base_diag["listing_status"]
                diagnostic["listing_count"] = base_diag["listing_count"]
                diagnostic["final_upstream_status"] = status
                base_diag["result"] = "ok"
                if include_content:
                    diagnostic["_content"] = response.content
                    diagnostic["_content_type"] = response.headers.get("content-type", "chemical/x-pdb")
                return diagnostic
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                cast_list = base_diag["direct_fetch_statuses"]
                assert isinstance(cast_list, list)
                cast_list.append({"filename": candidate_name, "status": status, "error": exc.__class__.__name__})
                if status == 404:
                    any_404 = True
                    continue
                if first_non404_status is None and status is not None:
                    first_non404_status = status
                if first_exception_type is None:
                    first_exception_type = exc.__class__.__name__
                base_diag["result"] = "error"
                current_app.logger.warning(
                    "[e3_handoff] upstream http error base=%s ligase=%s requested=%s candidate=%s status=%s",
                    base_diag["host"],
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    status,
                )
                break
            except requests.RequestException as exc:
                cast_list = base_diag["direct_fetch_statuses"]
                assert isinstance(cast_list, list)
                cast_list.append({"filename": candidate_name, "status": None, "error": exc.__class__.__name__})
                if first_exception_type is None:
                    first_exception_type = exc.__class__.__name__
                base_diag["result"] = "exception"
                current_app.logger.warning(
                    "[e3_handoff] upstream request exception base=%s ligase=%s requested=%s candidate=%s error=%s",
                    base_diag["host"],
                    clean_ligase,
                    requested_filename,
                    candidate_name,
                    exc,
                )
                break

    if first_non404_status is not None:
        diagnostic["final_upstream_status"] = first_non404_status
    elif any_404:
        diagnostic["final_upstream_status"] = 404
    diagnostic["exception_type"] = first_exception_type
    return diagnostic


def fetch_remote_ligase_pdb(ligase: str, filename: str, timeout: float = 20.0) -> tuple[bytes, str]:
    diagnostic = inspect_remote_ligase_pdb(ligase, filename, timeout=timeout, include_content=True)
    if diagnostic.get("ok"):
        return (
            bytes(diagnostic.get("_content") or b""),
            str(diagnostic.get("_content_type") or "chemical/x-pdb"),
        )

    normalized_bases = diagnostic.get("normalized_bases") or []
    if not normalized_bases:
        current_app.logger.warning(
            "[e3_handoff] no remote base configured ligase=%s filename=%s envs=%s",
            diagnostic.get("ligase"),
            diagnostic.get("requested_filename"),
            [name for name, present in dict(diagnostic.get("configured_env_vars") or {}).items() if present],
        )
        raise FileNotFoundError("No remote E3 ligase data source is configured.")

    current_app.logger.warning(
        "[e3_handoff] e3_pdb_unresolved ligase=%s requested=%s final_status=%s token_present=%s fallback_only=%s listing_status=%s matched=%s bases=%s exception=%s",
        diagnostic.get("ligase"),
        diagnostic.get("requested_filename"),
        diagnostic.get("final_upstream_status"),
        diagnostic.get("token_present"),
        diagnostic.get("used_fallback_only"),
        diagnostic.get("listing_status"),
        diagnostic.get("matched_filename"),
        [base.get("host") for base in normalized_bases if isinstance(base, dict)],
        diagnostic.get("exception_type"),
    )

    status_code = diagnostic.get("final_upstream_status")
    if status_code == 404:
        response = requests.Response()
        response.status_code = 404
        raise requests.HTTPError("Remote ligase PDB not found.", response=response)
    if isinstance(status_code, int):
        response = requests.Response()
        response.status_code = status_code
        raise requests.HTTPError(f"Remote ligase PDB upstream failed: HTTP {status_code}", response=response)
    if diagnostic.get("exception_type"):
        raise requests.RequestException(str(diagnostic["exception_type"]))
    raise FileNotFoundError("No remote E3 ligase data source is configured.")
