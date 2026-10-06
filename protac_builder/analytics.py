"""Small, privacy-conscious first-party analytics store for conference pages."""
from __future__ import annotations

import sqlite3
import os
from collections import defaultdict, deque
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Any

from flask import current_app
import requests

EVENT_TYPES = {"conference_page_view", "ecosystem_tool_click", "poster_resource_click", "ecosystem_cta_click"}
TEXT_FIELDS = {"page", "tool_name", "ecosystem_stage", "destination", "resource_type", "referrer", "device_category", "browser_family", "screen_category"}
UTM_FIELDS = {"utm_source", "utm_medium", "utm_campaign", "utm_content"}
MAX_TEXT_LENGTH = 300
_rate_lock = Lock()
_rate_windows: dict[str, deque[float]] = defaultdict(deque)

# The ecosystem receivers return country data in different shapes.  The hub
# deliberately renders only these fixed country centroids rather than the
# IP-derived points returned by older receivers.
COUNTRY_CENTROIDS = {
    "AR": (-34.0, -64.0), "AT": (47.5, 13.3), "AU": (-25.0, 133.0), "BE": (50.8, 4.5),
    "BR": (-10.0, -55.0), "CA": (56.1, -106.3), "CH": (46.8, 8.2), "CL": (-35.7, -71.5),
    "CN": (35.9, 104.2), "CO": (4.6, -74.3), "CZ": (49.8, 15.5), "DE": (51.2, 10.5),
    "DK": (56.3, 9.5), "ES": (40.5, -3.7), "FI": (61.9, 25.7), "FR": (46.2, 2.2),
    "GB": (55.4, -3.4), "GR": (39.1, 21.8), "HK": (22.4, 114.1), "HU": (47.2, 19.5),
    "ID": (-0.8, 113.9), "IE": (53.4, -8.2), "IL": (31.0, 34.9), "IN": (20.6, 78.9),
    "IT": (41.9, 12.6), "JP": (36.2, 138.3), "KE": (0.0, 37.9), "KR": (35.9, 127.8),
    "MX": (23.6, -102.6), "MY": (4.2, 101.9), "NL": (52.1, 5.3), "NO": (60.5, 8.5),
    "NZ": (-40.9, 174.9), "PH": (12.9, 121.8), "PL": (51.9, 19.1), "PT": (39.4, -8.2),
    "PY": (-23.4, -58.4), "RO": (45.9, 24.9), "RU": (61.5, 105.3), "SE": (60.1, 18.6),
    "SG": (1.4, 103.8), "TH": (15.9, 100.9), "TN": (33.9, 9.5), "TR": (39.0, 35.2),
    "TW": (23.7, 121.0), "UA": (48.4, 31.2), "US": (39.8, -98.6), "VN": (14.1, 108.3),
    "ZA": (-30.6, 22.9),
}
COUNTRY_CODES_BY_NAME = {
    "argentina": "AR", "australia": "AU", "austria": "AT", "belgium": "BE", "brazil": "BR",
    "canada": "CA", "china": "CN", "colombia": "CO", "czechia": "CZ", "czech republic": "CZ",
    "denmark": "DK", "france": "FR", "germany": "DE", "hong kong": "HK", "india": "IN",
    "indonesia": "ID", "italy": "IT", "japan": "JP", "kenya": "KE", "netherlands": "NL",
    "paraguay": "PY", "singapore": "SG", "south africa": "ZA", "south korea": "KR",
    "spain": "ES", "switzerland": "CH", "thailand": "TH", "tunisia": "TN", "united kingdom": "GB",
    "united states": "US", "united states of america": "US",
}


def _normalise_daily(payload: dict[str, Any], period: str) -> None:
    """Give every receiver a clean, one-row-per-day chart contract."""
    rows = payload.get("daily") or []
    by_date: dict[str, dict[str, int]] = {}
    for row in rows:
        raw_date = str(row.get("date") or row.get("day") or "")[:10]
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            continue
        views = row.get("views", row.get("page_views", row.get("count", 0)))
        visitors = row.get("visitors", row.get("sessions"))
        item = by_date.setdefault(raw_date, {"date": raw_date, "views": 0, "visitors": 0})
        item["views"] += int(views or 0)
        if visitors is not None:
            item["visitors"] += int(visitors or 0)
    if len(by_date) == 1 and not next(iter(by_date.values()))["visitors"]:
        # Older receivers supplied a daily page-view total but not a daily
        # session value; a one-day result can safely use its matching total.
        only = next(iter(by_date.values()))
        only["visitors"] = int((payload.get("metrics") or {}).get("sessions", 0) or 0)
    window = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period)
    if window:
        first = date.today() - timedelta(days=window - 1)
        payload["daily"] = [by_date.get((first + timedelta(days=index)).isoformat(), {"date": (first + timedelta(days=index)).isoformat(), "views": 0, "visitors": 0}) for index in range(window)]
    else:
        payload["daily"] = [by_date[key] for key in sorted(by_date)]


