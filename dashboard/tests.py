from collections import Counter
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from . import titles
from .tidy import tidy
from .management.commands import verify_pdfs
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


class PdfTextTests(SimpleTestCase):
    """Parsing of PDF page text used by `verify_pdfs` (the PDFs themselves are git-ignored)."""

    PAGE = "\n".join([
        "Table A8-1 First Class Mail Received by Type",
        "2010 2011 2012",
        "   I nsurance  2,001 2,602 2,443",
        "Total 15,995 16,281 16,311",
        "Total 23,263 22,906 22,501",
        "Total First-Class Received 50,063 48,272 47,204",
        "Under 45 17% 10% 6%",
    ])

    def test_split_letters_and_repeated_labels(self):
        self.assertEqual(verify_pdfs.label_rows(self.PAGE, "Insurance"), [["2,001", "2,602", "2,443"]])
        found, _ = verify_pdfs.page_series(self.PAGE, "Total", 2)
        self.assertEqual(found, {2010: "23,263", 2011: "22,906", 2012: "22,501"})
        found, _ = verify_pdfs.page_series(self.PAGE, "Total First-Class Received", 1)
        self.assertEqual(found[2012], "47,204")

    def test_label_containing_digits(self):
        self.assertEqual(verify_pdfs.label_rows(self.PAGE, "Under 45"), [["17%", "10%", "6%"]])

    def test_count_mismatch_is_reported_not_guessed(self):
        # As in FY2023 A8-1: "554" extracted as "5 54", giving one token too many.
        found, problem = verify_pdfs.page_series(self.PAGE + "\nOther Social 5 54 642 582", "Other Social", 1)
        self.assertIsNone(found)
        self.assertIn("4 numbers for 3 years", problem)

    def test_note_keeps_reviewer_text(self):
        notes = verify_pdfs.set_note("Checked by Sam", "[pdf-check] old")
        notes = verify_pdfs.set_note(notes, "matches docs/2023.pdf p.77 (35,729)")
        self.assertEqual(notes, "Checked by Sam\n[pdf-check] matches docs/2023.pdf p.77 (35,729)")


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

    def test_full_reload_is_idempotent_and_keeps_review(self):
        obs = self.preferred("fcm-received-total", 2023)
        obs.verified, obs.notes = True, "Checked against 2023.pdf p.77"
        obs.save()
        before = Observation.objects.count()
        table_pk = obs.source_table.pk

        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())
        call_command("load_metrics", stdout=StringIO())

        self.assertEqual(Observation.objects.count(), before)
        self.assertEqual(Metric.objects.count(), len(METRICS))
        self.assertEqual(MethodologyBreak.objects.count(), 3)
        reloaded = self.preferred("fcm-received-total", 2023)
        self.assertTrue(reloaded.verified)
        self.assertEqual(reloaded.notes, "Checked against 2023.pdf p.77")
        self.assertEqual(reloaded.source_table.pk, table_pk)  # table URLs stay stable

    def test_review_notes_from_code_are_applied(self):
        obs = Observation.objects.get(metric__slug="fcm-received-correspondence", fiscal_year=2007,
                                      report_year=2020)
        self.assertIn("Source inconsistency", obs.notes)

    def test_table_page_shows_tidied_columns_and_raw_on_request(self):
        pk = Table.objects.get(source_id="2016-p021-8").pk
        page = self.client.get(f"/dashboard/tables/{pk}/").content.decode()
        self.assertIn('colspan="4">Educational Attainment of Head of Household', page)
        self.assertIn('<th scope="col">High School Graduate</th>', page)
        self.assertNotIn("col_5", page)
        raw = self.client.get(f"/dashboard/tables/{pk}/?raw=1").content.decode()
        self.assertIn("col_5", raw)

    def test_recovered_titles_are_applied(self):
        t = Table.objects.get(source_id="2016-p050-2")  # extracted as "Table 5.6" with no title
        self.assertEqual(t.table_number, "Table 5.5")
        self.assertEqual(t.title, "Advertising Mail Received by Income and Age (Pieces per Household per Week)")
        self.assertLess(Table.objects.filter(title="").count(), 100)


