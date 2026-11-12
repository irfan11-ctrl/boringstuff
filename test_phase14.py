"""Phase 14 tests: legal pages, 404 page, retired tools, new AI actions, IP limit."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import create_app


def make_app(directory: str, **extra):
    config = {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(Path(directory) / "t.sqlite3")}
    config.update(extra)
    return create_app(config)


class Phase14Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = make_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_legal_pages_and_health(self) -> None:
        for path, text in (("/privacy", "Kebijakan Privasi"), ("/terms", "Ketentuan Penggunaan")):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code)
            self.assertIn(text, response.get_data(as_text=True))
        self.assertEqual("ok", self.client.get("/healthz").get_json()["status"])

    def test_unknown_page_is_html_but_unknown_api_stays_json(self) -> None:
        page = self.client.get("/nope")
        self.assertEqual(404, page.status_code)
        self.assertIn("text/html", page.content_type)
        api = self.client.get("/api/nope")
        self.assertEqual(404, api.status_code)
        self.assertIn("application/json", api.content_type)

    def test_security_headers_include_csp(self) -> None:
        headers = self.client.get("/").headers
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])

    def test_retired_tools_are_off_when_legacy_disabled(self) -> None:
        app = make_app(self.tmp.name, LEGACY_TOOLS_ENABLED=False)
        client = app.test_client()
        self.assertEqual(404, client.post("/api/pdf/compress").status_code)
        self.assertEqual(404, client.post("/api/captions/generate", json={}).status_code)

    def test_new_ai_actions_are_accepted_and_need_gemini(self) -> None:
        for action in ("polite", "formula"):
            response = self.client.post("/api/writing-tools", json={"action": action, "text": "hitung total kolom B kalau kolom A sama dengan Lunas"})
            self.assertEqual(503, response.status_code)
            self.assertEqual("ai_not_configured", response.get_json()["code"])

    def test_formula_action_calls_gemini_with_formula_instructions(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key"
        with mock.patch("app._gemini_text", return_value="=SUMIF(A:A;\"Lunas\";B:B)") as fake:
            response = self.client.post("/api/writing-tools", json={"action": "formula", "text": "total B jika A Lunas"})
        self.assertEqual(200, response.status_code)
        self.assertIn("Excel", fake.call_args[0][0])

    def test_ip_limit_blocks_many_sessions_from_one_address(self) -> None:
        self.app.config.update(GEMINI_API_KEY="test-key", AI_REQUESTS_PER_IP_HOUR=2)
        with mock.patch("app._gemini_text", return_value="ok result"):
            codes = []
            for _ in range(3):
                fresh = self.app.test_client()  # new cookie jar means a new session each time
                codes.append(fresh.post("/api/writing-tools", json={"action": "rewrite", "text": "halo"}).status_code)
        self.assertEqual([200, 200, 429], codes)


if __name__ == "__main__":
    unittest.main()
