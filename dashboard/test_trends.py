from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import MethodologyBreak, Metric, Observation, Segment


class TrendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())
        call_command("load_metrics", stdout=StringIO())

    def chart(self, **params):
        response = self.client.get(reverse("trend-data"), params)
        self.assertEqual(response.status_code, 200)
        return response.json()["chart"]

    def test_default_uses_restated_preferred_household_values_and_correct_unit(self):
        chart = self.chart()
        self.assertEqual(chart["unit"], "Millions of pieces")
        values = dict(zip(chart["years"], chart["datasets"][0]["data"]))
        self.assertEqual(values[2020], 35729)
        self.assertEqual(values[2023], 32228)
        self.assertEqual((chart["years"][0], chart["years"][-1]), (2000, 2023))
        source = chart["datasets"][0]["sources"][chart["years"].index(2020)]
        self.assertEqual(source["report_year"], 2023)
        self.assertFalse(source["verified"])

    def test_category_series_have_same_unit_and_do_not_mix_postal_scopes(self):
        chart = self.chart(trend="category_volume")
        self.assertEqual(len(chart["datasets"]), 3)
        values = [d["data"][chart["years"].index(2023)] for d in chart["datasets"]]
        self.assertEqual(values, [12864, 14879, 3236])
        response = self.client.get(reverse("trends"), {"trend": "category_volume"})
        self.assertContains(response, "do not represent all USPS mail")

    def test_sparse_demographic_years_have_null_gaps_and_keep_zero(self):
        segment = Segment.objects.get(dimension="age", value="65 and Over")
        Observation.objects.filter(
            metric__slug="bills-paid-by-mail-share", segment=segment, fiscal_year=2020
        ).update(value=0)
        chart = self.chart(trend="bills-paid-by-mail-share", segment=segment.pk)
        values = dict(zip(chart["years"], chart["datasets"][0]["data"]))
        self.assertIsNone(values[2016])
        self.assertEqual(values[2020], 0)
        self.assertEqual(values[2025], 22)
        self.assertEqual(chart["unit"], "Percent")

    def test_invalid_metric_and_segment_fall_back(self):
        self.assertEqual(self.chart(trend="<script>", segment="bad"), self.chart())
        self.assertEqual(self.chart(trend="total_volume"), self.chart())

    def test_scope_specific_and_global_breaks_are_shown_only_when_applicable(self):
        other = Metric.objects.get(slug="bills-paid-by-mail-share")
        change = MethodologyBreak.objects.create(fiscal_year=2015, title="Other metric only", description="Test")
        change.metrics.add(other)
        self.assertNotIn("Other metric only", [b["title"] for b in self.chart()["breaks"]])
        self.assertIn(2010, [b["year"] for b in self.chart()["breaks"]])
        self.assertIn("Other metric only", [b["title"] for b in self.chart(trend=other.slug)["breaks"]])

    def test_delays_are_explicitly_unavailable_and_do_not_load_chart(self):
        response = self.client.get(reverse("trends"), {"trend": "mail_delays"})
        self.assertContains(response, "missing data is not zero delays")
        self.assertNotContains(response, '<canvas')
        self.assertIsNone(self.chart(trend="mail_delays"))

    def test_html_fallback_sources_verification_and_notes_are_escaped(self):
        Observation.objects.filter(metric__slug="fcm-received-total").update(notes="<script>bad()</script>")
        response = self.client.get(reverse("trends"))
        self.assertContains(response, "Unverified")
        self.assertContains(response, "2023-p077-1")
        self.assertContains(response, "&lt;script&gt;bad()&lt;/script&gt;")
        self.assertNotContains(response, "<script>bad()</script>")

    def test_empty_database_renders_setup_notice(self):
        Metric.objects.all().delete()
        response = self.client.get(reverse("trends"))
        self.assertContains(response, "Run manage.py rebuild_db")
        self.assertNotContains(response, '<canvas')
