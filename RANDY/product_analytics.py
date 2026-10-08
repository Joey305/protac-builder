"""Persistent, aggregate-only PROTAC Builder product analytics for RANDY."""
from __future__ import annotations

import ipaddress
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

EVENTS = {
    "page_view", "builder_opened", "candidate_constructed", "candidate_exported",
    "batch_constructed", "deeppk_completed", "admet_completed", "report_downloaded",
    "template_downloaded", "component_saved", "attachment_prepared", "linker_selected",
    "builder_handoff_arrived",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{12,100}$")
HANDOFF_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
SAFE_HANDOFF_SOURCES = {"warhead_hunter", "e3_ligandalyzer", "vlisemod"}
FEATURES_BY_EVENT = {
    "page_view": {""}, "builder_opened": {""},
    "candidate_constructed": {"candidate_construction"}, "candidate_exported": {"smiles_export"},
    "batch_constructed": {"batch_builder"}, "deeppk_completed": {"deeppk"},
    "admet_completed": {"admet"}, "report_downloaded": {"analysis_report"},
    "template_downloaded": {"linker_template"},
    "component_saved": {"warhead", "linker", "recruiter"},
    "attachment_prepared": {"warhead", "linker", "recruiter"},
    "linker_selected": {"curated", "custom"},
    "builder_handoff_arrived": SAFE_HANDOFF_SOURCES,
}

# Country-level reporting must not expose a visitor's IP-derived city or precise
# location.  GeoIP is used only to derive a country code, then this fixed public
# country centroid is stored instead.  Unlisted countries remain countable but
# are omitted from the map until a centroid is added.
COUNTRY_CENTROIDS = {
    "AR": (-34.0, -64.0), "AU": (-25.0, 133.0), "AT": (47.5, 13.3), "BE": (50.8, 4.5),
    "BR": (-10.0, -55.0), "CA": (56.1, -106.3), "CH": (46.8, 8.2), "CL": (-35.7, -71.5),
    "CN": (35.9, 104.2), "CO": (4.6, -74.3), "CZ": (49.8, 15.5), "DE": (51.2, 10.5),
    "DK": (56.3, 9.5), "ES": (40.5, -3.7), "FI": (61.9, 25.7), "FR": (46.2, 2.2),
    "GB": (55.4, -3.4), "GR": (39.1, 21.8), "HK": (22.4, 114.1), "HU": (47.2, 19.5),
    "IE": (53.4, -8.2), "IL": (31.0, 34.9), "IN": (20.6, 78.9), "IT": (41.9, 12.6),
    "JP": (36.2, 138.3), "KR": (35.9, 127.8), "MX": (23.6, -102.6), "NL": (52.1, 5.3),
    "NO": (60.5, 8.5), "NZ": (-40.9, 174.9), "PL": (51.9, 19.1), "PT": (39.4, -8.2),
    "RO": (45.9, 24.9), "RU": (61.5, 105.3), "SE": (60.1, 18.6), "SG": (1.4, 103.8),
    "TR": (39.0, 35.2), "TW": (23.7, 121.0), "UA": (48.4, 31.2), "US": (39.8, -98.6),
    "ZA": (-30.6, 22.9),
}
INTERNAL_REFERRERS = {"protacbuilder.com", "www.protacbuilder.com", "internal"}


def _schema(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS protac_product_events (
      event_id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL, event_type TEXT NOT NULL,
      visitor_id TEXT NOT NULL, session_id TEXT NOT NULL, path TEXT NOT NULL, referrer TEXT NOT NULL,
      device TEXT NOT NULL, browser TEXT NOT NULL, country_code TEXT, country_name TEXT,
      latitude REAL, longitude REAL, feature TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_protac_product_time ON protac_product_events(occurred_at);
    CREATE INDEX IF NOT EXISTS idx_protac_product_type ON protac_product_events(event_type);
    CREATE INDEX IF NOT EXISTS idx_protac_product_session ON protac_product_events(session_id);
    """)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(protac_product_events)")}
    if "handoff_id" not in columns:
        connection.execute("ALTER TABLE protac_product_events ADD COLUMN handoff_id TEXT")
    # Scrub coordinates recorded by the first analytics version.  This is
    # idempotent and ensures an upgrade removes any historic precision too.
    connection.execute("UPDATE protac_product_events SET latitude = NULL, longitude = NULL")
    connection.executemany(
        "UPDATE protac_product_events SET latitude = ?, longitude = ? WHERE country_code = ?",
        [(latitude, longitude, country_code) for country_code, (latitude, longitude) in COUNTRY_CENTROIDS.items()],
    )


def _geo(ip: str):
    if os.environ.get("PROTAC_USAGE_GEOIP", "0").lower() not in {"1", "true", "yes", "on"}:
        return None, None, None, None
    try:
        address = ipaddress.ip_address(ip)
        if address.is_private or address.is_loopback: return None, None, None, None
        data = requests.get(f"https://ipwho.is/{address}", timeout=1.5).json()
        if data.get("success", True):
            country_code = str(data.get("country_code") or "")[:2].upper() or None
            centroid = COUNTRY_CENTROIDS.get(country_code or "")
            return country_code, str(data.get("country") or "")[:80] or None, *(centroid or (None, None))
    except (ValueError, requests.RequestException):
        pass
    return None, None, None, None


def validate(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or payload.get("event_type") not in EVENTS:
        return None
    if not all(SAFE_ID.fullmatch(str(payload.get(key, ""))) for key in ("event_id", "visitor_id", "session_id")):
        return None
    event_type = str(payload["event_type"])
    feature = str(payload.get("feature") or "")
    if feature not in FEATURES_BY_EVENT[event_type]:
        return None
    path = str(payload.get("path") or "")[:240]
    if not path.startswith("/") or "?" in path or "#" in path:
        return None
    handoff_id = str(payload.get("handoff_id") or "")
    if handoff_id and not HANDOFF_ID.fullmatch(handoff_id):
        return None
    if event_type == "builder_handoff_arrived" and not handoff_id:
        return None
    return {"event_id": payload["event_id"], "event_type": event_type, "visitor_id": payload["visitor_id"], "session_id": payload["session_id"], "path": path, "referrer": str(payload.get("referrer") or "direct")[:255], "device": str(payload.get("device") if payload.get("device") in {"desktop", "mobile", "tablet"} else "desktop"), "browser": str(payload.get("browser") or "other")[:32], "feature": feature, "handoff_id": handoff_id, "ip_address": str(payload.get("ip_address") or "")}


def insert(db_path: Path, event: dict[str, Any]) -> bool:
    country_code, country_name, latitude, longitude = _geo(event.pop("ip_address", ""))
    with sqlite3.connect(db_path) as connection:
        _schema(connection)
        before = connection.total_changes
        connection.execute("INSERT OR IGNORE INTO protac_product_events (event_id, occurred_at, event_type, visitor_id, session_id, path, referrer, device, browser, country_code, country_name, latitude, longitude, feature, handoff_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event["event_id"], datetime.now(timezone.utc).isoformat(), event["event_type"], event["visitor_id"], event["session_id"], event["path"], event["referrer"], event["device"], event["browser"], country_code, country_name, latitude, longitude, event["feature"], event["handoff_id"]))
        return connection.total_changes > before


def _daily_buckets(rows: list[dict[str, Any]], start: str | None) -> list[dict[str, Any]]:
    """Return one stable daily point per bucket, including genuine zero-traffic days."""
    values = {row["date"]: row for row in rows}
    if start:
        first = date.fromisoformat(start[:10])
    elif rows:
        first = date.fromisoformat(rows[0]["date"])
    else:
        return []
    last = datetime.now(timezone.utc).date()
    output = []
    while first <= last:
        key = first.isoformat()
        output.append(values.get(key, {"date": key, "views": 0, "visitors": 0}))
        first += timedelta(days=1)
    return output


def summary(db_path: Path, period: str = "30d") -> dict[str, Any]:
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period)
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), tzinfo=timezone.utc).isoformat() if days else None
    clause, params = (" WHERE occurred_at >= ?", (start,)) if start else ("", ())
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row; _schema(connection)
        count = lambda sql: connection.execute(sql, params).fetchone()[0]
        visitors = count("SELECT COUNT(DISTINCT visitor_id) FROM protac_product_events" + clause)
        sessions = count("SELECT COUNT(DISTINCT session_id) FROM protac_product_events" + clause)
        page_views = count("SELECT COUNT(*) FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view'")
        daily = [dict(row) for row in connection.execute("SELECT substr(occurred_at,1,10) date, COUNT(*) views, COUNT(DISTINCT visitor_id) visitors FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY date ORDER BY date", params)]
        grouped = lambda field: [dict(row) for row in connection.execute(f"SELECT {field} label, COUNT(*) value FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY label ORDER BY value DESC LIMIT 20", params)]
        referrers = [dict(row) for row in connection.execute("SELECT CASE WHEN referrer IN ('protacbuilder.com', 'www.protacbuilder.com', 'internal') THEN 'Internal navigation' ELSE referrer END label, COUNT(*) value FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY label ORDER BY value DESC LIMIT 20", params)]
        internal_navigation = sum(item["value"] for item in referrers if item["label"] == "Internal navigation")
        pages = [dict(row) for row in connection.execute("SELECT path, COUNT(*) views, COUNT(DISTINCT visitor_id) visitors FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY path ORDER BY views DESC LIMIT 30", params)]
        countries = [dict(row) for row in connection.execute("SELECT country_code, country_name, latitude, longitude, COUNT(*) views FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' AND country_code IS NOT NULL GROUP BY country_code ORDER BY views DESC", params)]
        counts = {row["event_type"]: row["sessions"] for row in connection.execute("SELECT event_type, COUNT(DISTINCT session_id) sessions FROM protac_product_events" + clause + " GROUP BY event_type", params)}
    funnel = [{"label": label, "sessions": counts.get(event, 0)} for label, event in (("Landing page", "page_view"), ("Builder opened", "builder_opened"), ("Attributed handoff arrived", "builder_handoff_arrived"), ("Components saved", "component_saved"), ("Attachment points prepared", "attachment_prepared"), ("Linker selected", "linker_selected"), ("Candidate constructed", "candidate_constructed"), ("Candidate exported", "candidate_exported"), ("Analysis completed", "deeppk_completed"), ("Report downloaded", "report_downloaded"))]
    features = [dict(row) for row in connection.execute("SELECT event_type || ':' || feature label, COUNT(DISTINCT session_id) value FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type IN ('component_saved','attachment_prepared','linker_selected','builder_handoff_arrived') GROUP BY event_type, feature ORDER BY value DESC", params)]
    return {"ok": True, "period": period, "metrics": {"visitors": visitors, "sessions": sessions, "page_views": page_views, "internal_navigation": internal_navigation, "candidate_constructed": counts.get("candidate_constructed", 0), "candidate_exported": counts.get("candidate_exported", 0), "deeppk_completed": counts.get("deeppk_completed", 0), "admet_completed": counts.get("admet_completed", 0), "report_downloaded": counts.get("report_downloaded", 0), "handoff_arrivals": counts.get("builder_handoff_arrived", 0)}, "daily": _daily_buckets(daily, start), "referrers": referrers, "devices": grouped("device"), "pages": pages, "countries": countries, "funnel": funnel, "features": features}
