from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd
from flask import Request, Response

from .paths import (
    API_LINKERS_CSV,
    GENERATED_PROTACS_LOG,
    LEGACY_PROTAC_LOG,
    LINKER_CSV_PATH,
    LOGS_DIR,
    PROTAC_DOWNLOAD_LOG,
    PROTAC_USAGE_LOG,
    WARHEAD_CSV_PATH,
)

try:
    import fcntl
except Exception:  # pragma: no cover - not available on macOS sandboxed Python builds
    fcntl = None


DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5069",
    "http://localhost:5069",
    "http://127.0.0.1:5002",
    "http://localhost:5002",
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_allowed_origins() -> set[str]:
    raw = os.environ.get("PROTAC_ALLOWED_ORIGINS", "")
    if not raw.strip():
        return set(DEFAULT_ALLOWED_ORIGINS)
    return {part.strip() for part in raw.split(",") if part.strip()}


def apply_cors_headers(request: Request, response: Response) -> Response:
    origin = (request.headers.get("Origin") or "").strip()
    if origin and origin in get_allowed_origins():
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def append_csv_row(path: Path, header: Iterable[str], row: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        if fcntl:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX)
            except Exception:
                pass

        writer = csv.writer(handle)
        if not exists:
            writer.writerow(list(header))
        writer.writerow(list(row))

        if fcntl:
            try:
                fcntl.flock(handle, fcntl.LOCK_UN)
            except Exception:
                pass


def ensure_csv(path: Path, header: Iterable[str]) -> None:
    if path.exists():
        return
    append_csv_row(path, header, [])
    with path.open("r+", encoding="utf-8") as handle:
        lines = handle.readlines()
        handle.seek(0)
        handle.truncate()
        if lines:
            handle.write(lines[0])


def initialize_runtime_files() -> None:
    from .usage import ensure_usage_files, migrate_legacy_usage_counts

    ensure_csv(
        GENERATED_PROTACS_LOG,
        [
            "timestamp_utc",
            "source",
            "client_ip",
            "warhead_mol",
            "linker_mol",
            "ligase_mol",
            "protac_mol",
            "protac_smiles",
        ],
    )
    ensure_csv(
        LEGACY_PROTAC_LOG,
        ["timestamp_utc", "protac_smiles"],
    )
    ensure_usage_files()
    migrate_legacy_usage_counts()


@lru_cache(maxsize=1)
def get_linkers_df() -> pd.DataFrame:
    if not LINKER_CSV_PATH.exists():
        raise FileNotFoundError(f"Missing required linker CSV: {LINKER_CSV_PATH}")
    return pd.read_csv(LINKER_CSV_PATH)


@lru_cache(maxsize=1)
def get_warheads_df() -> pd.DataFrame:
    if not WARHEAD_CSV_PATH.exists():
        raise FileNotFoundError(f"Missing required warhead CSV: {WARHEAD_CSV_PATH}")
    return (
        pd.read_csv(WARHEAD_CSV_PATH)
        .drop_duplicates(subset="ligand")
        .sort_values(by="ligand")
    )


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For", "")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP", "")
    if x_real_ip:
        return x_real_ip.strip()
    return request.remote_addr or "unknown"


def log_generated_protac(
    *,
    client_ip: str,
    warhead_mol: str = "",
    linker_mol: str = "",
    ligase_mol: str = "",
    protac_mol: str = "",
    protac_smiles: str = "",
    source: str = "web",
) -> None:
    append_csv_row(
        GENERATED_PROTACS_LOG,
        [
            "timestamp_utc",
            "source",
            "client_ip",
            "warhead_mol",
            "linker_mol",
            "ligase_mol",
            "protac_mol",
            "protac_smiles",
        ],
        [
            now_utc_iso(),
            source,
            client_ip,
            warhead_mol,
            linker_mol,
            ligase_mol,
            protac_mol,
            protac_smiles,
        ],
    )
    append_csv_row(
        LEGACY_PROTAC_LOG,
        ["timestamp_utc", "protac_smiles"],
        [now_utc_iso(), protac_smiles],
    )


def write_frontend_log(
    *,
    client_ip: str,
    warhead_mol: str,
    linker_mol: str,
    ligase_mol: str,
    protac_mol: str,
    protac_smiles: str,
) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = LOGS_DIR / f"protac_{stamp}.txt"
    content = [
        f"IP: {client_ip}",
        "",
        "=== WARHEAD ===",
        warhead_mol,
        "",
        "=== LINKER ===",
        linker_mol,
        "",
        "=== LIGASE ===",
        ligase_mol,
        "",
        "=== PROTAC (MOL) ===",
        protac_mol,
        "",
        "=== PROTAC (SMILES) ===",
        protac_smiles,
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def log_builder_usage(
    *,
    source: str,
    endpoint: str,
    status: str,
    built: int = 0,
    failed: int = 0,
    extra: str = "",
) -> None:
    from .usage import log_builder_usage as usage_log_builder_usage

    usage_log_builder_usage(
        source=source,
        endpoint=endpoint,
        metadata={"status": status, "built": int(built), "failed": int(failed), "extra": extra},
    )


def get_builder_usage_counts() -> dict[str, object]:
    from .usage import get_usage_summary

    return get_usage_summary()


def log_template_download(*, request: Request, filename: str) -> None:
    append_csv_row(
        PROTAC_DOWNLOAD_LOG,
        ["timestamp_utc", "client_ip", "user_agent", "filename"],
        [
            now_utc_iso(),
            get_client_ip(request),
            request.headers.get("User-Agent", ""),
            filename,
        ],
    )


def get_template_download_count() -> int:
    from .usage import get_template_download_count as usage_get_template_download_count

    return usage_get_template_download_count()


def api_linkers_exists() -> bool:
    return API_LINKERS_CSV.exists()