def _normalise_countries(payload: dict[str, Any]) -> None:
    """Aggregate country usage and replace legacy precise coordinates."""
    countries: dict[str, dict[str, Any]] = {}
    for row in payload.get("countries") or []:
        name = str(row.get("country_name") or row.get("name") or "Unknown").strip()
        code = str(row.get("country_code") or row.get("code") or COUNTRY_CODES_BY_NAME.get(name.lower(), "")).upper()
        if code not in COUNTRY_CENTROIDS:
            continue
        item = countries.setdefault(code, {"country_code": code, "country_name": name, "latitude": COUNTRY_CENTROIDS[code][0], "longitude": COUNTRY_CENTROIDS[code][1], "views": 0})
        item["views"] += int(row.get("views", row.get("count", 0)) or 0)
    payload["countries"] = sorted(countries.values(), key=lambda item: item["views"], reverse=True)


def _remote_base_url() -> str:
    """RANDY's analytics endpoint; intentionally separate from public browser code."""
    return os.environ.get("ANALYTICS_RANDY_URL", "").strip().rstrip("/")


def _remote_token() -> str:
    return os.environ.get("ANALYTICS_RANDY_TOKEN", "").strip() or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()


def remote_enabled() -> bool:
    return bool(_remote_base_url() and _remote_token())


def _remote_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_remote_token()}", "Content-Type": "application/json", "User-Agent": "protac-builder-conference-analytics/1.0"}


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(current_app.config["ANALYTICS_DB_PATH"])
    connection.row_factory = sqlite3.Row
    return connection


