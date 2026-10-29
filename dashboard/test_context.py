"""Tests for the "From the report" excerpts and the tables re-read from their PDF pages.

They use the committed table_context.json and dashboard/fy2021_quotes.py; docs/ isn't needed.
"""
import json
import re
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from . import context, pdftables
from .fy2021_quotes import QUOTES
from .management.commands.extract_context import implausible, leaks, score

with open(settings.BASE_DIR / "table_context.json", encoding="utf-8") as f:
    TABLE_CONTEXT = json.load(f)
with open(settings.BASE_DIR / "table_titles.json", encoding="utf-8") as f:
    TITLES = json.load(f)


class SentenceTests(SimpleTestCase):
    def test_abbreviations_and_decimals_dont_end_sentences(self):
        text = "Mail fell 4.7 percent vs. 2020 in the U.S. Postal Service network. Table 1.1 shows it."
        self.assertEqual(context.sentences(text), [
            "Mail fell 4.7 percent vs. 2020 in the U.S. Postal Service network.", "Table 1.1 shows it."])

    def test_us_can_end_a_sentence(self):
        text = "Direct mail is popular with advertisers in the U.S. Although there is no equivalent measure."
        self.assertEqual(len(context.sentences(text)), 2)

    def test_mentions(self):
        self.assertTrue(context.mentions("Tables 5.6 and 5.7 show that...", "Table 5.7"))
        self.assertTrue(context.mentions("Table 6.4 and Table 6.5 show that...", "Table 6.5"))
        self.assertTrue(context.mentions("their counterparts (see Fig. 7.1).", "Figure 7.1"))
        self.assertTrue(context.mentions("As Figure 4.2 illustrates, ...", "Figure 4.1/4.2"))
        self.assertTrue(context.mentions("Figures 4.5a and 4.5b, show ...", "Figure 4.5b"))
        self.assertFalse(context.mentions("Figure 5.3 shows that...", "Table 5.3"))
        self.assertFalse(context.mentions("Table 5.10 presents...", "Table 5.1"))

    def test_caption_is_not_an_excerpt(self):
        paragraphs = {77: ["Table A8-5a Bills and Statements Received Pieces in Millions by Sender Type Years 2000 - 2016"],
                      20: ["As shown in Table A8-5a, bills fell."]}
        found = context.excerpts(paragraphs, "Table A8-5a", 77, "Bills and Statements Received Pieces in Millions")
        self.assertEqual(found, [(20, "As shown in Table A8-5a, bills fell.")])

    def test_short_lead_in_brings_the_next_sentence(self):
        paragraphs = {54: ["Another interesting result can be seen in Figure 5.5. In some cases, behavior differs."]}
        self.assertEqual(context.excerpts(paragraphs, "Figure 5.5", 54)[0][1],
                         "Another interesting result can be seen in Figure 5.5. In some cases, behavior differs.")

    def test_nearest_pages_first_and_at_most_three(self):
        paragraphs = {p: [f"Table 2.1 is discussed on page {p} of the report here."] for p in (5, 30, 19, 21, 60)}
        self.assertEqual([p for p, _ in context.excerpts(paragraphs, "Table 2.1", 20)], [19, 21, 30])


class ParagraphTests(SimpleTestCase):
    def block(self, text):
        return (0, 0, 0, 0, text, 0, 0)

    def test_source_line_and_run_in_heading_are_dropped(self):
        blocks = [self.block("Source: HDS Diary Sample, FY 2020.\n \nHousehold Size\nTable 6.4 and Table 6.5 show "
                             "that as households\nincrease in size, the number of periodicals increases.")]
        self.assertEqual(context.paragraphs_from_blocks(blocks), [
            "Table 6.4 and Table 6.5 show that as households increase in size, the number of periodicals increases."])

    def test_sentence_broken_across_columns_and_a_footnote(self):
        blocks = [self.block("Population parameters were based on Census counts. As Table B.12 shows, each\n"
                             "county was grouped according to its location within these"),
                  self.block("1 Core-Based Statistical Area (CBSA) is defined within the sample according to the "
                             "official definition."),
                  self.block("12 mutually exclusive and collectively exhaustive\ngeographic categories.")]
        paras = context.paragraphs_from_blocks(blocks)
        self.assertIn("As Table B.12 shows, each county was grouped according to its location within these 12 "
                      "mutually exclusive and collectively exhaustive geographic categories.", paras[0])

    def test_table_cells_dont_absorb_a_continuation(self):
        blocks = [self.block("Total Periodicals 4.9 100%"), self.block("percent respectively (see Table E.2).")]
        self.assertNotIn("Total Periodicals", " ".join(context.paragraphs_from_blocks(blocks)))

    def test_letter_spaced_page_header_is_dropped(self):
        blocks = [self.block("2 0 2 5 H O U S E H O L D M A I L S U R V E Y\n \nAppendix B: M E T H O D O L O G Y 6 6\n"
                             "combinations of the factors that define strata to ensure a minimum size.")]
        self.assertEqual(context.paragraphs_from_blocks(blocks),
                         ["combinations of the factors that define strata to ensure a minimum size."])

    def test_paragraph_continued_on_the_next_page(self):
        pages = context.stitch({75: ["Intro sentence here. The strata definitions in Table B.2 collapse some possible"],
                                76: ["combinations of factors to ensure a minimum size.", "Next paragraph."]})
        self.assertTrue(pages[75][0].endswith("collapse some possible combinations of factors to ensure a minimum size."))
        self.assertEqual(pages[76], ["Next paragraph."])

    def test_hyphenated_line_breaks_keep_the_printed_hyphen(self):
        self.assertEqual(context.join_lines(["the pandemic-", "related decline in the 35-", "54 age range"]),
                         "the pandemic-related decline in the 35-54 age range")


