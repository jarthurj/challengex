from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import forecast as F
from .models import Segment
from .testdata import load_real_tables


class ModelTests(SimpleTestCase):
    def test_naive_drift_and_linear(self):
        values = [10.0, 12.0, 14.0, 16.0]
        self.assertEqual(F.naive(values, 2), [16.0, 16.0])
        self.assertEqual(F.drift(values, 2), [18.0, 20.0])
        self.assertEqual(F.linear(values, 3), [18.0, 20.0, 22.0])

    def test_holt_follows_a_straight_line(self):
        values = [100.0 - 3 * i for i in range(12)]
        for got, want in zip(F.holt(values, 3), [64.0, 61.0, 58.0]):
            self.assertAlmostEqual(got, want, places=6)

    def test_backtest_only_scores_years_it_did_not_see(self):
        values = list(range(10))
        pairs = F.backtest(values, "naive", horizon=5, min_train=6)
        self.assertEqual([len(pairs[h]) for h in range(1, 6)], [4, 3, 2, 1, 0])
        self.assertEqual(pairs[1][0], (6, 5))  # trained on 0..5, actual 6, naive says 5


class WindowTests(SimpleTestCase):
    def test_uses_trailing_run_of_consecutive_years(self):
        years = [2000, 2001] + list(range(2010, 2020))
        window = F.fit_window(years, [float(y) for y in years], breaks=[])
        self.assertEqual((window["years"][0], window["years"][-1]), (2010, 2019))

    def test_fits_after_a_break_when_enough_years_remain(self):
        years = list(range(2000, 2024))
        window = F.fit_window(years, [1.0] * len(years), breaks=[2010, 2024])
        self.assertEqual(window["years"][0], 2010)
        self.assertEqual(window["after_break"], 2010)
        self.assertEqual(window["crossed"], [])

    def test_flags_breaks_too_late_to_fit_after(self):
        years = list(range(2010, 2026))
        window = F.fit_window(years, [1.0] * len(years), breaks=[2024, 2025])
        self.assertEqual(window["years"][0], 2010)
        self.assertEqual(window["crossed"], [2024, 2025])

    def test_too_few_years_gives_a_reason_not_a_projection(self):
        result = F.forecast([2015, 2020, 2025], [40.0, 30.0, 22.0], "percent")
        self.assertIn("at least 8 consecutive", result["reason"])
        self.assertNotIn("points", result)


class ForecastTests(SimpleTestCase):
    def setUp(self):
        self.years = list(range(2010, 2024))
        self.values = [50000 - 1400 * i + (300 if i % 2 else -300) for i in range(14)]

    def test_compares_every_model_with_the_naive_baseline(self):
        result = F.forecast(self.years, self.values, "millions")
        self.assertEqual({b["model"] for b in result["backtest"]}, set(F.MODELS))
        naive = next(b for b in result["backtest"] if b["model"] == "naive")
        self.assertEqual(naive["vs_naive"], 1.0)
        chosen = next(b for b in result["backtest"] if b["chosen"])
        self.assertEqual(chosen["mae"], min(b["mae"] for b in result["backtest"]))
        self.assertTrue(result["beats_naive"])

    def test_horizon_years_and_widening_intervals(self):
        points = F.forecast(self.years, self.values, "millions")["points"]
        self.assertEqual([p["year"] for p in points], [2024, 2025, 2026, 2027, 2028])
        widths = [p["hi80"] - p["lo80"] for p in points]
        self.assertEqual(widths, sorted(widths))
        for p in points:
            self.assertTrue(p["lo95"] <= p["lo80"] <= p["value"] <= p["hi80"] <= p["hi95"])

    def test_flat_series_keeps_the_naive_baseline(self):
        result = F.forecast(self.years, [100.0] * 14, "millions")
        self.assertEqual(result["model"], "naive")
        self.assertFalse(result["beats_naive"])

    def test_percent_projection_stays_between_0_and_100(self):
        years = list(range(2010, 2026))
        result = F.forecast(years, [60.0 - 4 * i for i in range(16)], "percent")
        for p in result["points"]:
            self.assertTrue(0 <= p["lo95"] <= p["value"] <= p["hi95"] <= 100)


class TrendForecastTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def data(self, **params):
        return self.client.get(reverse("trend-data"), params).json()

    def test_total_mail_projection_is_labelled_and_fit_after_the_2010_break(self):
        payload = self.data()
        self.assertEqual(payload["chart"]["years"][-5:], [2024, 2025, 2026, 2027, 2028])
        labels = [d["label"] for d in payload["chart"]["datasets"]]
        self.assertTrue(any(label.startswith("Projection (") for label in labels))
        self.assertIn("80% prediction interval", labels)
        self.assertEqual(payload["forecast"]["fit_years"], [2010, 2023])
        published = payload["chart"]["datasets"][0]["data"]
        self.assertEqual(published[-5:], [None] * 5)  # projections never enter the published series
        page = self.client.get(reverse("trends")).content.decode()
        self.assertIn("statistical projections, not published USPS figures", page)
        self.assertIn("Naive (last value)", page)

    def test_market_series_fit_after_the_fy2014_restatement(self):
        # 2003-2023 from Table E.2, but 2012 on is the one basis later reports share.
        payload = self.data(trend="packages-volume")
        self.assertEqual(payload["chart"]["years"][0], 2003)
        self.assertEqual(payload["forecast"]["fit_years"], [2012, 2023])
        self.assertEqual([b["year"] for b in payload["chart"]["breaks"]], [2005, 2010, 2012])

    def test_bills_projection_flags_the_2024_and_2025_changes(self):
        payload = self.data(trend="bills-paid-by-mail-share")
        self.assertEqual(payload["forecast"]["crossed_breaks"], [2024, 2025])
        page = self.client.get(reverse("trends"), {"trend": "bills-paid-by-mail-share"}).content.decode()
        self.assertIn("crosses later methodology changes (FY2024, FY2025)", page)

    def test_no_projection_for_sparse_groups_or_the_category_chart(self):
        segment = Segment.objects.get(dimension="age", value="65 and Over")
        payload = self.data(trend="bills-paid-by-mail-share", segment=segment.pk)
        self.assertIn("reason", payload["forecast"])
        self.assertEqual(payload["chart"]["years"][-1], 2025)
        self.assertIsNone(self.data(trend="category_volume")["forecast"])
        page = self.client.get(reverse("trends"), {"trend": "category_volume"}).content.decode()
        self.assertIn("Projections are shown when a single metric is selected", page)
