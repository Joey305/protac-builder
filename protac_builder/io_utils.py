from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd
from flask import Request, Response

from .backup_client import backup_event
from .paths import (
    API_LINKERS_CSV,
    COMPONENT_SMILES_PATH,
    GENERATED_PROTACS_LOG,
    LEGACY_PROTAC_LOG,
    LINKER_CSV_PATH,
    LOGS_DIR,
    PROTAC_DOWNLOAD_LOG,
    PROTAC_USAGE_LOG,
    WARHEAD_CSV_PATH,
    migrate_legacy_runtime_files,
)

try:
    import fcntl
except Exception:  # pragma: no cover - not available on macOS sandboxed Python builds
    fcntl = None

LEGACY_PROTAC_HEADER = ["Date", "IP", "PROTAC", "WARHEAD", "LINKER", "LIGASE"]
LEGACY_TWO_COL_HEADER = ["timestamp_utc", "protac_smiles"]


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

    migrate_legacy_runtime_files()
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
        LEGACY_PROTAC_HEADER,
    )
    migrate_legacy_protac_log_schema()
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


@lru_cache(maxsize=1)
def get_component_smiles_df() -> pd.DataFrame:
    if not COMPONENT_SMILES_PATH.exists():
        raise FileNotFoundError(f"Missing required component SMILES file: {COMPONENT_SMILES_PATH}")

    df = pd.read_csv(
        COMPONENT_SMILES_PATH,
        sep="\t",
        header=None,
        names=["smiles", "ligand", "name"],
        usecols=[0, 1, 2],
        dtype=str,
        keep_default_na=False,
    )

    df["smiles"] = df["smiles"].astype(str).str.strip()
    df["ligand"] = df["ligand"].astype(str).str.strip().str.upper()
    df["name"] = df["name"].astype(str).str.strip()

    df = df[(df["smiles"] != "") & (df["ligand"] != "")]
    return df.drop_duplicates(subset="ligand", keep="first").sort_values(by="ligand")


def find_ligand_smiles(ligand_id: str) -> dict[str, str] | None:
    code = str(ligand_id or "").strip().upper()
    if not code:
        return None

    component_df = get_component_smiles_df()
    row = component_df[component_df["ligand"] == code]
    if not row.empty:
        record = row.iloc[0]
        return {
            "ligand": record["ligand"],
            "smiles": record["smiles"],
            "name": record.get("name", ""),
            "source": "component_smiles",
        }

    warheads_df = get_warheads_df()
    row = warheads_df[warheads_df["ligand"].astype(str).str.upper() == code]
    if row.empty:
        return None

    record = row.iloc[0]
    return {
        "ligand": str(record["ligand"]).strip().upper(),
        "smiles": str(record["smiles"]).strip(),
        "name": "",
        "source": "warheads_csv",
    }


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
    timestamp_utc = now_utc_iso()
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
            timestamp_utc,
            source,
            client_ip,
            warhead_mol,
            linker_mol,
            ligase_mol,
            protac_mol,
            protac_smiles,
        ],
    )
    backup_event(
        {
            "event_type": "generated_protac",
            "timestamp_utc": timestamp_utc,
            "source": source,
            "client_ip": client_ip,
            "protac_smiles": protac_smiles,
            "warhead_mol": warhead_mol,
            "linker_mol": linker_mol,
            "ligase_mol": ligase_mol,
            "protac_mol": protac_mol,
        }
    )
    # Keep detailed generated logs in GENERATED_PROTACS_LOG only.
    # Legacy PROTAC_log.csv is maintained separately in 6-column historical format.


def log_legacy_protac_components(
    *,
    client_ip: str,
    protac_smiles: str,
    warhead_smiles: str = "",
    linker_smiles: str = "",
    ligase_smiles: str = "",
) -> None:
    migrate_legacy_protac_log_schema()
    date_value = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    append_csv_row(
        LEGACY_PROTAC_LOG,
        LEGACY_PROTAC_HEADER,
        [
            date_value,
            client_ip,
            protac_smiles,
            warhead_smiles,
            linker_smiles,
            ligase_smiles,
        ],
    )
    backup_event(
        {
            "event_type": "legacy_protac_components",
            "date": date_value,
            "timestamp_utc": now_utc_iso(),
            "client_ip": client_ip,
            "protac_smiles": protac_smiles,
            "warhead_smiles": warhead_smiles,
            "linker_smiles": linker_smiles,
            "ligase_smiles": ligase_smiles,
        }
    )


def migrate_legacy_protac_log_schema() -> None:
    LEGACY_PROTAC_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LEGACY_PROTAC_LOG.exists() or LEGACY_PROTAC_LOG.stat().st_size == 0:
        with LEGACY_PROTAC_LOG.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(LEGACY_PROTAC_HEADER)
        return

    with LEGACY_PROTAC_LOG.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        with LEGACY_PROTAC_LOG.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(LEGACY_PROTAC_HEADER)
        return

    normalized: list[list[str]] = []
    first = [cell.strip() for cell in rows[0]]
    start_index = 1 if first in (LEGACY_PROTAC_HEADER, LEGACY_TWO_COL_HEADER) else 0

    for row in rows[start_index:]:
        if not row:
            continue
        cells = [str(cell).strip() for cell in row]
        if cells == LEGACY_PROTAC_HEADER or cells == LEGACY_TWO_COL_HEADER:
            continue
        if len(cells) >= 6:
            normalized.append(cells[:6])
        elif len(cells) == 2:
            # Migrate old 2-column rows: timestamp_utc, protac_smiles -> Date,IP,PROTAC,...
            ts = cells[0]
            protac = cells[1]
            date_value = ts.replace("T", "_").split(".")[0].replace(":", "-").rstrip("Z")
            normalized.append([date_value, "", protac, "", "", ""])
        else:
            protac = cells[-1] if cells else ""
            normalized.append(["", "", protac, "", "", ""])

    with LEGACY_PROTAC_LOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(LEGACY_PROTAC_HEADER)
        writer.writerows(normalized)


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
    timestamp_utc = now_utc_iso()
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    append_csv_row(
        PROTAC_DOWNLOAD_LOG,
        ["timestamp_utc", "client_ip", "user_agent", "filename"],
        [
            timestamp_utc,
            client_ip,
            user_agent,
            filename,
        ],
    )
    backup_event(
        {
            "event_type": "template_download",
            "timestamp_utc": timestamp_utc,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "filename": filename,
        }
    )


def get_template_download_count() -> int:
    from .usage import get_template_download_count as usage_get_template_download_count

    return usage_get_template_download_count()


def api_linkers_exists() -> bool:
    return API_LINKERS_CSV.exists()
