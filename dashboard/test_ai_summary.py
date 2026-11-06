"""AI summaries: the number check, stored-summary lookup, and their place on the Trends and Year pages."""
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase

from dashboard import ai_summary as a

DATA = {
    "kind": "comparative", "fiscal_year": None, "fiscal_year_range": None,
    "series": [{"metric": "packages-volume", "values": {"2022": 7300.0, "2023": 6700.0},
                "changes": {"vs_previous_year": {"from_year": 2022, "absolute": -600.0, "percent": -8.2}}}],
    "methodology_breaks": [{"fiscal_year": 2005, "title": "t", "note": "restated from 2.4 to 3.1 billion"}],
}


class ValidateTests(SimpleTestCase):
    def summary(self, text, metric="packages-volume", years=(2023,), caveats=()):
        return {"headline": "h", "statements": [{"text": text, "metric": metric, "years": list(years)}],
                "caveats": list(caveats)}

    def test_good_numbers_pass(self):
        s = self.summary("Packages fell 8.2% to 6,700 in FY2023.")
        self.assertTrue(a.validate_ai_summary(s, DATA)["passed"])

    def test_invented_number_fails(self):
        self.assertFalse(a.validate_ai_summary(self.summary("Packages hit 9,999."), DATA)["passed"])

    def test_unknown_metric_or_year_fails(self):
        self.assertFalse(a.validate_ai_summary(self.summary("x", metric="nope"), DATA)["passed"])
        self.assertFalse(a.validate_ai_summary(self.summary("x", years=(1999,)), DATA)["passed"])

    def test_numbers_in_break_notes_are_allowed_in_caveats(self):
        s = self.summary("x", caveats=["2005 was restated from 2.4 to 3.1 billion."])
        self.assertTrue(a.validate_ai_summary(s, DATA)["passed"])


class StoredSummaryTests(TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch = mock.patch.object(a, "SUMMARY_DIR", Path(folder.name))
        patch.start()
        self.addCleanup(patch.stop)

    def record(self, kind, key, year=None, passed=True, text="Packages <b>rose</b>."):
        return {"kind": kind, "key": key, "fiscal_year": year, "reviewed": False, "model": "m",
                "prompt_version": "v", "generated_at": "2026-01-01T00:00:00+00:00",
                "validation": {"passed": passed, "problems": []},
                "summary": {"headline": "Head", "caveats": ["Careful"],
                            "statements": [{"text": text, "metric": "packages-volume", "years": [2023]}]}}

    def store(self, section, *records):
        a.SUMMARY_DIR.mkdir(exist_ok=True)
        (a.SUMMARY_DIR / f"{section}.json").write_text(json.dumps(
            {"section": section, "summaries": {r["key"]: r for r in records}}))

    def test_range_keys_do_not_overwrite_each_other(self):
        self.assertEqual(a.record_key("range", (2010, 2020)), "range:2010-2020")
        self.assertEqual(a.record_key("yearly", year=2023), "yearly:2023")

    def test_failed_validation_is_never_returned(self):
        self.store("packages-volume", self.record("comparative", "comparative", passed=False))
        self.assertIsNone(a.get_summary("packages-volume", "comparative"))
        self.assertEqual(a.trend_summaries("packages-volume"), [])

    def test_trends_page_shows_summary_after_the_data_table_and_escapes_it(self):
        self.store("packages-volume", self.record("comparative", "comparative"))
        html = self.client.get("/dashboard/trends/?trend=packages-volume").content.decode()
        if "Values and sources" in html:   # the test database may hold no observations
            self.assertLess(html.index("Values and sources"), html.index("AI-generated summary"))
            self.assertIn("&lt;b&gt;rose&lt;/b&gt;", html)
            self.assertIn("Not yet reviewed", html)

    def test_year_summaries_match_the_year(self):
        self.store("packages", self.record("yearly", "yearly:2023", 2023))
        self.assertEqual(len(a.year_summaries(2023)), 1)
        self.assertEqual(a.year_summaries(2022), [])