class Fy2021QuoteTests(SimpleTestCase):
    def test_every_transcribed_sentence_refers_to_a_table_or_figure(self):
        for page, quotes in QUOTES.items():
            self.assertTrue(9 <= page <= 69 or 88 <= page <= 100, page)  # scanned chapter / Appendix B pages
            for quote in quotes:
                self.assertRegex(quote, context.REF, quote)
                self.assertRegex(quote, r"[.:]$", quote)

    def test_scanned_tables_get_transcribed_excerpts(self):
        e = TABLE_CONTEXT["2021-p035-1"]["excerpts"]  # Table 4.1, a scanned page
        self.assertTrue(e and all(x["from_image"] for x in e))
        self.assertIn("As Table 4.1 illustrates, in 2021 total transaction mail sent and received by households "
                      "fell 5.1% from 2020.", [x["text"] for x in e])


class TableContextFileTests(SimpleTestCase):
    def test_every_data_table_has_an_entry(self):
        with open(settings.BASE_DIR / "tables.json", encoding="utf-8") as f:
            ids = {t["id"] for t in json.load(f) if not TITLES[t["id"]]["title"].startswith("Survey form")}
        self.assertEqual(set(TABLE_CONTEXT), ids)

    def test_excerpts_mention_their_table_and_tables_without_say_why(self):
        for sid, entry in TABLE_CONTEXT.items():
            number = TITLES[sid]["table_number"]
            for e in entry["excerpts"]:
                self.assertTrue(context.mentions(e["text"], number), (sid, e["text"]))
                self.assertEqual(e["from_image"], sid.startswith("2021") and e["page"] in QUOTES, sid)
            self.assertTrue(entry["excerpts"] or entry["why_none"], sid)

    def test_coverage_does_not_regress(self):
        with_context = sum(1 for e in TABLE_CONTEXT.values() if e["excerpts"])
        self.assertGreaterEqual(with_context, 790)
        self.assertGreaterEqual(sum(1 for e in TABLE_CONTEXT.values() if e["structure"]), 50)


class ReReadTests(SimpleTestCase):
    def test_consistent_needs_every_extracted_number_in_order(self):
        rebuilt = {"headers": ["Household Income", "Under 35", "35 to 54"], "groups": [],
                   "rows": [["Under $35", "0.2", "0.6"], ["Average", "0.4", "0.7"]]}
        self.assertTrue(pdftables.consistent([["0.2", "0.6"], ["Average", "0.4", "0.7"]], rebuilt))
        self.assertFalse(pdftables.consistent([["0.6", "0.2"]], rebuilt))
        self.assertFalse(pdftables.consistent([["0.9"]], rebuilt))

    def test_implausible_re_reads_are_rejected(self):
        good = {"headers": ["Type", "Received", "Sent"], "groups": [], "rows": [["Broadband", "1.0", "0.1"]]}
        tidied = {"rows": [["Broadband", "1.0", "0.1"]]}
        self.assertEqual(implausible(good, tidied), "")
        wrapped = dict(good, rows=[["", "35", "54"]])
        self.assertIn("header line", implausible(wrapped, {"rows": [[""]]}))
        split = dict(good, rows=good["rows"] + [["Services", "", ""]])
        self.assertIn("number of rows", implausible(split, tidied))
        self.assertTrue(leaks(dict(good, headers=["(Pieces per Household per Week)", "a", "b"]), "Title"))

    def test_score_counts_unnamed_columns_and_missing_labels(self):
        self.assertEqual(score(["Type", "Column 2", "Sent"], [["", "1.0", "0.1"]]), 2)


class TablePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_tables", str(settings.BASE_DIR / "tables.json"), stdout=StringIO())

    def page(self, source_id, query=""):
        from .models import Table
        return self.client.get(f"/dashboard/tables/{Table.objects.get(source_id=source_id).pk}/{query}").content.decode()

    def test_from_the_report_quotes_with_page(self):
        page = self.page("2016-p067-8")  # Table 7.7
        self.assertIn("From the report", page)
        self.assertIn("Table 7.7 shows the packages sent and received by households", page)
        self.assertIn("FY2016 report, PDF page 67", page)

    def test_scanned_page_quote_is_labelled(self):
        self.assertIn("transcribed from the scanned page image", self.page("2021-p035-1"))

    def test_table_without_discussion_says_why(self):
        sid = next(k for k, v in TABLE_CONTEXT.items() if not v["excerpts"] and "never refers" in v["why_none"])
        self.assertIn("never refers to", self.page(sid))

    def test_re_read_layout_is_used_and_raw_still_available(self):
        page = self.page("2016-p037-1")  # Table 4.2: the extraction put the group heading in a column's place
        self.assertIn('colspan="4">Educational Attainment of Head of Household', page)
        self.assertIn('<th scope="col">Less than High School</th>', page)
        self.assertIn("re-read from the table", page)
        raw = self.page("2016-p037-1", "?raw=1")
        self.assertNotIn("re-read from the table", raw)

    def test_row_labels_recovered(self):
        page = self.page("2016-p011-1")  # Table E.5: the extraction lost its row labels
        for label in ("Newspapers", "Magazines", "Total Periodicals"):
            self.assertIn(f'<th scope="row" class="label">{label}', page)

    def test_quotes_are_escaped(self):
        sid = next(k for k, v in TABLE_CONTEXT.items() if any('"Other"' in e["text"] for e in v["excerpts"]))
        page = self.page(sid)  # FY2021 Table 5.1: the quote contains "Other" in quotation marks
        self.assertIn("&quot;Other&quot;", page)
        self.assertFalse(re.search(r'[^=]"Other"', page))
