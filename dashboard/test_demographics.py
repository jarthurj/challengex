"""Household groups before FY2025: the one-year "by Income and Age / Education" tables."""
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .crosstab import check_heading, crosstab_values, income_band
from .management.commands.verify_pdfs import crosstab_page
from .models import MethodologyBreak, Observation
from .testdata import load_real_tables

# FY2009 Table 4.4 as extracted: income bands as rows, ages then Average as columns.
ROWS = [
    ("Under $35", ["2.8", "3.6", "3.5", "3.4"]),
    ("$35 to $65", ["3.7", "5.2", "4.9", "4.8"]),
    ("$65 to $100", ["4.7", "5.7", "6.1", "5.6"]),
    ("Over $100", ["4.6", "6.4", "7.4", "6.4"]),
    ("Average", ["3.7", "5.4", "5.0", "4.9"]),
]


class CrossTabTests(SimpleTestCase):
    def test_margins_give_the_groups_and_all_households(self):
        found = dict(crosstab_values(ROWS, "age"))
        self.assertEqual(found[("age", "Under 35")], "3.7")
        self.assertEqual(found[("age", "Over 55")], "5.0")
        self.assertEqual(found[("income", "Over $100K")], "6.4")
        self.assertEqual(found[("all", "All households")], "4.9")
        self.assertEqual(len(found), 3 + 4 + 1)

    def test_without_margins_only_the_column_groups(self):
        rows = [(label, values + ["9.9"]) for label, values in ROWS]  # education has four groups
        found = dict(crosstab_values(rows, "education", margins=False))
        self.assertEqual(list(found), [("education", "Less than high school"), ("education", "High school graduate"),
                                       ("education", "Some college or technical school graduate"),
                                       ("education", "College graduate")])

    def test_wrong_shapes_are_refused_not_guessed(self):
        with self.assertRaisesMessage(ValueError, "has 3 values for 4 columns"):
            crosstab_values([ROWS[0], ("$35 to $65", ["3.7", "5.2", "4.8"]), *ROWS[2:]], "age")
        with self.assertRaisesMessage(ValueError, "missing rows: Over $100K"):
            crosstab_values([r for r in ROWS if r[0] != "Over $100"], "age")

    def test_labels_and_heading(self):
        self.assertEqual(income_band("$35k to $65k"), "$35K to $65K")  # FY2003 prints "k"
        self.assertIsNone(income_band("Under 35"))
        self.assertIsNone(check_heading("Age of Head of Household Average Under 34 35 to 54 Over 55", "age"))
        self.assertIsNotNone(check_heading("Over 55 35 to 54 Under 35 Average", "age"))  # out of order
        self.assertIsNone(check_heading(  # FY2017: "Under" and "35" wrapped onto separate lines
            "Age of Head of Household Under col_4 35 to Over 55 Average 35 54", "age"))


class PdfPageTests(SimpleTestCase):
    def test_caption_source_line_and_split_rows(self):
        page = "\n".join([
            "As Table 5.4 shows, income matters.",  # a mention in the prose, not the caption
            "Table 5. 4:  ",
            "Advertising Mail Received by Income and Age ",
            "Source:  HDS Diary Sample, FY 2022.",  # printed above the table on some pages
            "Average ",
            "Under 35 35 to 54 Over 55 ",
            "Under $35 ",
            "1.0 1.2 1.8 1.4 ",  # FY2022+: values on the line after the label
            "$35 to $65 1.2 1.8 2.6 2.0 ",
            "$65 to $100 1.2 2.1 3.4 2.5 ",
            "Over $100 1.0 2.1 3.0 2.3 ",
            "Average 1.1 2.0 2.8 2.2 ",
            "Table 5.5: ",
            "Advertising Mail Sent by Income and Age",
            "Under $35 9.9 9.9 9.9 9.9 ",
        ])
        rows, heading, problem = crosstab_page(page, "Table 5.4", "Advertising Mail Received by Income and Age")
        self.assertIsNone(problem)
        self.assertIsNone(check_heading(heading, "age"))
        found = dict(crosstab_values(rows, "age"))
        self.assertEqual(found[("income", "Under $35K")], "1.4")
        self.assertEqual(found[("all", "All households")], "2.2")


class LoadDemographicsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def value(self, slug, dimension, group, year):
        o = Observation.objects.get(metric__slug=slug, segment__dimension=dimension, segment__value=group,
                                    fiscal_year=year)
        return o.raw_value, o.value, o.source_table.source_id

    def test_known_values(self):
        # FY2003 Table 5.4 ("Total", "Under $35k", "Under 34") and FY2023 Table 4.4
        self.assertEqual(self.value("transactions-received-per-household", "all", "All households", 2003),
                         ("5.3", 275.6, "2003-p040-2"))
        self.assertEqual(self.value("transactions-received-per-household", "age", "Under 35", 2003)[0], "4.4")
        self.assertEqual(self.value("transactions-received-per-household", "income", "Over $100K", 2023),
                         ("2.3", 119.6, "2023-p041-6"))
        self.assertEqual(self.value("advertising-mail-received-per-household", "education", "College graduate",
                                    2007)[0], "20.3")

    def test_fy2015_correspondence_margins_come_from_the_education_table(self):
        self.assertEqual(self.value("correspondence-received-per-household", "income", "Under $35K", 2015),
                         ("1.3", 67.6, "2015-p030-1"))
        self.assertFalse(Observation.objects.filter(metric__slug="correspondence-received-per-household",
                                                    segment__dimension="age", fiscal_year=2015).exists())

    def test_one_value_per_group_and_year_and_the_2014_break(self):
        transactions = Observation.objects.filter(metric__slug="transactions-received-per-household")
        self.assertEqual(transactions.count(), 18 * 8 + 18 * 4)  # age tables 3+4+1, education tables 4
        self.assertEqual(transactions.values("segment", "fiscal_year").distinct().count(), transactions.count())
        weighting = MethodologyBreak.objects.get(fiscal_year=2014)
        self.assertIn("transactions-received-per-household", weighting.metrics.values_list("slug", flat=True))

    def test_reclassifications_are_marked_on_the_one_year_series(self):
        # Each year comes from its own report, so every reclassification a later report made by
        # restating earlier years in Table E.2 is a break in these series, on the metrics it moved.
        def years(slug):
            return sorted(MethodologyBreak.objects.filter(metrics__slug=slug).values_list("fiscal_year", flat=True))
        self.assertEqual(years("correspondence-received-per-household"), [2008, 2012, 2014, 2015, 2017])
        self.assertEqual(years("transactions-received-per-household"), [2012, 2013, 2014, 2015, 2017])
        self.assertEqual(years("advertising-mail-received-per-household"), [2007, 2008, 2014])

    def test_advertising_starts_in_fy2005(self):
        # FY2005 Table 5.5 "Ad Mail Received by Income and Age"; FY2003's tables count unaddressed
        # mail too, so they aren't used.
        self.assertEqual(self.value("advertising-mail-received-per-household", "all", "All households", 2005),
                         ("17.3", 899.6, "2005-p045-1"))
        self.assertFalse(Observation.objects.filter(metric__slug="advertising-mail-received-per-household",
                                                    fiscal_year=2003).exists())
