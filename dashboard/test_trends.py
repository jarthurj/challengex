from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import MethodologyBreak, Metric, Observation, Segment
from .testdata import load_real_tables


class TrendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
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
        published = [y for y, v in values.items() if v is not None]
        self.assertEqual((published[0], published[-1]), (2000, 2023))  # the axis runs on for the projection
        source = chart["datasets"][0]["sources"][chart["years"].index(2020)]
        self.assertEqual(source["report_year"], 2023)
        self.assertFalse(source["verified"])

    def test_category_series_have_same_unit_and_do_not_mix_postal_scopes(self):
        chart = self.chart(trend="category_volume")
        published = [d for d in chart["datasets"] if not d.get("projection")]
        self.assertEqual(len(published), 3)
        values = [d["data"][chart["years"].index(2023)] for d in published]
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


class ChartCopyTests(TestCase):
    """"Copy the values with sources" on the Trends page: a tab-separated table for a report."""

    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def copy(self, **params):
        page = self.client.get(reverse("trends"), params).content.decode()
        start = page.index('<pre class="copy-source copy-visible" id="chart-copy">')
        return page, page[page.index(">", start) + 1:page.index("</pre>", start)]

    def test_every_published_value_is_copied_with_its_source(self):
        page, text = self.copy(trend="fcm-received-total")
        self.assertIn('data-copy="chart-copy" hidden>Copy the values with sources</button>', page)
        lines = text.splitlines()
        self.assertEqual(lines[0], "First-Class Mail received by households: All households (Millions of pieces)")
        header = lines.index("Fiscal year\tMetric\tValue (Millions of pieces)\tSource report\tPage\tTable\t"
                             "Verified against the PDF")
        end = lines.index("Projections: statistical estimates made by this dashboard, not published USPS figures.")
        rows = [line.split("\t") for line in lines[header + 1:end] if line.startswith("FY") and "\t" in line]
        published = [r for r in rows if len(r) == 7]
        self.assertEqual(len(published), Observation.objects.filter(
            metric__slug="fcm-received-total", segment__dimension="all", is_preferred=True).count())
        o = Observation.objects.select_related("source_table").get(
            metric__slug="fcm-received-total", segment__dimension="all", is_preferred=True, fiscal_year=2020)
        self.assertIn(["FY2020", "First-Class Mail received by households", "35,729", f"FY{o.report_year}",
                       str(o.source_table.page), o.source_table.source_id, "yes" if o.verified else "no"],
                      published)

    def test_breaks_and_projections_are_labelled(self):
        _, text = self.copy(trend="fcm-received-total")
        self.assertIn("Methodology changes (values on either side may not be comparable):", text)
        self.assertIn("Projections: statistical estimates made by this dashboard, not published USPS figures.", text)
        projected = [line.split("\t") for line in text.splitlines() if line.startswith("FY2028\t")]
        self.assertEqual(len(projected), 1)
        self.assertRegex(projected[0][3], r"^[\d,]+ to [\d,]+$")   # the 80% interval
        self.assertEqual(projected[0][6], "FY2010-FY2023, from the FY2010 methodology change")
        self.assertRegex(projected[0][7], r"^[\d,]+$")   # the chosen model's backtest error

    def test_the_category_chart_copies_all_three_lines_and_their_projections(self):
        _, text = self.copy(trend="category_volume")
        for name in ("First-Class correspondence received", "First-Class transaction mail received",
                     "First-Class advertising received (ads only)"):
            self.assertIn(f"FY2023\t{name}\t", text)
            self.assertIn(f"FY2028\t{name}\t", text)

    def test_gaps_are_named_not_filled(self):
        segment = Segment.objects.get(dimension="age", value="65 and Over")
        _, text = self.copy(trend="bills-paid-by-mail-share", segment=segment.pk)
        self.assertIn("No published value for Share of bills paid by mail in FY2016", text)
        self.assertNotIn("Projections:", text)

    def test_copied_text_is_escaped(self):
        Metric.objects.filter(slug="fcm-received-total").update(name="<b>Mail</b> & co")
        page, text = self.copy(trend="fcm-received-total")
        self.assertIn("&lt;b&gt;Mail&lt;/b&gt; &amp; co", text)
        self.assertNotIn("<b>Mail</b>", page)

    def test_the_csv_has_every_category_projection(self):
        response = self.client.get(reverse("trend-csv"), {"trend": "category_volume"})
        body = response.content.decode()
        self.assertEqual(body.count("projection (not a published figure)"), 15)
        for slug in ("fcm-received-correspondence", "fcm-received-transactions", "fcm-received-advertising"):
            self.assertIn(f",{slug},", body)
