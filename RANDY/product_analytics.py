"""Persistent, aggregate-only PROTAC Builder product analytics for RANDY."""
from __future__ import annotations

import ipaddress
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

EVENTS = {"page_view", "builder_opened", "candidate_constructed"}
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{12,100}$")


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


def _geo(ip: str):
    if os.environ.get("PROTAC_USAGE_GEOIP", "0").lower() not in {"1", "true", "yes", "on"}:
        return None, None, None, None
    try:
        address = ipaddress.ip_address(ip)
        if address.is_private or address.is_loopback: return None, None, None, None
        data = requests.get(f"https://ipwho.is/{address}", timeout=1.5).json()
        if data.get("success", True): return str(data.get("country_code") or "")[:2].upper() or None, str(data.get("country") or "")[:80] or None, data.get("latitude"), data.get("longitude")
    except (ValueError, requests.RequestException):
        pass
    return None, None, None, None


def validate(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or payload.get("event_type") not in EVENTS:
        return None
    if not all(SAFE_ID.fullmatch(str(payload.get(key, ""))) for key in ("event_id", "visitor_id", "session_id")):
        return None
    path = str(payload.get("path") or "")[:240]
    if not path.startswith("/") or "?" in path or "#" in path:
        return None
    return {"event_id": payload["event_id"], "event_type": payload["event_type"], "visitor_id": payload["visitor_id"], "session_id": payload["session_id"], "path": path, "referrer": str(payload.get("referrer") or "direct")[:255], "device": str(payload.get("device") if payload.get("device") in {"desktop", "mobile", "tablet"} else "desktop"), "browser": str(payload.get("browser") or "other")[:32], "feature": str(payload.get("feature") or "")[:80], "ip_address": str(payload.get("ip_address") or "")}


def insert(db_path: Path, event: dict[str, Any]) -> bool:
    country_code, country_name, latitude, longitude = _geo(event.pop("ip_address", ""))
    with sqlite3.connect(db_path) as connection:
        _schema(connection)
        before = connection.total_changes
        connection.execute("INSERT OR IGNORE INTO protac_product_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event["event_id"], datetime.now(timezone.utc).isoformat(), event["event_type"], event["visitor_id"], event["session_id"], event["path"], event["referrer"], event["device"], event["browser"], country_code, country_name, latitude, longitude, event["feature"]))
        return connection.total_changes > before


def summary(db_path: Path, period: str = "30d") -> dict[str, Any]:
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat() if days else None
    clause, params = (" WHERE occurred_at >= ?", (start,)) if start else ("", ())
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row; _schema(connection)
        count = lambda sql: connection.execute(sql, params).fetchone()[0]
        visitors = count("SELECT COUNT(DISTINCT visitor_id) FROM protac_product_events" + clause)
        sessions = count("SELECT COUNT(DISTINCT session_id) FROM protac_product_events" + clause)
        page_views = count("SELECT COUNT(*) FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view'")
        daily = [dict(row) for row in connection.execute("SELECT substr(occurred_at,1,10) date, COUNT(*) views, COUNT(DISTINCT visitor_id) visitors FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY date ORDER BY date", params)]
        grouped = lambda field: [dict(row) for row in connection.execute(f"SELECT {field} label, COUNT(*) value FROM protac_product_events" + clause + " GROUP BY label ORDER BY value DESC LIMIT 20", params)]
        pages = [dict(row) for row in connection.execute("SELECT path, COUNT(*) views, COUNT(DISTINCT visitor_id) visitors FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' GROUP BY path ORDER BY views DESC LIMIT 30", params)]
        countries = [dict(row) for row in connection.execute("SELECT country_code, country_name, latitude, longitude, COUNT(*) views FROM protac_product_events" + clause + (" AND" if clause else " WHERE") + " event_type='page_view' AND country_code IS NOT NULL GROUP BY country_code ORDER BY views DESC", params)]
        counts = {row["event_type"]: row["sessions"] for row in connection.execute("SELECT event_type, COUNT(DISTINCT session_id) sessions FROM protac_product_events" + clause + " GROUP BY event_type", params)}
    funnel = [{"label": label, "sessions": counts.get(event, 0)} for label, event in (("Landing page", "page_view"), ("Builder opened", "builder_opened"), ("Candidate constructed", "candidate_constructed"))]
    return {"ok": True, "period": period, "metrics": {"visitors": visitors, "sessions": sessions, "page_views": page_views}, "daily": daily, "referrers": grouped("referrer"), "devices": grouped("device"), "pages": pages, "countries": countries, "funnel": funnel}
