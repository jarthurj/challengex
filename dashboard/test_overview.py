import csv
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import overview_views
from .models import Observation
from .testdata import load_real_tables


class FormatTests(SimpleTestCase):
    def test_values_and_changes_carry_units(self):
        self.assertEqual(overview_views.fmt(32228, "millions"), "32,228 million pieces")
        self.assertEqual(overview_views.fmt(637.3, "per_household_year"), "637.3 pieces per household per year")
        self.assertEqual(overview_views.fmt(14.0, "percent"), "14%")  # published as a whole percent
        self.assertEqual(overview_views.fmt_change(32228, 38958, "millions"), "-17.3% (-6,730 million pieces)")
        self.assertEqual(overview_views.fmt_change(14, 31, "percent"), "-17 percentage points")

    def test_csv_cells_that_look_like_formulas_are_quoted(self):
        self.assertEqual(overview_views.safe_cell("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(overview_views.safe_cell("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(overview_views.safe_cell(-17.3), -17.3)  # numbers are left alone
        self.assertEqual(overview_views.safe_cell("All households"), "All households")


class OverviewYearCsvTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def get(self, name, *args, query=""):
        return self.client.get(reverse(name, args=args) + query)

    def test_site_root_goes_to_the_welcome_page(self):
        self.assertRedirects(self.client.get("/"), reverse("welcome"))

    def test_overview_has_no_intro_paragraph(self):
        page = self.get("dashboard").content.decode()
        self.assertNotIn("Latest published values from the USPS Household Diary Study", page)
        self.assertNotIn("select a card's link for the full trend", page)
        self.assertIn("<h1>U.S. household mail at a glance</h1>", page)

    def test_overview_cards_show_latest_value_changes_and_sources(self):
        page = self.get("dashboard").content.decode()
        self.assertIn("637.3 pieces per household per year", page)  # all household mail, FY2025
        self.assertIn("vs. FY2020 (837.0 pieces per household per year)", page)
        self.assertIn("-23.9% (-199.7 pieces per household per year)", page)
        self.assertIn("32,228 million pieces", page)  # First-Class received, FY2023
        self.assertIn("FY2023 report, page 77", page)
        self.assertIn("-7 percentage points", page)  # bills by mail, 14% vs 21%
        self.assertIn("?trend=packages-per-household", page)

    def test_market_mix_shares_are_of_the_markets_shown(self):
        mix = overview_views.market_mix()
        self.assertEqual(mix["year"], 2025)
        self.assertEqual(len(mix["rows"]), 5)
        self.assertAlmostEqual(sum(r["share"] for r in mix["rows"]), 100)
        self.assertTrue(all(r["share"] > 0 for r in mix["rows"]))
        page = self.get("dashboard").content.decode()
        self.assertIn("also counted in another market", page)

    def test_year_page_lists_published_values_and_groups(self):
        page = self.get("year-detail", 2025).content.decode()
        self.assertIn("Household mail in FY2025", page)
        self.assertIn("Share of bills paid by mail", page)
        self.assertIn("Age of householder: 65 and Over", page)
        self.assertIn(reverse("year-csv", args=[2025]), page)
        self.assertIn(f"{reverse('table-list')}?year=2025", page)
        self.assertEqual(self.get("year-detail", 1999).status_code, 404)

    def test_year_form_validates_its_input(self):
        self.assertRedirects(self.get("year-pick", query="?year=2015"), reverse("year-detail", args=[2015]))
        self.assertRedirects(self.get("year-pick", query="?year=<script>"), reverse("year-detail", args=[2025]))

    def rows(self, response):
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        return list(csv.DictReader(StringIO(response.content.decode())))

    def test_year_csv_has_every_preferred_value_with_its_source(self):
        rows = self.rows(self.get("year-csv", 2025))
        self.assertEqual(len(rows), Observation.objects.filter(fiscal_year=2025, is_preferred=True).count())
        bills = next(r for r in rows if r["metric_slug"] == "bills-paid-by-mail-share"
                     and r["household_group"] == "All households")
        self.assertEqual((bills["value"], bills["source_table"], bills["kind"]), ("14.0", "2025-p062-1", "published"))

    def test_trend_csv_has_published_values_then_labelled_projections(self):
        rows = self.rows(self.get("trend-csv", query="?trend=fcm-received-total"))
        published = [r for r in rows if r["kind"] == "published"]
        projected = [r for r in rows if r["kind"].startswith("projection")]
        self.assertEqual((published[0]["fiscal_year"], published[-1]["fiscal_year"]), ("2000", "2023"))
        self.assertEqual([r["fiscal_year"] for r in projected], ["2024", "2025", "2026", "2027", "2028"])
        self.assertTrue(all(r["low_80"] and r["high_95"] and r["model"] for r in projected))
        self.assertTrue(all(r["source_table"] for r in published))
        page = self.get("trends", query="?trend=fcm-received-total").content.decode()
        self.assertIn(reverse("trend-csv") + "?trend=fcm-received-total", page)