class RebuildDbTests(TestCase):
    def test_rebuild_fills_an_empty_database_and_keeps_local_work(self):
        from django.contrib.auth.models import User
        call_command("rebuild_db", skip_verify=True, stdout=StringIO())
        self.assertEqual(Table.objects.count(), 1095)
        self.assertEqual(Observation.objects.count(), 313)

        User.objects.create_superuser("me", "me@example.com", "pw")
        obs = Observation.objects.filter(metric__slug="fcm-received-total", is_preferred=True).first()
        obs.verified, obs.notes = True, "checked by hand"
        obs.save()

        call_command("rebuild_db", skip_verify=True, stdout=StringIO())  # re-run on the same database

        self.assertTrue(User.objects.filter(username="me").exists())
        # load_metrics recreates observations, so look this one up by its natural key
        obs = Observation.objects.get(metric=obs.metric, segment=obs.segment, fiscal_year=obs.fiscal_year,
                                      report_year=obs.report_year)
        self.assertTrue(obs.verified)
        self.assertEqual(obs.notes, "checked by hand")


class TidyTests(SimpleTestCase):
    """Column-name repair for display (dashboard/tidy.py), on the shapes found in tables.json."""

    def test_names_shifted_right_of_values_with_group_heading(self):
        # 2016-p021-8: each name sits one column right of its numbers; the group heading took a slot.
        cols = ["Mail Received", "Households (Millions)", "Educational Attainment of Head of Household",
                "Less than High School", "col_5", "High School Graduate", "col_7", "College Graduate"]
        out = tidy(cols, [["45 or more", "4.8", "8%", "", "18%", "", "59%", ""]])
        self.assertEqual(out["headers"], ["Mail Received", "Households (Millions)", "Less than High School",
                                          "High School Graduate", "College Graduate"])
        self.assertEqual(out["rows"], [["45 or more", "4.8", "8%", "18%", "59%"]])
        self.assertEqual(out["groups"], [("", 1), ("", 1), ("Educational Attainment of Head of Household", 3)])

    def test_years_row_promoted_and_realigned_caption_dropped(self):
        # 2023-p077-1: caption in columns[0], years as the first data row, values one column left.
        cols = ["Table A8-1 First Class Mail Received by Type", "col_2", "col_3", "col_4", "col_5"]
        rows = [["", "", "2010", "", "2011"], ["Personal", "4,855", "", "4,301", ""],
                ["", "Note: Beginning in 2010 data was restated.", "", "", ""]]
        out = tidy(cols, rows)
        self.assertEqual(out["headers"], ["", "2010", "2011"])
        self.assertEqual(out["rows"], [["Personal", "4,855", "4,301"]])
        self.assertEqual(out["footnotes"], ["Note: Beginning in 2010 data was restated."])

    def test_label_heading_left_of_values_and_units_from_title(self):
        # 2016-p050-3: "Household Size" belongs to the label column; the value column is unnamed.
        out = tidy(["col_1", "Household Size", "col_3"],
                   [["One person", "", "9.6"], ["", "Source: HDS Diary Sample, FY 2016.", ""]],
                   "Advertising Mail Received by Size of Household (Pieces per Household per Week)")
        self.assertEqual(out["headers"], ["Household Size", "Pieces per Household per Week"])
        self.assertEqual(out["rows"], [["One person", "9.6"]])

    def test_repeated_header_removed_and_section_label_kept(self):
        out = tidy(["Market", "2019", "2020"], [["Market", "2019", "2020"], ["Correspondence", "15.1", "15.1"]])
        self.assertEqual(out["rows"], [["Correspondence", "15.1", "15.1"]])
        out = tidy(["Industry", "col_2"], [["Financial", "Bills (Millions)"], ["Bank", "863"]])
        self.assertEqual(out["headers"], ["Industry", "Bills (Millions)"])
        self.assertEqual(out["rows"][0], ["Financial", ""])

    def test_unrecoverable_names_are_labelled_not_guessed(self):
        out = tidy(["Label", "col_2", "col_3"], [["A", "1.0", "2.0"]])
        self.assertEqual(out["headers"], ["Label", "Column 2", "Column 3"])
        self.assertTrue(out["notes"])


