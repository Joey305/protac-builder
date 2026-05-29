from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import (
    LEGACY_PROTAC_LOG,
    PROTAC_DOWNLOAD_LOG,
    PROTAC_USAGE_LOG,
    PROTAC_USAGE_SEED_PATH,
    RUNTIME_DATA_DIR,
    STATIC_DATA_DIR,
)


COUNTED_BUILD_ENDPOINTS = {
    "generate",
    "builder_batch",
    "builder_cli",
    "mapped_smiles",
}

BUILD_COUNT_NOTE = "Verified historical build count from legacy PROTAC_log.csv plus new standalone successful builds."
STANDALONE_COUNT_RULE = (
    "seed_total from parent legacy PROTAC_log.csv non-header rows + "
    "local standalone successful generated PROTAC rows"
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_csv_row(path: Path, header: list[str], row: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(header)
        writer.writerow(row)


def _ensure_csv(path: Path, header: list[str]) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)


def _count_non_header_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def _default_seed_payload() -> dict[str, object]:
    return {
        "seed_total": 0,
        "seed_template_downloads": 0,
        "source": "unverified",
        "source_file": None,
        "counting_rule": STANDALONE_COUNT_RULE,
        "notes": "No verified historical build log found. Counter starts from standalone successful builds.",
    }


def ensure_usage_files() -> None:
    _ensure_csv(
        PROTAC_USAGE_LOG,
        ["timestamp_utc", "source", "endpoint", "status", "built", "failed", "extra"],
    )
    _ensure_csv(
        PROTAC_DOWNLOAD_LOG,
        ["timestamp_utc", "client_ip", "user_agent", "filename"],
    )
    if not PROTAC_USAGE_SEED_PATH.exists():
        PROTAC_USAGE_SEED_PATH.write_text(
            json.dumps(_default_seed_payload(), indent=2) + "\n",
            encoding="utf-8",
        )


def _load_seed() -> dict[str, object]:
    ensure_usage_files()
    try:
        return json.loads(PROTAC_USAGE_SEED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_seed_payload()


def _legacy_static_data_dir() -> Path:
    return STATIC_DATA_DIR


def migrate_legacy_usage_counts() -> dict[str, object]:
    ensure_usage_files()
    seed = _load_seed()

    legacy_dir = _legacy_static_data_dir()
    legacy_build_log = legacy_dir / "PROTAC_log.csv"
    legacy_download_log = legacy_dir / "protac_api_downloads.csv"

    verified_seed_total = _count_non_header_rows(legacy_build_log)
    verified_seed_downloads = _count_non_header_rows(legacy_download_log)

    verified_seed = {
        "seed_total": verified_seed_total,
        "seed_template_downloads": verified_seed_downloads,
        "source": "legacy_static_data_protac_log" if legacy_build_log.exists() else "unverified",
        "source_file": "static/data/PROTAC_log.csv" if legacy_build_log.exists() else None,
        "counting_rule": STANDALONE_COUNT_RULE,
        "notes": BUILD_COUNT_NOTE if legacy_build_log.exists() else _default_seed_payload()["notes"],
    }

    if seed != verified_seed:
        PROTAC_USAGE_SEED_PATH.write_text(json.dumps(verified_seed, indent=2) + "\n", encoding="utf-8")
        return verified_seed
    return seed


def log_builder_usage(source: str, endpoint: str, metadata: dict[str, object] | None = None) -> None:
    ensure_usage_files()
    metadata = metadata or {}
    status = str(metadata.get("status", "ok")).strip().lower() or "ok"
    built = int(metadata.get("built", 1 if status == "ok" else 0) or 0)
    failed = int(metadata.get("failed", 0) or 0)
    extra = str(metadata.get("extra", ""))
    _append_csv_row(
        PROTAC_USAGE_LOG,
        ["timestamp_utc", "source", "endpoint", "status", "built", "failed", "extra"],
        [now_utc_iso(), source, endpoint, status, built, failed, extra],
    )


def _count_local_actions() -> tuple[int, dict[str, int], dict[str, int]]:
    by_source: dict[str, int] = {}
    by_endpoint: dict[str, int] = {}

    with PROTAC_USAGE_LOG.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            endpoint = (row.get("endpoint") or "").strip()
            status = (row.get("status") or "").strip().lower()
            if status != "ok" or endpoint not in COUNTED_BUILD_ENDPOINTS:
                continue
            source = (row.get("source") or "unknown").strip() or "unknown"
            by_source[source] = by_source.get(source, 0) + 1
            by_endpoint[endpoint] = by_endpoint.get(endpoint, 0) + 1

    local_actions = 0
    with PROTAC_USAGE_LOG.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            endpoint = (row.get("endpoint") or "").strip()
            status = (row.get("status") or "").strip().lower()
            if status != "ok" or endpoint not in COUNTED_BUILD_ENDPOINTS:
                continue
            try:
                built = int(row.get("built") or 1)
            except ValueError:
                built = 1
            local_actions += max(built, 0)
    return local_actions, by_source, by_endpoint


def get_usage_summary() -> dict[str, object]:
    ensure_usage_files()
    seed = migrate_legacy_usage_counts()
    seed_total = int(seed.get("seed_total", 0) or 0)
    local_actions, by_source, by_endpoint = _count_local_actions()
    return {
        "total": seed_total + local_actions,
        "seed_total": seed_total,
        "local_actions": local_actions,
        "source": seed.get("source"),
        "source_file": seed.get("source_file"),
        "canonical_log_file": str(LEGACY_PROTAC_LOG),
        "runtime_data_dir": str(RUNTIME_DATA_DIR),
        "counting_rule": seed.get("counting_rule"),
        "notes": seed.get("notes"),
        "by_source": by_source,
        "by_endpoint": by_endpoint,
    }


def get_template_download_count() -> int:
    seed = migrate_legacy_usage_counts()
    return int(seed.get("seed_template_downloads", 0) or 0) + _count_non_header_rows(PROTAC_DOWNLOAD_LOG)
