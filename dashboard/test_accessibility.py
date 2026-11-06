"""Page structure that WCAG 2.1 AA relies on, checked on every page type.

The full check (axe-core in a browser, keyboard walk-through, 320 px reflow) is described in
CLAUDE.md; these tests keep the structure from regressing without needing a browser.
"""
import re
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Table
from .testdata import load_real_tables


class PageStructureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_real_tables()
        call_command("load_metrics", stdout=StringIO())

    def pages(self):
        table = Table.objects.get(source_id="2016-p011-1")
        return {
            "overview": reverse("dashboard"),
            "trends": reverse("trends"),
            "year": reverse("year-detail", args=[2025]),
            "tables": reverse("table-list"),
            "table": reverse("table-detail", args=[table.pk]),
        }

    def test_every_page_has_language_title_skip_link_nav_and_one_main(self):
        for name, url in self.pages().items():
            page = self.client.get(url).content.decode()
            self.assertIn('<html lang="en">', page, name)
            self.assertRegex(page, r"<title>[^<]+</title>", name)
            self.assertIn('<a class="skip-link" href="#main">Skip to main content</a>', page, name)
            self.assertIn('<nav aria-label="Main navigation"', page, name)
            self.assertEqual(page.count('<main id="main">'), 1, name)
            self.assertEqual(page.count("<h1"), 1, name)
            # the shared styles (_head.html): Tailwind pinned with an integrity hash, like Chart.js
            self.assertIn("@tailwindcss/browser@4.1.11/dist/index.global.js", page, name)
            self.assertRegex(page, r'tailwindcss/browser[^>]*integrity="sha384-[^"]+"', name)

    def test_current_page_is_marked_in_the_navigation(self):
        for name, url in self.pages().items():
            if name == "table":
                continue
            page = self.client.get(url).content.decode()
            nav = page[page.index('<nav aria-label="Main navigation"'):page.index("</nav>")]
            self.assertEqual(nav.count('aria-current="page"'), 1, name)  # the CSS names it too

    def test_headings_do_not_skip_levels(self):
        for name, url in self.pages().items():
            page = self.client.get(url).content.decode()
            levels = [int(h) for h in re.findall(r"<h([1-6])[ >]", page)]
            for previous, current in zip(levels, levels[1:]):
                self.assertLessEqual(current, previous + 1, f"{name}: h{previous} then h{current}")

    def test_form_controls_have_labels(self):
        for name, url in self.pages().items():
            page = self.client.get(url).content.decode()
            for match in re.finditer(r"<(?:select|input)[^>]*>", page):
                control = match.group(0)
                if 'type="hidden"' in control:
                    continue
                control_id = re.search(r'id="([^"]+)"', control)
                if control_id and f'for="{control_id.group(1)}"' in page:
                    continue
                # Otherwise it must sit inside a <label> ... </label>.
                before = page[:match.start()]
                self.assertGreater(before.rfind("<label"), before.rfind("</label>"), f"{name}: {control}")

    def test_projection_band_edges_meet_graphics_contrast(self):
        datasets = self.client.get(reverse("trend-data")).json()["chart"]["datasets"]
        band = [d for d in datasets if d["label"].startswith("80%")]
        self.assertTrue(band)
        self.assertTrue(all(d["borderWidth"] >= 1 and d["borderColor"] == "#767676" for d in band))