def initialize_store(database_path: str | None = None) -> None:
    path = database_path or current_app.config["ANALYTICS_DB_PATH"]
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS analytics_events (
              id INTEGER PRIMARY KEY,
              event_type TEXT NOT NULL,
              occurred_at TEXT NOT NULL,
              session_id TEXT NOT NULL,
              page TEXT,
              tool_name TEXT,
              ecosystem_stage TEXT,
              destination TEXT,
              resource_type TEXT,
              utm_source TEXT,
              utm_medium TEXT,
              utm_campaign TEXT,
              utm_content TEXT,
              referrer TEXT,
              device_category TEXT,
              browser_family TEXT,
              screen_category TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics_events(occurred_at);
            CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_analytics_campaign ON analytics_events(utm_campaign);
            CREATE INDEX IF NOT EXISTS idx_analytics_session ON analytics_events(session_id);
            """)


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:MAX_TEXT_LENGTH] or None


def validate_event(payload: Any) -> dict[str, str | None] | None:
    if not isinstance(payload, dict) or set(payload) - ({"event_type", "session_id"} | TEXT_FIELDS | UTM_FIELDS):
        return None
    event_type = payload.get("event_type")
    session_id = _clean_text(payload.get("session_id"))
    if event_type not in EVENT_TYPES or not session_id or len(session_id) < 16:
        return None
    if payload.get("page") not in (None, "/barcelona-2026"):
        return None
    if event_type == "ecosystem_tool_click" and not (_clean_text(payload.get("tool_name")) and _clean_text(payload.get("destination"))):
        return None
    if event_type == "poster_resource_click" and not _clean_text(payload.get("resource_type")):
        return None
    cleaned = {key: _clean_text(payload.get(key)) for key in TEXT_FIELDS | UTM_FIELDS}
    cleaned.update(event_type=event_type, session_id=session_id)
    return cleaned


def allow_event(client_key: str) -> bool:
    """A deliberately small in-process guard; reverse-proxy rate limiting may supplement it."""
    now = monotonic()
    with _rate_lock:
        window = _rate_windows[client_key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= 60:
            return False
        window.append(now)
    return True


def record_event(event: dict[str, str | None]) -> bool:
    if remote_enabled():
        try:
            response = requests.post(f"{_remote_base_url()}/event", json=event, headers=_remote_headers(), timeout=2.5)
            return 200 <= response.status_code < 300
        except requests.RequestException:
            # When RANDY is configured, do not write an ephemeral Heroku copy.
            return False
    columns = ["event_type", "session_id", *sorted(TEXT_FIELDS | UTM_FIELDS)]
    values = [event.get(column) for column in columns]
    with closing(_connection()) as connection:
        with connection:
            connection.execute(
                f"INSERT INTO analytics_events (occurred_at, {', '.join(columns)}) VALUES (?, {', '.join('?' for _ in columns)})",
                [datetime.now(timezone.utc).isoformat(), *values],
            )
    return True


def _remote_dashboard_summary(range_name: str, campaign: str, start: str | None, end: str | None) -> dict[str, Any] | None:
    if not remote_enabled():
        return None
    try:
        response = requests.get(f"{_remote_base_url()}/summary", params={"range": range_name, "campaign": campaign, "start": start or "", "end": end or ""}, headers=_remote_headers(), timeout=3.5)
        payload = response.json() if response.status_code == 200 else None
        if isinstance(payload, dict) and payload.get("ok"):
            payload.pop("ok", None)
            return payload
    except (requests.RequestException, ValueError):
        pass
    return None


def ecosystem_dashboard(view: str, period: str, campaign: str = "") -> tuple[dict[str, Any], bool]:
    """Fetch aggregate-only reports from the existing RANDY tool receivers."""
    view = view if view in {"protac", "poster", "warhead", "e3", "vlismod"} else "protac"
    period = period if period in {"7d", "30d", "90d", "1y", "all"} else "30d"
    if view == "poster":
        report = dashboard_summary({"7d": "7d", "30d": "30d", "90d": "30d", "1y": "all", "all": "all"}[period], campaign)
        _normalise_daily(report, period)
        _normalise_countries(report)
        return report, report.get("persistence_source") != "randy_unavailable"
    root = _remote_base_url().rsplit("/backup/analytics", 1)[0] if "/backup/analytics" in _remote_base_url() else ""
    token = _remote_token()
    if not root or not token:
        return {}, False
    routes = {
        "protac": ("/backup/product-analytics/summary", {"period": period}),
        "warhead": ("/backup/analytics/hunter/overview", {"days": {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": 3650}[period]}),
        "e3": ("/backup/e3/analytics/rollup", {"days": {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": "all"}[period]}),
        "vlismod": ("/backup/vlismod/analytics/rollup", {"period": period}),
    }
    headers = {"Authorization": f"Bearer {os.environ.get('VLISMOD_ANALYTICS_TOKEN', '').strip() if view == 'vlismod' else token}", "User-Agent": "protac-builder-analytics-hub/1.0"}
    if view == "vlismod" and not os.environ.get("VLISMOD_ANALYTICS_TOKEN", "").strip():
        return {}, False
    try:
        response = requests.get(root + routes[view][0], params=routes[view][1], headers=headers, timeout=5)
        payload = response.json() if response.ok else {}
        if view == "warhead" and payload.get("ok"):
            usage = payload.get("usage") or {}
            payload["metrics"] = {"visitors": usage.get("unique_visitors", 0), "sessions": usage.get("sessions", 0), "page_views": usage.get("page_views", 0)}
            payload["daily"] = usage.get("trend", [])
            payload["referrers"] = [{"label": item.get("name", "direct"), "value": item.get("count", 0)} for item in usage.get("referrers", [])]
            payload["pages"] = [{"path": item.get("page", ""), "views": item.get("views", 0)} for item in usage.get("pages", [])]
            payload["countries"] = usage.get("locations", [])
            payload["funnel"] = [{"label": "Jobs analyzed", "sessions": (payload.get("overview") or {}).get("total_jobs", 0)}, {"label": "Completed", "sessions": (payload.get("overview") or {}).get("completed_jobs", 0)}]
        if payload.get("ok"):
            _normalise_daily(payload, period)
            _normalise_countries(payload)
        return payload, bool(payload.get("ok"))
    except (requests.RequestException, ValueError):
        return {}, False


def _range_start(range_name: str, start: str | None, end: str | None) -> tuple[str | None, str | None]:
    today = date.today()
    if range_name == "today": return today.isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "7d": return (today - timedelta(days=6)).isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "30d": return (today - timedelta(days=29)).isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "custom":
        try:
            return (date.fromisoformat(start).isoformat() if start else None, (date.fromisoformat(end) + timedelta(days=1)).isoformat() if end else None)
        except ValueError:
            return None, None
    return None, None


def dashboard_summary(range_name: str = "30d", campaign: str = "", start: str | None = None, end: str | None = None) -> dict[str, Any]:
    range_name = range_name if range_name in {"today", "7d", "30d", "custom", "all"} else "30d"
    remote = _remote_dashboard_summary(range_name, campaign, start, end)
    if remote is not None:
        return remote
    if remote_enabled():
        # Avoid silently presenting an empty ephemeral Heroku database as production data.
        return {"filters": {"range": range_name, "campaign": campaign, "start": start or "", "end": end or ""}, "views": 0, "unique_sessions": 0, "tool_clicks": 0, "resources": 0, "ctr": 0, "most_used_tool": "Unavailable", "engaged_sessions": 0, "engagement_rate": 0, "average_tools_per_engaged": 0, "multi_tool_rate": 0, "tools": [], "daily": [], "sources": [], "devices": [], "persistence_source": "randy_unavailable"}
    start, end = _range_start(range_name, start, end)
    conditions, params = [], []
    if start: conditions.append("occurred_at >= ?"); params.append(start)
    if end: conditions.append("occurred_at < ?"); params.append(end)
    if campaign: conditions.append("utm_campaign = ?"); params.append(campaign[:MAX_TEXT_LENGTH])
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with closing(_connection()) as connection:
        def one(query: str, values: list[Any] = params): return connection.execute(query + where, values).fetchone()[0]
        views = one("SELECT COUNT(*) FROM analytics_events") if False else connection.execute("SELECT COUNT(*) FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'conference_page_view'", params).fetchone()[0]
        sessions = connection.execute("SELECT COUNT(DISTINCT session_id) FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'conference_page_view'", params).fetchone()[0]
        tool_clicks = connection.execute("SELECT COUNT(*) FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'ecosystem_tool_click'", params).fetchone()[0]
        resources = connection.execute("SELECT COUNT(*) FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'poster_resource_click'", params).fetchone()[0]
        tools = [dict(row) for row in connection.execute("SELECT tool_name AS label, COUNT(*) AS count FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'ecosystem_tool_click' GROUP BY tool_name ORDER BY count DESC", params)]
        daily = [dict(row) for row in connection.execute("SELECT substr(occurred_at, 1, 10) AS day, COUNT(*) AS views, COUNT(DISTINCT session_id) AS sessions FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'conference_page_view' GROUP BY day ORDER BY day", params)]
        sources = [dict(row) for row in connection.execute("SELECT COALESCE(NULLIF(utm_source, ''), 'direct / other') AS label, COUNT(*) AS count FROM analytics_events" + where + " GROUP BY label ORDER BY count DESC", params)]
        devices = [dict(row) for row in connection.execute("SELECT COALESCE(NULLIF(device_category, ''), 'unknown') AS label, COUNT(*) AS count FROM analytics_events" + where + " GROUP BY label ORDER BY count DESC", params)]
        engaged = connection.execute("SELECT COUNT(DISTINCT session_id) FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'ecosystem_tool_click'", params).fetchone()[0]
        multi = connection.execute("SELECT COUNT(*) FROM (SELECT session_id FROM analytics_events" + where + (" AND " if where else " WHERE ") + "event_type = 'ecosystem_tool_click' GROUP BY session_id HAVING COUNT(*) > 1)", params).fetchone()[0]
    return {"filters": {"range": range_name, "campaign": campaign, "start": start or "", "end": end or ""}, "views": views, "unique_sessions": sessions, "tool_clicks": tool_clicks, "resources": resources, "ctr": round((tool_clicks / views * 100), 1) if views else 0, "most_used_tool": tools[0]["label"] if tools else "—", "engaged_sessions": engaged, "engagement_rate": round((engaged / sessions * 100), 1) if sessions else 0, "average_tools_per_engaged": round(tool_clicks / engaged, 2) if engaged else 0, "multi_tool_rate": round((multi / engaged * 100), 1) if engaged else 0, "tools": tools, "daily": daily, "sources": sources, "devices": devices}
