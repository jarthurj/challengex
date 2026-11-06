"""The AI summaries tab: year by year, long term, search, categories, copy and export, the summary
page, the staff review mark, and "Create a summary" (Gemini mocked: no key or network needed)."""
import json
import re
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from dashboard import ai_summary as a
from dashboard import ai_views

from .testdata import load_real_tables

SOURCES = [{"metric": "packages-volume", "segment": {"dimension": "all", "value": "All households"},
            "sources": {"2020": {"report_year": 2023, "page": 10, "verified": True},
                        "2023": {"report_year": 2023, "page": 10, "verified": False}}}]


def record(text, key="comparative", kind="comparative", year=None, years=(2023,), metric="packages-volume",
           headline="Head", passed=True):
    return {"kind": kind, "key": key, "fiscal_year": year, "fiscal_year_range": None, "reviewed": False,
            "ai_generated": True, "model": "m", "prompt_version": "v", "input_hash": "old",
            "generated_at": "2026-01-01T00:00:00+00:00", "sources": SOURCES,
            "validation": {"passed": passed, "problems": [] if passed else ["made up"]},
            "summary": {"headline": headline, "caveats": ["Careful"],
                        "statements": [{"text": text, "metric": metric, "years": list(years)}]}}


def yearly(text, year, **kw):
    return record(text, key=f"yearly:{year}", kind="yearly", year=year, years=(year,), **kw)


class AiPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch = mock.patch.object(a, "SUMMARY_DIR", Path(folder.name))
        patch.start()
        self.addCleanup(patch.stop)
        a._CHECKS.clear()
        cache.clear()   # the live-request counters

    def store(self, section, *records):
        a.SUMMARY_DIR.mkdir(exist_ok=True)
        (a.SUMMARY_DIR / f"{section}.json").write_text(json.dumps(
            {"section": section, "summaries": {r["key"]: r for r in records}}), encoding="utf-8")

    def page(self, query=""):
        return self.client.get("/dashboard/ai/" + query).content.decode()

    # --- categories, views and the year slider ---

    def test_every_subject_has_a_category(self):
        for key in a.SECTIONS:
            self.assertIn(a.category_of(key), a.CATEGORY_ORDER, key)
        self.assertEqual(a.category_of("packages-volume"), "packages")
        self.assertEqual(a.category_of("bills-paid-by-mail-share"), "transactions-and-bill-payment")
        self.assertEqual(a.category_of("transactions-received-per-household"), "household-profile-and-demographics")
        self.assertEqual(a.category_of("first-class-mail-received-by-category"), "mail-volumes-and-flows")
        self.assertEqual(a.category_of("executive-summary"), "executive-summary")

    def test_year_by_year_is_the_default_with_a_year_dropdown(self):
        self.store("executive-summary", yearly("Packages were 6,300 million pieces in FY2020.", 2020))
        self.store("packages", yearly("Packages were 6,300 million pieces in FY2020.", 2020))
        self.store("packages-volume", yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        html = self.page()
        self.assertIn("<h2 id=\"results-heading\">FY2023, year by year</h2>", html)   # the latest stored year
        self.assertEqual(html.count('class="ai-item"'), 1)
        self.assertNotIn('type="range"', html)                                         # no slider
        self.assertNotRegex(html, r'<input[^>]+type="number"')                          # no typing box
        self.assertIn('<label for="summary-year">Fiscal year</label>', html)
        # the dropdown: each subject's latest year first, then the years with a stored summary, latest first
        select = html[html.index('<select id="summary-year"'):html.index("</select>", html.index('<select id="summary-year"'))]
        options = re.findall(r'<option value="([^"]+)"( selected)?>([^<]+)</option>', select)
        self.assertEqual([(v, t) for v, _, t in options],
                         [("latest", "Latest year for each subject"), ("2023", "FY2023"), ("2020", "FY2020")])
        self.assertEqual([v for v, s, _ in options if s], ["2023"])
        self.assertIn('<optgroup label="One fiscal year">', select)
        self.assertNotIn('class="button-link"', html[html.index('class="year-pick toolbar"'):])   # no separate button
        self.assertRegex(html, r'</select>\s*<button type="submit">Show</button>')
        # one toolbar: previous year, the dropdown, next year, stepping through the years it lists
        toolbar = html[html.index('class="year-pick toolbar"'):html.index("</form>", html.index('class="year-pick toolbar"'))]
        self.assertLess(toolbar.index("Previous year, "), toolbar.index('id="summary-year"'))
        self.assertIn('href="?view=year&amp;year=2020#results-heading"', html)
        self.assertNotIn("Next year, ", html)
        self.assertIn("All AI-generated, none reviewed by a person yet.", html)   # said once, for the whole list
        self.assertNotIn('<span class="badge">One year, FY2023</span>', html)     # the year is in the heading
        # another year: grouped by category, topic and subject sections together
        html = self.page("?view=year&year=2020")
        self.assertEqual(html.count('class="ai-item"'), 2)
        self.assertIn('<h3 id="cat-executive-summary">Executive summary</h3>', html)
        self.assertIn('<h3 id="cat-packages">Packages</h3>', html)
        self.assertLess(html.index("cat-executive-summary"), html.index('id="cat-packages"'))
        self.assertIn('href="#cat-packages"', html)   # jump links
        # a year with none says so and offers to create one for that year
        html = self.page("?view=year&year=2010")
        self.assertIn("No summaries match for FY2010", html)
        self.assertRegex(html, r'(?s)<select id="gen-year" name="year">.*?<option value="2010" selected>')
        # a typed year that isn't in the data falls back to the default, and says so
        for bad in ("1999", "abc", "2020.0", "２０２０", "-1", "9" * 5000, "<b>1</b>"):
            html = " ".join(self.page(f"?view=year&year={bad}").split())
            self.assertIn("FY2023, year by year", html)
            self.assertIn("isn't a fiscal year in the data (FY2000 to FY2025), so FY2023 is shown", html)
            self.assertNotIn("<b>1</b>", html)
        self.assertIn(" 2020 ", self.page("?view=year&year=%202020%20").replace('"', " "))   # spaces are fine

    def test_the_latest_year_for_each_subject(self):
        self.store("executive-summary", yearly("Packages were 6,300 million pieces in FY2020.", 2020),
                   yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        self.store("packages-volume", yearly("Packages were 6,300 million pieces in FY2020.", 2020),
                   yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        self.store("packages-per-household",
                   yearly("Packages were 9,999 pieces per household in FY2025.", 2025,
                          metric="packages-per-household"),                             # fails: hidden
                   yearly("Packages were 47.0 pieces per household per year in FY2020.", 2020,
                          metric="packages-per-household"))                             # so this one shows
        self.store("periodicals-volume", yearly("Periodicals were 3,900 million pieces in FY2020.", 2020,
                                                metric="periodicals-volume"))
        self.store("periodicals", record("Periodicals over time.", metric="periodicals-volume"))   # long term
        html = self.page("?view=year&year=latest")
        self.assertIn("The latest year for each subject", html)
        self.assertIn('<option value="latest" selected>Latest year for each subject</option>', html)
        dropdown = html[html.index('<select id="summary-year"'):html.index("</select>", html.index('<select id="summary-year"'))]
        self.assertNotRegex(dropdown, r'<option value="20\d\d" selected>')   # no fiscal year is the selection
        # each subject from its own latest year with a summary that shows, grouped by category
        self.assertEqual(html.count('class="ai-item"'), 4)   # yearly summaries only, one per subject
        self.assertIn('<h3 id="cat-executive-summary">Executive summary <span class="small">(FY2023)</span></h3>', html)
        self.assertIn('<h3 id="cat-packages">Packages <span class="small">(FY2020, FY2023)</span></h3>', html)
        self.assertIn('<h3 id="cat-periodicals">Periodicals <span class="small">(FY2020)</span></h3>', html)
        self.assertIn("Packages per household (One year, FY2020)", html)     # its FY2025 one is hidden
        self.assertNotIn("Packages sent and received by households (One year, FY2020)", html)   # FY2023 is its latest
        self.assertIn('<span class="badge">One year, FY2020</span>', html)   # years differ here, so rows say theirs
        self.assertIn('<span class="chevron" aria-hidden="true"></span>Overview<span class="visually-hidden">: '
                      'Executive summary</span>', html)   # a topic's own summary, under its own heading
        self.assertIn("1 stored summary is hidden", " ".join(html.split()))
        self.assertNotIn("Previous year", html)
        self.assertIn('href="/dashboard/ai/export.txt?view=year&amp;year=latest"', html)
        self.assertIn("Periodicals were 3,900", self.client.get("/dashboard/ai/export.txt?view=year&year=latest")
                      .content.decode())
        # it narrows like the other views: one category
        self.assertEqual(self.page("?view=year&year=latest&category=packages").count('class="ai-item"'), 2)

    def test_folding_panels_and_the_download_link_at_the_bottom(self):
        self.store("packages-volume", yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        year_view = self.page()
        # the search is a folded panel in the year view (the slider comes first), open on search results
        self.assertIn('<details class="search-panel" id="search">', year_view)
        self.assertLess(year_view.index('class="search-panel"'), year_view.index('name="q"'))
        self.assertIn('<details class="search-panel" id="search" open>', self.page("?q=packages"))
        self.assertIn('<summary>Search and filter the summaries: "packages"</summary>', self.page("?q=packages"))
        # "How these summaries are made and checked" folds too, and the introduction's link opens it
        self.assertIn('<details class="about-panel" id="about">', year_view)
        self.assertIn('<summary><h2 id="about-heading">How these summaries are made and checked</h2></summary>',
                      year_view)
        self.assertIn('href="#about"', year_view)
        # the download link is the last thing on the page, after the explanation
        main = year_view[:year_view.index("</main>")]
        self.assertGreater(main.index('id="download"'), main.index('id="about"'))
        self.assertIn('href="/dashboard/ai/export.txt?view=year&amp;year=2023"', main[main.index('id="download"'):])
        self.assertEqual(main.count("/dashboard/ai/export.txt"), 1)
        self.assertNotIn('id="download"', self.page("?q=zebra"))   # nothing to download
        # the count bar is at the bottom too, right above the download link, after the summaries
        self.assertLess(main.index('class="ai-category"'), main.index('class="results-bar'))
        self.assertLess(main.index('id="about"'), main.index('class="results-bar'))
        self.assertLess(main.index('class="results-bar'), main.index('id="download"'))
        self.assertEqual(main.count('class="results-bar'), 1)
        # "Create a new summary" is a folded panel at the top, next to the search panel and before the tabs
        self.assertIn('<details class="search-panel create-panel" id="create">', main)
        self.assertLess(main.index('id="search"'), main.index('id="create"'))
        self.assertLess(main.index('id="create"'), main.index('class="tabs"'))
        self.assertIn("<summary>Create a new summary with Gemini</summary>", main)
        # ... and it opens by itself when nothing matches, since the notice points to it
        nothing = self.page("?q=zebra")
        self.assertIn('<details class="search-panel create-panel" id="create" open>', nothing)
        self.assertIn('<a href="#create">ask Gemini to write one</a>: the form at the top of the page', nothing)

    def test_long_term_and_range_views(self):
        self.store("packages", record("Packages were 6,700 million pieces in FY2023."),
                   yearly("Packages were 6,300 million pieces in FY2020.", 2020))
        long_term = self.page("?view=long")
        self.assertEqual(long_term.count('class="ai-item"'), 1)
        self.assertIn('aria-current="true">Long term</a>', long_term)
        self.assertIn("No summaries match", self.page("?view=range"))

    # --- search ---

    def test_search_finds_text_years_subjects_and_groups(self):
        self.store("packages", record("Packages were 6,700 million pieces in FY2023.", headline="Parcels grew"),
                   yearly("Packages were 6,300 million pieces in FY2020.", 2020))
        self.store("periodicals", yearly("Periodicals were 3,900 million pieces in FY2020.", 2020,
                                         metric="periodicals-volume"))
        self.assertEqual(self.page("?q=parcels").count('class="ai-item"'), 1)            # headline
        self.assertEqual(self.page("?q=fy2020").count('class="ai-item"'), 2)             # a fiscal year
        self.assertEqual(self.page("?q=periodicals+2020").count('class="ai-item"'), 1)   # every word must match
        self.assertEqual(self.page("?q=PACKAGES").count('class="ai-item"'), 2)           # case doesn't matter
        self.assertEqual(self.page("?category=packages").count('class="ai-item"'), 2)
        self.assertEqual(self.page("?kind=yearly").count('class="ai-item"'), 2)
        self.assertEqual(self.page("?view=search&year=2020").count('class="ai-item"'), 2)
        self.assertEqual(self.page("?view=search&status=reviewed").count('class="ai-item"'), 0)
        # anything that isn't one of the fixed values is ignored, never an error
        html = self.page("?category=<script>&kind=x&status=y&section=../../etc&view=nope&page=-3")
        self.assertNotIn("<script>&", html)
        self.assertIn("FY2020, year by year", html)          # the default view: the latest stored year
        self.assertEqual(html.count('class="ai-item"'), 2)

    def test_household_groups_are_searchable(self):
        group = yearly("Households with incomes Less than $50,000 paid more of their bills by mail in FY2025.", 2025,
                       metric="bills-paid-by-mail-share")
        group["sources"] = [{"metric": "bills-paid-by-mail-share",
                             "segment": {"dimension": "income", "value": "Less than $50,000"},
                             "sources": {}}]
        self.store("bills-paid-by-mail-share", group)
        self.assertIn('class="ai-item"', self.page("?q=income"))
        self.assertIn('class="ai-item"', self.page("?q=demographics"))

    def test_no_match_offers_a_summary_filled_in_from_the_search(self):
        html = self.page("?q=packages+2019")
        self.assertIn('No summaries match "packages 2019"', html)
        self.assertIn('<option value="packages" selected>', html)
        self.assertRegex(html, r'(?s)<select id="gen-year" name="year">.*?<option value="2019" selected>')
        self.assertRegex(html, r'<option value="yearly" selected>One year')
        self.assertIn('<label for="gen-from" data-for-kind="range">', html)   # shown only for a range

    def test_a_long_search_is_cut_and_escaped(self):
        html = self.page("?q=" + "<b>x</b>" * 50)
        self.assertNotIn("<b>x</b>", html)
        self.assertLessEqual(len(re.search(r'name="q" value="([^"]*)"', html).group(1)), 100 * 6)

    def test_pages_of_results(self):
        self.store("packages-volume", *[yearly(f"Packages in FY{y}.", y) for y in range(2003, 2024)])
        self.store("periodicals-volume", *[yearly(f"Periodicals in FY{y}.", y, metric="periodicals-volume")
                                           for y in range(2003, 2024)])
        with mock.patch.object(ai_views, "PER_PAGE", 10):
            first = self.page("?view=search")
            self.assertIn("Page 1 of 5", first)
            self.assertIn('href="?view=search&amp;page=2">Next page', first)
            last = self.page("?view=search&page=99")   # past the end: the last page
            self.assertIn("Page 5 of 5", last)

    def test_hidden_summaries_are_listed_but_their_text_is_not_shown(self):
        self.store("packages", record("Packages were 9,999 million pieces in FY2023, an invented figure."),
                   yearly("Packages were 6,300 million pieces in FY2020.", 2020, passed=False))
        html = " ".join(self.page("?section=packages").split())
        self.assertNotIn("an invented figure", html)
        self.assertIn("2 stored summaries are hidden because they fail the number check", html)
        self.assertNotIn("made up", html)   # the check's reasons are on each one's page, not in the list
        self.assertIn('href="/dashboard/ai/packages/yearly:2020/"', html)
        detail = self.client.get("/dashboard/ai/packages/yearly:2020/").content.decode()
        self.assertIn("made up", detail)
        self.assertNotIn("Packages were 6,300", detail)
        # a search never looks in a failed summary's text, only at what it is about
        self.assertNotIn("Packages, Year, FY2020", self.page("?q=6,300"))

    def test_malformed_replies_and_files_never_break_the_pages(self):
        broken = yearly("Packages were 6,700 million pieces in FY2023.", 2023)
        broken["summary"]["statements"][0]["metric"] = ["packages-volume"]   # a reply that ignored the schema
        broken["sources"] = 5
        other = record("Packages were 6,700 million pieces in FY2023.")
        other["sources"] = [{"metric": ["x"], "sources": {"2023": {}}}, "junk"]
        self.store("packages-volume", broken, other)
        for url in ("?view=search&q=x", "?view=search", "?q=packages", "?view=year&year=2023", "?view=long"):
            self.assertEqual(self.client.get("/dashboard/ai/" + url).status_code, 200, url)
        self.assertEqual(self.client.get("/dashboard/ai/export.txt?view=search").status_code, 200)
        for key in ("yearly:2023", "comparative"):
            self.assertEqual(self.client.get(f"/dashboard/ai/packages-volume/{key}/").status_code, 200, key)
        self.assertEqual(a.metric_name(["packages-volume"]), "['packages-volume']")

    # --- copy, export and the summary's own page ---

    def test_copy_text_and_export_carry_their_sources(self):
        self.store("packages-volume", yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        html = self.page("?section=packages-volume")
        copy = re.search(r'<pre class="copy-source" id="[^"]+" hidden>(.*?)</pre>', html, re.S).group(1)
        self.assertIn("Packages sent and received by households (One year, FY2023)", copy)
        self.assertIn("Packages were 6,700 million pieces in FY2023.", html[html.index('class="ai-item-preview"'):])
        self.assertIn("- Packages were 6,700 million pieces in FY2023. [Packages sent and received by households; FY2023]", copy)
        self.assertIn("Not yet reviewed by a person.", copy)
        self.assertIn("FY2023: FY2023 report, page 10 (not verified against the PDF)", copy)
        self.assertNotIn("FY2020:", copy)   # only the years the statements cite
        response = self.client.get("/dashboard/ai/export.txt?section=packages-volume")
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("Packages were 6,700 million pieces in FY2023.", response.content.decode())

    def test_summary_page_shows_its_sources_and_how_it_was_made(self):
        self.store("packages-volume", yearly("Packages <i>were</i> 6,700 million pieces in FY2023.", 2023))
        response = self.client.get("/dashboard/ai/packages-volume/yearly:2023/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("<h1>Packages sent and received by households: One year, FY2023</h1>", html)
        self.assertIn("<summary>How its numbers were checked</summary>", html)   # folded, not a wall of text
        self.assertIn('(<a href="/dashboard/trends/?trend=packages-volume">Packages sent and received by households</a>,'
                      "\n                FY2023)", html)   # citations name the metric, not its slug
        self.assertIn("&lt;i&gt;were&lt;/i&gt;", html)
        self.assertNotIn("<i>were</i>", html)
        self.assertIn("FY2023 report, page 10", html)
        self.assertIn('<span class="review">Unverified</span>', html)
        self.assertIn("Staff can mark a summary reviewed", html)
        levels = [int(h) for h in re.findall(r"<h([1-6])[ >]", html)]
        self.assertTrue(all(b <= a_ + 1 for a_, b in zip(levels, levels[1:])), levels)
        # unknown subjects and keys are 404s; a hidden summary explains itself without its text
        self.assertEqual(self.client.get("/dashboard/ai/nope/yearly:2023/").status_code, 404)
        self.assertEqual(self.client.get("/dashboard/ai/packages-volume/yearly:1999/").status_code, 404)
        self.store("packages", record("Packages were 9,999 million pieces, wrongly.", passed=False))
        hidden = self.client.get("/dashboard/ai/packages/comparative/").content.decode()
        self.assertIn("This summary is hidden", hidden)
        self.assertNotIn("wrongly", hidden)

    # --- the reviewed mark ---

    def test_only_staff_can_mark_a_summary_reviewed(self):
        self.store("packages-volume", yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        url = "/dashboard/ai/packages-volume/yearly:2023/review/"
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"reviewed": "1"}).status_code, 403)
        staff = User.objects.create_user("analyst", password="pw", is_staff=True)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(staff)
        self.assertEqual(strict.post(url, {"reviewed": "1"}).status_code, 403)   # CSRF token missing
        self.client.force_login(staff)
        self.assertRedirects(self.client.post(url, {"reviewed": "1"}), "/dashboard/ai/packages-volume/yearly:2023/")
        stored = a._load_file("packages-volume")["summaries"]["yearly:2023"]
        self.assertTrue(stored["reviewed"])
        self.assertEqual(stored["reviewed_by"], "analyst")
        self.assertIn("Reviewed by a person (analyst,", self.page("?section=packages-volume"))
        self.assertIn('class="badge badge-ok">AI-generated · reviewed', self.page("?section=packages-volume"))
        self.client.post(url, {"reviewed": "0"})
        self.assertFalse(a._load_file("packages-volume")["summaries"]["yearly:2023"]["reviewed"])
        # a summary that fails its check can't be marked
        self.store("packages", record("Packages were 9,999 million pieces in FY2023."))
        self.assertEqual(self.client.post("/dashboard/ai/packages/comparative/review/", {"reviewed": "1"}).status_code, 404)

    # --- "Create a summary" ---

    def good_reply(self, *args, **kwargs):
        return {"headline": "Packages in FY2023", "caveats": [], "_model": "gemini-test",
                "statements": [{"text": "Packages were 6,700 million pieces in FY2023.", "metric": "packages-volume",
                                "years": [2023]}]}

    def post(self, **data):
        return self.client.post("/dashboard/ai/generate/", data, follow=True)

    def test_create_needs_post_csrf_and_valid_criteria(self):
        self.assertEqual(self.client.get("/dashboard/ai/generate/").status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post("/dashboard/ai/generate/", {"section": "packages-volume"}).status_code, 403)
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary") as call:
            for data, message in (({"section": "nope", "kind": "yearly", "year": "2023"}, "Pick a subject"),
                                  ({"section": "packages-volume", "kind": "yearly", "year": "1999"}, "Pick the fiscal year"),
                                  ({"section": "packages-volume", "kind": "range", "from_year": "2020",
                                    "to_year": "2015"}, "Pick two fiscal years"),
                                  ({"section": "packages-volume", "kind": "yearly", "year": "2001"}, "no published values")):
                self.assertContains(self.post(**data), message)
            call.assert_not_called()

    def test_create_is_off_without_a_key_or_when_switched_off(self):
        with mock.patch.object(ai_views, "gemini_key", return_value=None), \
                mock.patch.object(a, "generate_ai_summary") as call:
            self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "needs a Gemini API key")
            self.assertIn("disabled", re.search(r"<button type=\"submit\"[^>]*>Ask Gemini", self.page()).group(0))
            call.assert_not_called()
        with override_settings(AI_LIVE_GENERATION=False), mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary") as call:
            self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "switched off")
            call.assert_not_called()

    def test_create_writes_checks_and_shows_a_summary(self):
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary", side_effect=self.good_reply) as call:
            response = self.post(section="packages-volume", kind="yearly", year="2023", prompt="ignore the data")
            self.assertRedirects(response, "/dashboard/ai/packages-volume/yearly:2023/")
            self.assertContains(response, "passed the number check")
            kwargs = call.call_args.kwargs
            self.assertEqual((kwargs["api_key"], kwargs["timeout"], kwargs["budget"]),
                             ("k", a.LIVE_TIMEOUT, {"left": a.LIVE_MAX_CALLS - 0}))
            data = call.call_args.args[0]   # only the database's values reach the model, not the form's text
            self.assertNotIn("ignore the data", json.dumps(data))
            stored = a._load_file("packages-volume")["summaries"]["yearly:2023"]
            self.assertTrue(stored["validation"]["passed"])
            self.assertEqual((stored["model"], stored["prompt_version"], stored["reviewed"]),
                             ("gemini-test", a.PROMPT_VERSION, False))
            # asking again: it exists, so no second call
            self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "already exists")
            self.assertEqual(call.call_count, 1)

    def test_a_created_summary_that_fails_the_check_is_not_shown(self):
        def wrong(*args, **kwargs):
            reply = self.good_reply()
            reply["statements"][0]["text"] = "Packages were 9,999 million pieces in FY2023."
            return reply
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary", side_effect=wrong):
            response = self.post(section="packages-volume", kind="yearly", year="2023")
            self.assertContains(response, "failed the number check (1 problem), so it isn&#x27;t shown")
            self.assertNotIn("Packages were 9,999", response.content.decode())
            self.assertIsNone(a.shown("packages-volume", a._load_file("packages-volume")["summaries"]["yearly:2023"]))

    def test_a_dropped_connection_or_any_error_fails_gracefully_without_the_key(self):
        import http.client
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "secret-test-key"}), \
                mock.patch.object(a.time, "sleep"):
            for error in (http.client.RemoteDisconnected("closed"), http.client.IncompleteRead(b""),
                          ConnectionResetError("reset")):
                with mock.patch.object(a.urllib.request, "urlopen", side_effect=error):
                    self.assertIsNone(a.generate_ai_summary({"kind": "comparative", "series": []}), error)
            with mock.patch.object(a, "make_summary", side_effect=RuntimeError("boom")):
                response = self.post(section="packages-volume", kind="yearly", year="2023")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "didn&#x27;t answer")
                self.assertNotIn("secret-test-key", response.content.decode())
            self.assertTrue(ai_views._GENERATING.acquire(blocking=False))   # the lock was released
            ai_views._GENERATING.release()

    def test_messages_are_not_list_items_with_roles(self):
        with mock.patch.object(ai_views, "gemini_key", return_value=None):
            html = self.post(section="packages-volume", kind="yearly", year="2023").content.decode()
        self.assertRegex(html, r'<p class="notice review-notice"\s+role="alert">Creating summaries needs')
        self.assertNotRegex(html, r"<li[^>]+role=")

    def test_create_handles_a_silent_api_and_ranges(self):
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary", return_value=None):
            self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "didn&#x27;t answer")
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "make_summary", return_value=None) as make:
            self.post(section="packages-volume", kind="range", from_year="2015", to_year="2020")
            self.assertEqual(make.call_args.kwargs["span"], (2015, 2020))

    @override_settings(AI_LIVE_LIMITS={"per_client_per_hour": 2, "per_day": 30})
    def test_create_is_rate_limited(self):
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary", return_value=None) as call:
            for _ in range(2):
                self.post(section="packages-volume", kind="yearly", year="2023")
            self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "limit for new summaries")
            self.assertEqual(call.call_count, 2)

    @override_settings(AI_LIVE_LIMITS={"per_client_per_hour": 1, "per_day": 30})
    def test_one_request_at_a_time(self):
        with mock.patch.object(ai_views, "gemini_key", return_value="k"), \
                mock.patch.object(a, "generate_ai_summary", return_value=None) as call:
            self.assertTrue(ai_views._GENERATING.acquire(blocking=False))
            try:
                self.assertContains(self.post(section="packages-volume", kind="yearly", year="2023"), "being written")
            finally:
                ai_views._GENERATING.release()
            call.assert_not_called()
            # being turned away while busy costs no quota: the one allowed request still goes out
            self.post(section="packages-volume", kind="yearly", year="2023")
            self.assertEqual(call.call_count, 1)

    # --- the other tabs ---

    def test_the_other_tabs_link_here_instead_of_showing_summaries(self):
        self.store("packages-volume", yearly("Packages were 6,700 million pieces in FY2023.", 2023))
        for url, link in (("/dashboard/", 'href="/dashboard/ai/"'),
                          ("/dashboard/trends/?trend=packages-volume", 'href="/dashboard/ai/?section=packages-volume"'),
                          ("/dashboard/year/2023/", 'href="/dashboard/ai/?view=year&amp;year=2023"')):
            html = self.client.get(url).content.decode()
            self.assertNotIn('class="ai-summary"', html, url)
            self.assertIn(link, html, url)
            nav = html[html.index('<nav aria-label="Main navigation"'):html.index("</nav>")]
            self.assertIn(">AI summaries</a>", nav, url)