class TitleTests(SimpleTestCase):
    """dashboard/titles.py on small synthetic pages (the PDFs themselves are git-ignored)."""

    PAGE = [
        "As Table 5.5 illustrates, households headed by an older person receive more mail.",
        "Table 5.6:",
        "Advertising Mail Received by Size of Household",
        "(Pieces per Household per Week)",
        "Household Size",
        "One person 9.6",
        "Two 12.8",
        "Three 12.7",
        "Average 12.1",
        "Table 5.7:",
        "Advertising Mail Received by Number",
        "of Adults",
        "(Pieces per Household per Week)",
        "One 9.4",
        "Two 12.8",
        "Three or more 14.1",
        "Average 12.1",
    ]
    SIZE = {"id": "2016-p050-3", "year": 2016, "page": 50, "table_number": "", "title": "", "columns": ["", "Household Size", ""],
            "rows": [["One person", "", "9.6"], ["Two", "", "12.8"], ["Three", "", "12.7"], ["Average", "", "12.1"]]}
    ADULTS = {"id": "2016-p050-4", "year": 2016, "page": 50, "table_number": "Table 5.6", "title": "presents these data",
              "columns": ["", "Adults", ""],
              "rows": [["One", "", "9.4"], ["Two", "", "12.8"], ["Three or more", "", "14.1"], ["Average", "", "12.1"]]}

    def test_captions_skip_prose_and_join_wrapped_titles(self):
        caps = titles.captions(self.PAGE)
        self.assertEqual([c["num"] for c in caps], ["Table 5.6", "Table 5.7"])
        self.assertEqual(titles.title_for(caps[1], {}),
                         "Advertising Mail Received by Number of Adults (Pieces per Household per Week)")

    def test_rows_vote_and_shared_rows_are_ignored(self):
        # "Two 12.8" and "Average 12.1" appear under both captions, so only the other rows count.
        got = titles.assign_page([self.SIZE, self.ADULTS], self.PAGE, {})
        self.assertEqual(got["2016-p050-3"][0]["num"], "Table 5.6")
        self.assertEqual(got["2016-p050-4"][0]["num"], "Table 5.7")

    def test_list_of_tables_title_is_preferred(self):
        records = titles.assign_report([self.SIZE], {
            3: ["Table 5.6: Advertising Mail Received by Size of Household ........ 50",
                "Table 5.7: Advertising Mail Received by Number of Adults ........ 50",
                "Table 5.8: Advertising Mail Received by Internet Access ........ 51",
                "Table 5.9: Income and Education by Type of Internet Access ...... 51"],
            50: self.PAGE,
        })
        self.assertEqual(records["2016-p050-3"]["title"],
                         "Advertising Mail Received by Size of Household (Pieces per Household per Week)")

    def test_number_spacing_and_years_in_titles(self):
        self.assertEqual(titles.fix_line("Table 7. 1:"), "Table 7.1:")
        self.assertEqual(titles.fix_line("Table B.1 1:"), "Table B.11:")
        cap = titles.captions(["Table 1.1:", "Total Mail Volume: FY 2020, 2021, and 2022", "(Billions of Pieces)",
                               "Mail Classification 2020 2021 2022"])[0]
        self.assertEqual(titles.title_for(cap, {}), "Total Mail Volume: FY 2020, 2021, and 2022 (Billions of Pieces)")

    def test_scanned_page_without_matching_caption_stays_untitled(self):
        t = {**self.SIZE, "title": "lacsdA an Argon"}
        records = titles.assign_report([t], {50: []})
        self.assertNotIn("title", records["2016-p050-3"])
        self.assertTrue(records["2016-p050-3"]["method"].startswith("none"))

    def test_survey_forms_are_labelled_not_guessed(self):
        form = {**self.SIZE, "id": "2016-p191-1", "page": 191}
        records = titles.assign_report([form], {191: ["Answer Sheet Purple", "Mail Piece"]})
        self.assertEqual(records["2016-p191-1"]["title"], titles.SURVEY_FORM_TITLE)
        self.assertEqual(records["2016-p191-1"]["table_number"], "")
