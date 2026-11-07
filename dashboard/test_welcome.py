"""The welcome page (the USPS logo's link): what the site is, how to get around, and its counts."""
import re
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Table
from .testdata import load_real_tables


def nav_of(page):
    return page[page.index('<nav aria-label="Main navigation"'):page.index("</nav>")]


class WelcomePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def page(self):
        response = self.client.get(reverse("welcome"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_it_introduces_the_site(self):
        page = self.page()
        self.assertIn("<title>Welcome to the Household Mail Dashboard</title>", page)
        self.assertIn("How America uses its mail, FY2000 to FY2025", page)
        self.assertIn("What this site is", page)
        self.assertIn("Household Diary Study every year since 1987", page)
        self.assertIn("Built for", page)
        self.assertIn("How to read the numbers", page)

    def test_removed_text_and_decoration_stay_removed(self):
        page = self.page()
        self.assertNotIn("USPS Household Diary Study &middot; Household Mail Survey", page)  # the old eyebrow
        self.assertNotIn("A student project built by Team C3", page)                         # the old footer
        self.assertNotIn("<footer", page)
        reading = page[page.index('aria-labelledby="reading-title"'):page.index("</main>")]
        self.assertNotIn("<svg", reading)                                                    # no checkmarks
        self.assertNotIn("check-icon", page)

    def test_only_find_your_way_around_has_cards_and_icons(self):
        page = self.page()
        tour = page[page.index('<ul class="tour">'):page.index("</ul>", page.index('<ul class="tour">'))]
        self.assertEqual(tour.count('<li class="tour-card">'), 6)
        self.assertEqual(tour.count('<svg aria-hidden="true" focusable="false"'), 6)   # icons are decoration
        self.assertEqual(tour.count('class="tour-try"'), 6)
        main = page[page.index('<main id="main">'):page.index("</main>")]
        self.assertEqual(main.count("<svg"), 6)                                        # none elsewhere

    def test_common_tasks_are_a_numbered_list(self):
        page = self.page()
        tasks = page[page.index('<ol class="tasks">'):page.index("</ol>")]
        self.assertEqual(tasks.count("<li>"), 4)
        self.assertIn("<h3>Put figures into a report</h3>", tasks)
        self.assertIn('<span class="task-number" aria-hidden="true">1</span>', tasks)  # the list numbers it too

    def test_the_site_font_is_arial_and_nothing_is_heavier_than_bold(self):
        page = self.page()
        self.assertIn("--font-sans: Arial, Helvetica, sans-serif;", page)
        self.assertNotIn("font-extrabold", page)
        self.assertNotIn("font-black", page)

    def test_it_links_to_every_section_of_the_site(self):
        page = self.page()
        main = page[page.index('<main id="main">'):page.index("</main>")]
        self.assertIn("Find your way around", main)
        for name in ("dashboard", "trends", "ai-summaries", "table-list", "settings"):
            self.assertIn(f'href="{reverse(name)}"', main, name)
        self.assertIn(f'href="{reverse("year-detail", args=[2025])}"', main)  # the latest year

    def test_the_table_count_comes_from_the_loaded_data(self):
        tables = Table.objects.exclude(section="survey_form").count()
        self.assertIn(f"Search all {tables:,} tables taken from the", self.page())

    def test_the_banner_photo_is_local_and_under_a_navy_layer(self):
        from django.contrib.staticfiles import finders
        page = self.page()
        self.assertIn("/static/dashboard/welcome-mailbox.jpg", page)   # served by the site, not a CDN
        self.assertNotIn("images.unsplash.com", page)
        self.assertIsNotNone(finders.find("dashboard/welcome-mailbox.jpg"))
        # the overlay behind the text is at least 0.9 opaque USPS navy (#004b87), wide or narrow
        self.assertIn("linear-gradient(rgb(0 75 135 / 0.9), rgb(0 75 135 / 0.9))", page)
        self.assertIn("rgb(0 75 135 / 0.95) 0%, rgb(0 75 135 / 0.9) 58%", page)

    def test_the_banner_has_no_row_of_figures(self):
        page = self.page()
        banner = page[page.index('<section class="hero"'):page.index("</section>")]
        for text in ("fiscal years of data", "annual reports", "tables extracted from them",
                     "each checked against its PDF page", "<dl", "<dd"):
            self.assertNotIn(text, banner, text)
        self.assertNotIn("hero-facts", page)

    def test_the_logo_leads_here_from_every_page(self):
        for url in (reverse("dashboard"), reverse("trends"), reverse("ai-summaries"),
                    reverse("table-list"), reverse("settings"), reverse("welcome")):
            nav = nav_of(self.client.get(url).content.decode())
            self.assertRegex(nav, rf'<a href="{re.escape(reverse("welcome"))}" class="brand"', url)
            self.assertIn('alt="Household Mail home: the welcome page"', nav, url)

    def test_on_this_page_the_logo_is_the_current_link(self):
        nav = nav_of(self.page())
        self.assertRegex(nav, r'class="brand" aria-current="page"')
        self.assertEqual(nav.count('aria-current="page"'), 1)   # not the Overview tab too

    def test_overview_tab_still_opens_the_overview(self):
        nav = nav_of(self.page())
        self.assertIn(f'<a href="{reverse("dashboard")}">Overview</a>', nav)


class EmptyDatabaseWelcomeTests(TestCase):
    def test_it_works_before_the_data_is_loaded(self):
        page = self.client.get(reverse("welcome")).content.decode()
        self.assertIn("Find your way around", page)
        self.assertNotIn('class="hero-facts"', page)          # no counts to show
        self.assertIn(f'href="{reverse("year-pick")}"', page)  # "By year" without a latest year
