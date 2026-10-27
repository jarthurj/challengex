from collections import Counter
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .management.commands.load_metrics import mark_preferred, row_values, year_header
from .metric_sources import CONVERSIONS, METRICS, SOURCES
from .models import MethodologyBreak, Metric, Observation, Table


class YearHeaderTests(SimpleTestCase):
    def test_aligned_layout(self):
        lines = [["Table A8-6 Shares of Bills Paid", "", ""], ["Method", "2000", "2001"]]
        self.assertEqual(year_header(lines), [2000, 2001])

    def test_interleaved_layout(self):
        # FY2023-style: years and values sit in alternating, shifted columns.
        lines = [["", "", "2010", "", "2011"]]
        self.assertEqual(year_header(lines), [2010, 2011])
        self.assertEqual(row_values(["Personal", "4,855", "", "4,301", ""]), ["4,855", "4,301"])

    def test_ignores_ranges_and_single_years(self):
        lines = [["", "% change 2015-2025"], ["Mail Flows", "2015", "2020", "2025", "", "2015-2025"]]
        self.assertEqual(year_header(lines), [2015, 2020, 2025])

    def test_no_header(self):
        self.assertIsNone(year_header([["Label", "12", "13"]]))


class PreferenceTests(SimpleTestCase):
    def obs(self, report_year, ocr=False):
        return Observation(metric_id=1, segment_id=1, fiscal_year=2020,
                           report_year=report_year, source_table=Table(ocr=ocr))

    def test_latest_report_wins(self):
        old, new = self.obs(2020), self.obs(2023)
        mark_preferred([old, new])
        self.assertTrue(new.is_preferred)
        self.assertFalse(old.is_preferred)

    def test_ocr_loses_to_older_clean_report(self):
        clean, ocr = self.obs(2020), self.obs(2021, ocr=True)
        mark_preferred([clean, ocr])
        self.assertTrue(clean.is_preferred)
        self.assertFalse(ocr.is_preferred)


class ConversionTests(SimpleTestCase):
    def test_per_week_to_per_year(self):
        self.assertEqual(CONVERSIONS["per_household_week", "per_household_year"](2.5), 130)


class MappingTests(SimpleTestCase):
    def test_sources_reference_declared_metrics(self):
        slugs = {m["slug"] for m in METRICS}
        for source_id, (_, row_maps) in SOURCES.items():
            for rm in row_maps:
                self.assertIn(rm.metric, slugs, source_id)


class LoadMetricsTests(TestCase):
    """End to end against the real tables.json."""

    @classmethod
    def setUpTestData(cls):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())
        call_command("load_metrics", stdout=StringIO())

    def preferred(self, slug, year, dimension="all"):
        return Observation.objects.get(metric__slug=slug, fiscal_year=year,
                                       segment__dimension=dimension, is_preferred=True)

    def test_known_values(self):
        self.assertEqual(self.preferred("bills-paid-by-mail-share", 2000).value, 81)
        self.assertEqual(self.preferred("bills-paid-by-mail-share", 2024).value, 13)
        self.assertEqual(self.preferred("bills-paid-by-mail-share", 2025).value, 14)
        self.assertEqual(self.preferred("fcm-received-total", 2023).value, 32228)
        self.assertEqual(self.preferred("fcm-received-per-household", 2024).value, 221.7)

    def test_repeated_label_uses_occurrence(self):
        # A8-1 has two rows labelled "Total": correspondence first, transactions second.
        self.assertEqual(self.preferred("fcm-received-correspondence", 2023).value, 12864)
        self.assertEqual(self.preferred("fcm-received-transactions", 2023).value, 14879)

    def test_restatement_prefers_latest_report(self):
        values = dict(Observation.objects.filter(metric__slug="fcm-received-total", fiscal_year=2020)
                      .values_list("report_year", "value"))
        self.assertEqual(values[2020], 35345)  # as first published
        self.assertEqual(self.preferred("fcm-received-total", 2020).value, 35729)  # FY2023 restated

    def test_one_preferred_value_per_year(self):
        groups = Counter(Observation.objects.filter(is_preferred=True)
                         .values_list("metric", "segment", "fiscal_year"))
        self.assertTrue(groups)
        self.assertEqual(max(groups.values()), 1)

    def test_every_value_links_to_a_clean_source(self):
        self.assertFalse(Observation.objects.filter(source_table__ocr=True).exists())

    def test_fifteen_plus_years(self):
        years = self.preferred_years("bills-paid-by-mail-share")
        self.assertEqual((years[0], years[-1]), (2000, 2025))
        self.assertEqual(len(self.preferred_years("fcm-received-total")), 24)

    def preferred_years(self, slug):
        return sorted(Observation.objects.filter(metric__slug=slug, segment__dimension="all",
                                                 is_preferred=True).values_list("fiscal_year", flat=True))

    def test_demographic_segments(self):
        older = Observation.objects.get(metric__slug="bills-paid-by-mail-share", fiscal_year=2025,
                                        segment__dimension="age", segment__value="65 and Over")
        self.assertEqual(older.value, 22)
        dims = set(Observation.objects.filter(report_year=2025).values_list("segment__dimension", flat=True))
        self.assertEqual(dims, {"all", "age", "income", "education", "tenure", "msa"})

    def test_admin_review_pages_render(self):
        from django.contrib.auth.models import User
        self.client.force_login(User.objects.create_superuser("reviewer", "r@example.com", "pw"))
        for model in ["metric", "segment", "observation", "methodologybreak"]:
            self.assertEqual(self.client.get(f"/admin/dashboard/{model}/").status_code, 200, model)

    def test_reload_is_idempotent_and_keeps_review(self):
        obs = self.preferred("fcm-received-total", 2023)
        obs.verified, obs.notes = True, "Checked against 2023.pdf p.77"
        obs.save()
        before = Observation.objects.count()

        call_command("load_metrics", stdout=StringIO())

        self.assertEqual(Observation.objects.count(), before)
        self.assertEqual(Metric.objects.count(), len(METRICS))
        self.assertEqual(MethodologyBreak.objects.count(), 3)
        reloaded = self.preferred("fcm-received-total", 2023)
        self.assertTrue(reloaded.verified)
        self.assertEqual(reloaded.notes, "Checked against 2023.pdf p.77")
