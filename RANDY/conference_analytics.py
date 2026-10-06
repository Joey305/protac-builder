"""Authenticated, aggregate-only conference analytics for the RANDY receiver."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

EVENT_TYPES = {"conference_page_view", "poster_tools_viewed", "ecosystem_tool_click", "poster_resource_click", "ecosystem_cta_click"}
TEXT_FIELDS = {"page", "tool_name", "ecosystem_stage", "destination", "resource_type", "referrer", "device_category", "browser_family", "screen_category"}
UTM_FIELDS = {"utm_source", "utm_medium", "utm_campaign", "utm_content"}
MAX_TEXT_LENGTH = 300


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conference_analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL, event_type TEXT NOT NULL, session_id TEXT NOT NULL,
            page TEXT, tool_name TEXT, ecosystem_stage TEXT, destination TEXT, resource_type TEXT,
            utm_source TEXT, utm_medium TEXT, utm_campaign TEXT, utm_content TEXT,
            referrer TEXT, device_category TEXT, browser_family TEXT, screen_category TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_conference_analytics_timestamp ON conference_analytics_events(occurred_at);
        CREATE INDEX IF NOT EXISTS idx_conference_analytics_type ON conference_analytics_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_conference_analytics_campaign ON conference_analytics_events(utm_campaign);
        CREATE INDEX IF NOT EXISTS idx_conference_analytics_session ON conference_analytics_events(session_id);
        """
    )


def _clean(value: Any) -> str | None:
    return value.strip()[:MAX_TEXT_LENGTH] or None if isinstance(value, str) else None


def validate_event(payload: Any) -> dict[str, str | None] | None:
    if not isinstance(payload, dict) or set(payload) - ({"event_type", "session_id"} | TEXT_FIELDS | UTM_FIELDS):
        return None
    session_id = _clean(payload.get("session_id"))
    if payload.get("event_type") not in EVENT_TYPES or not session_id or len(session_id) < 16:
        return None
    if payload.get("page") not in (None, "/barcelona-2026"):
        return None
    if payload["event_type"] == "ecosystem_tool_click" and not (_clean(payload.get("tool_name")) and _clean(payload.get("destination"))):
        return None
    if payload["event_type"] == "poster_resource_click" and not _clean(payload.get("resource_type")):
        return None
    event = {key: _clean(payload.get(key)) for key in TEXT_FIELDS | UTM_FIELDS}
    event.update(event_type=payload["event_type"], session_id=session_id)
    return event


def insert_event(db_path, event: dict[str, str | None], occurred_at: str) -> int:
    columns = ["event_type", "session_id", *sorted(TEXT_FIELDS | UTM_FIELDS)]
    with sqlite3.connect(db_path) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            f"INSERT INTO conference_analytics_events (occurred_at, {', '.join(columns)}) VALUES (?, {', '.join('?' for _ in columns)})",
            [occurred_at, *(event.get(column) for column in columns)],
        )
        connection.commit()
        return int(cursor.lastrowid)


def _range_start(range_name: str, start: str | None, end: str | None) -> tuple[str | None, str | None]:
    today = date.today()
    if range_name == "today": return today.isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "7d": return (today - timedelta(days=6)).isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "30d": return (today - timedelta(days=29)).isoformat(), (today + timedelta(days=1)).isoformat()
    if range_name == "custom":
        try: return (date.fromisoformat(start).isoformat() if start else None, (date.fromisoformat(end) + timedelta(days=1)).isoformat() if end else None)
        except ValueError: return None, None
    return None, None


def summary(db_path, range_name: str = "30d", campaign: str = "", start: str | None = None, end: str | None = None) -> dict[str, Any]:
    range_name = range_name if range_name in {"today", "7d", "30d", "custom", "all"} else "30d"
    start, end = _range_start(range_name, start, end)
    conditions, params = [], []
    if start: conditions.append("occurred_at >= ?"); params.append(start)
    if end: conditions.append("occurred_at < ?"); params.append(end)
    if campaign: conditions.append("utm_campaign = ?"); params.append(campaign[:MAX_TEXT_LENGTH])
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    def event_where(event_type: str) -> str: return where + (" AND " if where else " WHERE ") + f"event_type = '{event_type}'"
    with sqlite3.connect(db_path) as connection:
        _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        query = lambda sql, values=params: connection.execute(sql, values).fetchone()[0]
        views = query("SELECT COUNT(*) FROM conference_analytics_events" + event_where("conference_page_view"))
        sessions = query("SELECT COUNT(DISTINCT session_id) FROM conference_analytics_events" + event_where("conference_page_view"))
        tool_clicks = query("SELECT COUNT(*) FROM conference_analytics_events" + event_where("ecosystem_tool_click"))
        resources = query("SELECT COUNT(*) FROM conference_analytics_events" + event_where("poster_resource_click"))
        tools = [dict(row) for row in connection.execute("SELECT tool_name AS label, COUNT(*) AS count FROM conference_analytics_events" + event_where("ecosystem_tool_click") + " GROUP BY tool_name ORDER BY count DESC", params)]
        daily = [dict(row) for row in connection.execute("SELECT substr(occurred_at, 1, 10) AS day, COUNT(*) AS views, COUNT(DISTINCT session_id) AS sessions FROM conference_analytics_events" + event_where("conference_page_view") + " GROUP BY day ORDER BY day", params)]
        sources = [dict(row) for row in connection.execute("SELECT COALESCE(NULLIF(utm_source, ''), 'direct / other') AS label, COUNT(*) AS count FROM conference_analytics_events" + where + " GROUP BY label ORDER BY count DESC", params)]
        devices = [dict(row) for row in connection.execute("SELECT COALESCE(NULLIF(device_category, ''), 'unknown') AS label, COUNT(*) AS count FROM conference_analytics_events" + where + " GROUP BY label ORDER BY count DESC", params)]
        engaged = query("SELECT COUNT(DISTINCT session_id) FROM conference_analytics_events" + event_where("ecosystem_tool_click"))
        tools_viewed = query("SELECT COUNT(DISTINCT session_id) FROM conference_analytics_events" + event_where("poster_tools_viewed"))
        multi = query("SELECT COUNT(*) FROM (SELECT session_id FROM conference_analytics_events" + event_where("ecosystem_tool_click") + " GROUP BY session_id HAVING COUNT(*) > 1)")
    return {"filters": {"range": range_name, "campaign": campaign, "start": start or "", "end": end or ""}, "views": views, "unique_sessions": sessions, "tool_clicks": tool_clicks, "resources": resources, "ctr": round(tool_clicks / views * 100, 1) if views else 0, "most_used_tool": tools[0]["label"] if tools else "—", "engaged_sessions": engaged, "tools_viewed": tools_viewed, "multi_tool_sessions": multi, "engagement_rate": round(engaged / sessions * 100, 1) if sessions else 0, "average_tools_per_engaged": round(tool_clicks / engaged, 2) if engaged else 0, "multi_tool_rate": round(multi / engaged * 100, 1) if engaged else 0, "tools": tools, "daily": daily, "sources": sources, "devices": devices}
