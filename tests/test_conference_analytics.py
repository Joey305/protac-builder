import os
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
from unittest.mock import Mock, patch


class ConferenceAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ANALYTICS_DB_PATH"] = str(Path(self.tmp.name) / "analytics.sqlite3")
        os.environ["ADMIN_EMAIL"] = "admin@example.org"
        os.environ["ADMIN_PASSWORD"] = "test-password"
        from app import create_app
        self.client = create_app().test_client()

    def tearDown(self):
        self.tmp.cleanup()
        for name in ("ANALYTICS_DB_PATH", "ANALYTICS_RANDY_URL", "ANALYTICS_RANDY_TOKEN", "VLISMOD_ANALYTICS_TOKEN", "ADMIN_EMAIL", "ADMIN_PASSWORD"):
            os.environ.pop(name, None)

    def _event(self, **extra):
        event = {"event_type": "conference_page_view", "session_id": "d8b7246d-6ca2-4b06-bd95-e1791f7c5f0e", "page": "/barcelona-2026", "utm_campaign": "ddce_barcelona_2026", "device_category": "mobile"}
        event.update(extra)
        return event

    def _auth(self):
        return {"Authorization": "Basic " + b64encode(b"admin@example.org:test-password").decode()}

    def test_conference_page_and_configured_links_load(self):
        response = self.client.get("/barcelona-2026")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"WarheadHunter", response.data)
        self.assertIn(b"https://warheadhunter.com", response.data)
        self.assertIn(b"https://pymacs.com", response.data)
        self.assertIn(b"https://autodockvina.com", response.data)
        self.assertIn(b"https://github.com/Joey305/JARI", response.data)
        self.assertIn(b"https://www.youtube.com/@DigitalDrugTraining", response.data)

    def test_event_validation_and_campaign_summary(self):
        self.assertEqual(self.client.post("/api/analytics/event", json=self._event()).status_code, 202)
        self.assertEqual(self.client.post("/api/analytics/event", json={"event_type": "anything"}).status_code, 400)
        self.client.post("/api/analytics/event", json=self._event(event_type="ecosystem_tool_click", tool_name="WarheadHunter", ecosystem_stage="Warhead Discovery", destination="https://warheadhunter.com"))
        response = self.client.get("/admin/analytics/summary?range=all&campaign=ddce_barcelona_2026", headers=self._auth())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["tool_clicks"], 1)

    def test_dashboard_requires_authorization(self):
        self.assertEqual(self.client.get("/admin/analytics").status_code, 401)
        self.assertEqual(self.client.get("/admin/analytics", headers=self._auth()).status_code, 200)

    def test_randy_configuration_skips_ephemeral_store(self):
        os.environ["ANALYTICS_RANDY_URL"] = "https://randy.example/backup/analytics"
        os.environ["ANALYTICS_RANDY_TOKEN"] = "receiver-token"
        from app import create_app
        app = create_app()
        self.assertTrue(app.config["ANALYTICS_DB_PATH"])
        os.environ.pop("ANALYTICS_RANDY_URL", None)
        os.environ.pop("ANALYTICS_RANDY_TOKEN", None)

    def test_vlismod_detail_rollup_preserves_workflow_daily_series(self):
        os.environ["ANALYTICS_RANDY_URL"] = "https://randy.example/backup/analytics"
        os.environ["ANALYTICS_RANDY_TOKEN"] = "builder-token"
        os.environ["VLISMOD_ANALYTICS_TOKEN"] = "vlismod-token"
        payload = {
            "ok": True,
            "summary": {"unique_visitors": 2, "sessions": 3, "page_views": 4},
            "daily": [{"date": "2026-10-13", "page_views": 4, "sessions": 3, "workflow_starts": 2, "completed": 1, "exports": 1, "handoffs": 1}],
            "operations": {"submitted": 2, "completed": 1, "failed": 0, "empty_results": [], "performance": [], "segmentation": [], "alerts": []},
            "engagement": {"new_visitors": 2, "returning_visitors": 0, "engaged_sessions": 1, "research_sessions": 1},
            "handoffs": {"total": 1, "cross_tool": {"initiated": 1, "builder_arrived": None}},
            "workflows": [], "funnel": [], "countries": [], "referrers": [], "pages": [],
        }
        response = Mock(ok=True)
        response.json.return_value = payload
        with patch("protac_builder.analytics.requests.get", return_value=response):
            from protac_builder.analytics import ecosystem_dashboard
            report, available = ecosystem_dashboard("vlismod", "all")
        self.assertTrue(available)
        self.assertEqual(report["daily"][0]["workflow_starts"], 2)
        self.assertEqual(report["daily"][0]["handoffs"], 1)


if __name__ == "__main__":
    unittest.main()
