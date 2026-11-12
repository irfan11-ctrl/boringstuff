"""Dependency-free structural checks for the Boringstuff browser interface."""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import json
import unittest


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"


class InterfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.label_targets: list[str] = []
        self.tabs: list[dict[str, str]] = []
        self.panels: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "label" and values.get("for"):
            self.label_targets.append(values["for"])
        if values.get("role") == "tab":
            self.tabs.append(values)
        if values.get("role") == "tabpanel":
            self.panels.append(values)


class FrontendStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.parser = InterfaceParser()
        cls.parser.feed(cls.html)

    def test_ids_are_unique_and_labels_have_targets(self) -> None:
        duplicates = [key for key, count in Counter(self.parser.ids).items() if count > 1]
        self.assertEqual([], duplicates, f"Duplicate HTML IDs: {duplicates}")
        missing = sorted(set(self.parser.label_targets) - set(self.parser.ids))
        self.assertEqual([], missing, f"Labels reference missing controls: {missing}")

    def test_tool_tabs_reference_existing_panels(self) -> None:
        panel_ids = {panel.get("id") for panel in self.parser.panels}
        self.assertEqual(11, len(self.parser.tabs))
        self.assertEqual(13, len(self.parser.panels))
        for tab in self.parser.tabs:
            self.assertIn(tab.get("aria-controls"), panel_ids)
            self.assertTrue(tab.get("data-feature"))

    def test_everyday_tools_and_gemini_writing_desk_are_present(self) -> None:
        for required in (
            'id="panel-everyday"', 'id="everydayTool"', 'value="word"',
            'value="case"', 'value="duplicates"', 'value="clean"', 'value="bullets"',
            'id="writingToolsForm"', 'value="email_reply"', 'value="summarize"',
            'value="grammar"', 'value="translate"', '"/api/writing-tools"',
            'id="writingAiStatus"', 'id="writingLanguage"',
        ):
            self.assertIn(required, self.html)

    def test_donation_links_are_preserved(self) -> None:
        self.assertIn("https://trakteer.id/therealmen", self.html)
        self.assertIn("https://buymeacoffee.com/vantagesola", self.html)

    def test_mobile_breakpoints_and_touch_target_rules_exist(self) -> None:
        self.assertIn("@media (max-width: 767.98px)", self.html)
        self.assertIn("@media (max-width: 390px)", self.html)
        self.assertRegex(self.html, r"\.navbar-toggler\s*\{[^}]*min-height:\s*44px")
        self.assertRegex(self.html, r"\.form-control,\s*\.form-select\s*\{[^}]*font-size:\s*16px")

    def test_reduced_motion_support_is_present(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.html)
        self.assertIn("animation: none !important", self.html)

    def test_seo_metadata_and_structured_data_are_present(self) -> None:
        for required in (
            'name="description"',
            'name="robots"',
            'property="og:title"',
            'property="og:description"',
            'name="twitter:card"',
        ):
            self.assertIn(required, self.html)
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            self.html,
            re.S | re.I,
        )
        self.assertIsNotNone(match, "JSON-LD structured data is missing")
        structured_data = json.loads(match.group(1))
        self.assertEqual("SoftwareApplication", structured_data["@type"])
        self.assertEqual("BoringStuff", structured_data["name"])

    def test_luxury_loader_has_accessible_status_and_delayed_display(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="luxury-loader" id="luxuryLoader" aria-hidden="true">',
        )
        self.assertRegex(
            self.html,
            r'<div class="loader-card" role="status" aria-live="polite" aria-atomic="true">',
        )
        self.assertIn('luxuryLoader.setAttribute("aria-hidden", "false")', self.html)
        self.assertIn('luxuryLoader.setAttribute("aria-hidden", "true")', self.html)
        self.assertIn('window.setTimeout(() => {', self.html)
        self.assertIn('}, 180);', self.html)
        self.assertIn('520 - (Date.now() - loaderShownAt)', self.html)

    def test_ai_career_studio_and_privacy_notice_are_present(self) -> None:
        for required in (
            'id="panel-career"', 'id="resumeReviewForm"', 'id="interviewPrepForm"',
            '"/api/resume/analyze"', '"/api/interview/prepare"',
            'teks yang kamu kirim ke fitur ini diproses oleh Google Gemini',
        ):
            self.assertIn(required, self.html)

    def test_new_local_tools_are_present(self) -> None:
        for required in ('id="panel-split"', 'id="panel-diff"', 'id="panel-margin"', 'id="panel-table"',
                         'id="panel-photopdf"', 'id="panel-cleaner"', 'id="panel-qr"', 'id="panel-images"',
                         '/static/local-tools.js', '/static/file-tools.js', 'href="/privacy"', 'value="formula"', 'value="emails"'):
            self.assertIn(required, self.html)

    def test_document_output_shows_generation_source_badge(self) -> None:
        self.assertIn('id="documentGenerationBadge"', self.html)
        self.assertIn("Dibuat dengan Gemini AI", self.html)
        self.assertIn('role="status" aria-live="polite"', self.html)

    def test_inline_javascript_has_balanced_script_tags(self) -> None:
        javascript_scripts = re.findall(
            r"<script(?![^>]*application/ld\+json)(?:\s[^>]*)?>",
            self.html,
            re.I,
        )
        javascript_closers = re.findall(r"</script\s*>", self.html, re.I)
        self.assertEqual(4, len(javascript_scripts))
        self.assertEqual(5, len(javascript_closers))

    def test_primary_interface_uses_indonesian_copy(self) -> None:
        for required in (
            'id="toolsHeading">Pilih alat', 'id="tab-everyday"',
            '<h3>Peralatan Teks</h3>', 'id="libraryHeading">Perpustakaan saya',
            'id="runEveryday">Jalankan</button>', 'id="copyEveryday">Salin hasil</button>',
            'id="writingAction"', 'Terjemahkan ke',
            'option value="English">Bahasa Inggris', 'option value="Spanish">Spanyol',
        ):
            self.assertIn(required, self.html)
        self.assertNotIn('applicationKategori', self.html)
        self.assertNotIn('min-height'.replace('min', 'mnt'), self.html)

    def test_retired_tools_are_not_publicly_listed(self) -> None:
        for retired in ('id="tab-social"', 'id="tab-pdf"'):
            self.assertNotIn(retired, self.html)
        self.assertIn('data-legacy-panel="social"', self.html)
        self.assertIn('data-legacy-panel="pdf"', self.html)

    def test_browser_tools_have_input_and_memory_safety_limits(self) -> None:
        local_tools = (ROOT / "static" / "local-tools.js").read_text(encoding="utf-8")
        file_tools = (ROOT / "static" / "file-tools.js").read_text(encoding="utf-8")
        self.assertIn("margin > 100", local_tools)
        self.assertIn("20 * 1024 * 1024", local_tools)
        self.assertIn("100 * 1024 * 1024", local_tools)
        self.assertIn("30000000", local_tools)
        self.assertIn("30000000", file_tools)
        self.assertIn("(?:[ T].*)?$", file_tools)

    def test_local_text_counter_uses_unicode_aware_segmentation(self) -> None:
        self.assertIn("Intl.Segmenter", self.html)
        self.assertIn("kata ·", self.html)
        self.assertIn("Karakter tanpa spasi:", self.html)

    def test_split_and_margin_calculators_reject_invalid_values(self) -> None:
        local_tools = (ROOT / "static" / "local-tools.js").read_text(encoding="utf-8")
        self.assertIn("Nama orang tidak boleh duplikat", local_tools)
        self.assertIn("svcPct < 0", local_tools)
        self.assertIn("Biaya tetap, potongan, dan target margin tidak boleh negatif", local_tools)

    def test_external_javascript_references_existing_dom_ids(self) -> None:
        for relative in ("static/local-tools.js", "static/file-tools.js"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            refs = set(re.findall(r'\$\(["\']([^"\']+)', source))
            refs.update(re.findall(r'on\(["\']([^"\']+)', source))
            missing = sorted(refs - set(self.parser.ids))
            self.assertEqual([], missing, f"{relative} references missing DOM IDs: {missing}")


if __name__ == "__main__":
    unittest.main()
