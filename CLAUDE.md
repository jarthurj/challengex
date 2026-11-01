# ChallengeX: USPS Household Mail Dashboard (Group 2)

This is an **outside challenge set by USPS** through George Mason University's Challenge X
program, not a course assignment. The client is USPS and its Office of Inspector General (OIG).

## Goal (from `docs/USPS Analysing Mail Usage Through an Interactive Dashboard.pptx.pdf`)
Challenge X use case: **"Postal Insights: Analyzing US Mail Usage Through an Interactive Dashboard."**

**Problem.** USPS has run the Household Diary Study every year since 1987. It was renamed the
Household Mail Survey (HMS) in FY2025. Each report runs about 80 pages and is heavy on charts,
so key data is hard to find and long-term trends are hard to spot. The findings are purely
descriptive and offer no strategic direction.

**Challenge.** Turn these clunky reports into a state-of-the-art dashboard that shows both
**annual results** and **long-term trends**. Use **AI** to analyze multi-year market data and
produce **automated trend summaries** and **predictive forecasts**.
The stated goal is "Unlock the hidden value of these annual reports."

**Required capabilities (the slides' "Proposed Solution" and "Example Output" pages):**
1. **Ingest 15+ years** of HDS/HMS results.
2. **Clear visualizations by year, postal product, and user demographics.** Demographics are a
   requirement, not an extra.
3. **Generated summaries** of yearly and long-term changes in mail and package usage.
4. **Longitudinal trend forecasting** of future household behavior.
5. A seamless, easy-to-navigate experience.

**Who it's for and how success is measured:**
- **USPS OIG (internal).** Cut the preparation time for the OIG report *"How Americans Use Mail"*
  by 50%.
- **USPS OIG and global postal partners (external).** A tool to track, segment, and analyze US
  mail trends.
- Our inference: users should be able to copy or export charts, numbers, and summaries straight
  into a report.

**The three problems the team is solving:**
1. **Database design.** Turn messy extracted PDF tables into data you can query across years.
2. **UI and data presentation.** Lookup, yearly view, trend charts by product and demographic,
   and AI insights.
3. **AI integration.** Which AI to use for summaries and forecasts, and how to wire it in.

## What kind of project this is
This is an end-to-end **analytics data product**, sometimes called "augmented analytics." It has
four parts:
- A **document-extraction ETL pipeline** that turns PDFs into structured tables.
- A **dimensional data model**: `Observation` is the fact table; `Metric`, `Segment`, and year
  are the dimensions.
- A **BI dashboard**.
- **Time-series forecasting** plus **LLM-generated narrative insights**.

The client is a federal agency and its oversight office (USPS OIG), so public-sector
accessibility and security norms apply.

**Our inference: the challenge will be judged on a live demo.** Build a thin end-to-end slice
first (data → chart → forecast → AI summary for a few metrics), then broaden it. That beats a
perfect database with no dashboard on demo day.

## Quality bar (acceptance criteria)
These are standard industry practice for this kind of product. They are not in the slides, but
the team holds the work to them, and a feature isn't done until it meets the ones that apply.

**User stories.** The primary persona is an OIG analyst writing "How Americans Use Mail." That
analyst should be able to:
- Find any headline number for any year within a few clicks, along with its source report and
  page.
- Compare one metric across years and demographic segments on a single chart.
- Read a plain-language summary of what changed and why, and copy it into a report with its
  citations.
- See each forecast with its uncertainty and the model's track record.
- A partner postal analyst should be able to filter by product and demographic and export the
  result to CSV.

**Data:**
- **Provenance.** Every number shown traces back to `source_table`, report year, and page, and
  the UI links to it.
- **Quality dimensions:**
  - Accuracy: the `verified` flag, plus a visible badge on unverified values.
  - Completeness: show gaps; never silently interpolate.
  - Consistency: canonical units.
  - Uniqueness: one preferred value per metric, segment, and year.
- **Reproducible, idempotent loads.** Rebuilding from `tables.json` plus the mapping always
  produces the same database.
- **Data dictionary.** Every `Metric` has a definition, a unit, a market, and its source tables.

**Dashboard and UX:**
- Every chart has a title, units, a source, the report year, and methodology-break annotations.
- **Accessibility: WCAG 2.1 AA, as Section 508 requires for a federal audience.**
  - Never use color as the only way to encode information.
  - Every chart has a data-table fallback or text alternative.
  - The whole dashboard works by keyboard.
  - Text meets contrast requirements.
- Pages load in about 2 seconds or less. No external API calls happen during a page load.
- Number formatting is consistent: thousands separators, fixed decimals per unit, and units
  always shown.

**Forecasting:**
- Compare every model against a naive baseline: the last value, or drift.
- Report backtest error (MAE or MAPE) on held-out years.
- Show prediction intervals and label forecasts as projections.
- Keep horizons at 5 years or less.
- Flag any series that crosses a methodology break, or fit only on the years after the break.
- Explain the model and its assumptions in the UI.

**Generative AI.** Follow the NIST AI RMF and the OWASP Top 10 for LLM Applications:
- **Grounding:**
  - The LLM sees only our observations, forecasts, and methodology notes.
  - Every claim cites a metric and year.
  - An automated check confirms that every number in the generated text matches the database.
- Label AI-generated text, and require a human "reviewed" flag before it's treated as final.
- Keep prompt templates versioned in code. Store the model ID, prompt version, and a hash of the
  inputs with each `Insight`.
- Keep a small eval set of known metrics and expected facts, and check summaries against it for
  numeric errors and hallucinations.
- **Prompt injection.** Treat "Ask the data" input as untrusted. The LLM has no write tools, and
  its output is escaped when rendered.

**Security** (a federal client, plus an LLM that takes free-text input):
- **OWASP Top 10:**
  - Keep Django's autoescaping on. Never apply `|safe` to LLM or extracted text.
  - Keep CSRF protection on.
  - Use the ORM only; no raw SQL built from user input.
  - Validate every query parameter.
- Secrets live only in `.env` and are never logged or committed.
- Pin dependencies in `requirements.txt` and scan them with `pip-audit`.
- Cap the LLM's cost and rate, with a timeout, and fail gracefully when the API is unavailable.
- Before any deployment:
  - Set `DEBUG=False`.
  - Read `SECRET_KEY` from the environment.
  - Set `ALLOWED_HOSTS`.
  - Serve over HTTPS.
  - Put authentication in front of the admin.

**Engineering:**
- Write tests (`python manage.py test`) alongside each feature, not at the end. Cover the unit
  conversions, the loader mapping, the forecasts, and the AI-text number check.
- Keep changes small and focused, merged to `main` with a clear description.
- Update this file when a team decision changes.

## Stack and how to run
- Django 6.1, SQLite, Python 3.15. The project is `mysite/` and the app is `dashboard/`.
- **`db.sqlite3` is not in git.** It's git-ignored, and each person builds their own copy.
  - Everything in it is generated from files in git: `tables.json`, `table_titles.json`, and
    `dashboard/metric_sources.py`.
  - The rebuilt database is identical to the one that used to be committed.
  - First-time setup, or after a pull that changes the data:
    `pip install -r requirements.txt` then `python manage.py rebuild_db`.
  - `rebuild_db` runs `migrate`, `load_tables`, `load_metrics`, and `verify_pdfs` (the last only
    if `pypdf` and the PDFs in `docs/` are present). It takes a few seconds.
  - It's safe to re-run: admin accounts and reviewers' flags and notes are kept.
  - Admin accounts (`createsuperuser`) and notes typed into the admin exist only in your local
    database.
- Hosting is local only. `SECRET_KEY` is hard-coded in `mysite/settings.py` and `DEBUG=True`,
  which is fine because nothing is deployed. Never commit API keys. Put them in `.env`, which
  `python-dotenv` reads.
- Run the server: `python manage.py runserver`, then open `http://127.0.0.1:8000/` (it goes to
  the Overview at `/dashboard/`).
- The individual steps that `rebuild_db` runs, in order. Every step is safe to re-run, and
  reviewers' `verified` flags and notes survive:
  1. `python manage.py load_tables tables.json`. This updates tables in place by `source_id`
     (table IDs and URLs stay stable), rebuilds their rows, and applies the corrected titles and
     numbers from `table_titles.json`.
  2. `python manage.py load_metrics`. This rebuilds the metric layer from
     `dashboard/metric_sources.py`, including the fixed `REVIEW_NOTES`.
  3. `python manage.py verify_pdfs` checks every loaded value against the text of its source
     PDF page, then sets `verified` and adds a `[pdf-check]` note. It needs the PDFs in `docs/`
     and `pypdf`. **Run it after mapping any new series.**
  - `python manage.py extract_titles` regenerates `table_titles.json` from the PDFs (about 30
    seconds). It's only needed if `tables.json` or `dashboard/titles.py` changes. The output is
    committed, so teammates without `docs/` still get the titles.
  - `python manage.py extract_context` regenerates `table_context.json` (about 25 seconds), which
    holds each table's "From the report" excerpts, units, and its layout re-read from the PDF page.
    It needs `docs/`, a loaded database, and PyMuPDF (`pip install -r requirements-dev.txt`;
    PyMuPDF is AGPL, so it isn't in `requirements.txt`). Rerun it after changing `tables.json`,
    `table_titles.json`, `context.py`, `pdftables.py`, or `fy2021_quotes.py`. The output is
    committed; the site only reads the JSON.
- Run the tests: `python manage.py test dashboard`. They load the real `tables.json`, and they
  don't need `docs/`.
- See `VERIFICATION.md` for the full check of the loaded data against every file in `docs/`.
- The team decided against ModelForms. Don't add them.

## Source material
- **`docs/`** (git-ignored, local only, about 200 MB; each teammate keeps their own copy):
  - The original report PDFs for **2000, 2001, 2003–2010, and 2012–2025**. 2002 and 2011 are
    missing.
  - The assignment slides.
  - **Text layers:**
    - Most PDFs have a real text layer, which `pypdf` reads exactly.
    - **FY2004 is fully scanned.**
    - In **FY2021**, the chapter pages (9–69) are scanned, but Appendix A has text.
    - In **FY2019**, the Appendix A tables are embedded as images.
    - Pages without text can only be checked by rendering them, for example with PyMuPDF.
  - `tables.xlsx - Index.pdf`, a printed index of `tables.json`.
  - `2025.docx` and `2025_Household_Mail_Survey_extracted.xlsx`, alternate extractions of
    FY2025.
- **`tables.json`** holds 1,095 tables and 9,559 rows from the **FY2016–FY2025** reports only.
  - Fields: `id` (`{year}-p{page}-{n}`), `year`, `page`, `table_number`, `title`,
    `source_file`, `ocr`, `columns`, and `rows` (a list of string lists; `rows[i][0]` is the
    label).
  - Tables per year: 2016: 139, 2017: 127, 2018: 114, 2019: 96, 2020: 114, 2021: 128,
    2022: 115, 2023: 115, 2024: 79, 2025: 68.
- **"15+ years" is already covered by the Appendix A trend tables** (A8-x before FY2024, A-x
  from FY2024). None of them are OCR'd:
  - The FY2020 report's A8 tables cover **2000–2020**. For example, `2020-p072-1` is A8-1,
    First-Class Mail received by type, in millions of pieces.
  - The FY2022 and FY2023 reports' A8 tables cover 2010–2022 and 2010–2023.
  - FY2024 A-x covers 2014–2024, per household per year. FY2025 A-x has only 2015, 2020, and
    2025.

  So the full history is **2000–2025**, entirely from non-OCR tables. Use Appendix A as the
  primary trend source. Use the E.x and 1.x tables to check it and to add series the appendix
  lacks. Extract from the older `docs/` PDFs only to verify values or fill a specific missing
  series.
- **How comparison years work:**
  - Up to FY2023, reports compare against the 2 prior years.
  - From FY2024, reports compare against the years 5 and 10 earlier (2014/2019/2024 and
    2015/2020/2025).

## Known data-quality problems (verify before trusting a number)
- **The FY2021 chapter tables are OCR'd from scanned pages, and their values are wrong**
  (112 of 128 FY2021 tables).
  - Example: `2021-p009-1` gives 395.1 billion First-Class pieces received. The real figure is
    about 32 billion.
  - Treat every `ocr=True` table as unverified. 2021 is the only year with OCR.
  - **The 16 FY2021 Appendix A tables (`2021-p072-1` … `2021-p087-1`) are not OCR.** They are
    `ocr=False`, and all 3,572 of their numbers match the PDF text exactly, so they're usable as
    sources.
  - The 2021 values also appear in the FY2022, FY2023, and FY2024 appendices.
- **Appendix gaps:**
  - FY2019's Appendix A tables (pp. 69–85) are images in the PDF, which is why the extraction
    skipped them.
  - FY2018 is missing A8-10.
  - Both gaps are covered by later reports' appendices, so they're low priority.
- **The correspondence/transactions split was reclassified several times.** The total stays the
  same, but the split moves between categories.
  - Reports in FY2007–2010, FY2012–2014, FY2015–2016, FY2017–2018, and FY2019 each split
    2000–2010 differently. For example, 2000 correspondence is 16,304M in FY2014, 18,311M in
    FY2015, and 19,470M from FY2017 on.
  - The loaded preferred values come from FY2020 (2000–2009) and FY2023 (2010+). Both use the
    current classification, and they agree where they overlap.
  - **Never combine split values from different reports in one series without checking this.**
- **Small inconsistencies in USPS's own tables.**
  - In the FY2020 report's A8-1, the parts for 2007 and 2008 add up to 9M and 7M more than the
    printed total. Correspondence is about 8M higher than in FY2017/2018.
  - The values are kept as published, and the affected observations carry a note.
- **Appendix layouts differ between reports. Never match values to years by column position.**
  - FY2020 A8 tables are aligned.
  - FY2022 and FY2023 alternate value and blank columns, and each value sits one column to the
    left of its year label. In `2023-p077-1`, "2010" is at index 2, but `4,855` is at index 1.
  - The years row is often the first data row, and `columns[0]` holds the real title.
  - `load_metrics` handles all of this by reading the years in order from the header line, then
    the non-empty values in order. It refuses to load if the two counts differ.
  - Rows can repeat a label. A8-1 has two "Total" rows (correspondence, then transactions), so
    the mapping uses `nth`.
- **Back-matter noise.** There are 49 "tables" from Appendix C, the survey instruments (cover
  letter, diary instructions, blank answer sheets), in 2016, 2017, and 2021. They're titled as
  survey forms. Exclude them from metrics.
- **Titles and table numbers in `tables.json` are unreliable. Use the corrected ones.**
  - Originally, 706 titles were empty, and many others were scraps of body text ("presents these
    data in two other forms,").
  - Numbers were sometimes taken from prose, such as "Table 1.6 presents…". In `2016-p050-2`, the
    extraction said "Table 5.6" but the table is really 5.5.
  - `dashboard/titles.py` recovers the real caption and number for all 1,095 tables, stored in
    `table_titles.json` with the method used for each and the original values. 234 numbers were
    corrected.
  - It matches by content: rows whose label and exact numbers appear once on the page vote for
    the caption above them. Titles come from each report's List of Tables, or from the page
    caption (FY2022 has no list).
  - Scanned and chart pages were read from page images; see `FROM_PAGE_IMAGES` and `MANUAL` in
    `titles.py`.
  - Some "tables" are chart data, titled "Figure x.y". Their extracted values are often OCR noise.
  - Even corrected, the same number means different things in different years. "Table 1.1" in
    2023 is not "Table 1.1" in 2024. **Never join across years on `table_number`.**
- **Column names are often wrong in the raw extraction.** 732 tables were affected; blank names
  load as `col_N`. `dashboard/tidy.py` repairs them **for display only**, and the stored data
  is unchanged. The patterns it handles:
  - Names one column to the right of their values, with empty spacer columns. A group heading
    such as "Educational Attainment of Head of Household" can take a slot; it becomes a heading
    row instead.
  - The real header in the first data row, such as the years in Appendix A tables, where
    `columns[0]` is the caption.
  - Repeated header rows.
  - A name one column to the left of its values.
  - "Source:"/"Note:" lines extracted as rows; these become footnotes.
  - A single value column with no name in the report, which gets named from the title's units.
  - Staggered values (Appendix A tables such as `2016-p084-1`): some rows sit one column left or
    right of their year, in an unnamed spacer column. When no row fills both, they move under
    the year. Long single-cell note lines become footnotes.
  - The label column's heading ("Sector") one column right, over an empty column.
  - A row label printed on two lines ("First-Class Ads / Share of Total Ads") that the
    extraction split into a row plus an empty row. The PDF re-read's labels decide which empty
    rows are second lines (`label_joins` in `table_context.json`), so section headings stay.

  With tidying and the PDF re-reads below, 116 of the 1,046 data tables still show a
  "Column N" somewhere, mostly charts (`Figure x.y`) and FY2021 OCR tables. Every table page has
  a "Show the raw extraction" link (`?raw=1`).
- **Tables re-read from the PDF page (`dashboard/pdftables.py`).** For 76 tables the layout is
  rebuilt from word positions on the page: lost row labels (e.g. `2016-p011-1`), and group
  headings ("Educational Attainment of Head of Household") lost or put in a column's place
  (`2016-p037-1`). A re-read is used only if it fixes something tidy can't, every extracted number
  appears in it in order, it has the same row count, and no caption text, second header row or
  merged year heading leaked in; otherwise the tidied extraction is shown. Most
  rejected re-reads are two-part tables or wrapped headings. Still display-only.
- **"From the report" excerpts (`dashboard/context.py`).** 795 of 1,046 data tables have the
  report's own sentences about them, quoted verbatim with the PDF page. The other 251 are never
  cited in their report's text: 154 Appendix A trend tables, 71 Appendix B methodology tables,
  23 chapter tables, and 3 charts. FY2021's scanned pages have no text layer, so their sentences
  were transcribed by hand from the page images into `dashboard/fy2021_quotes.py` (49 pages, 115
  sentences); the page labels them as transcribed.
- **Unit changes (the biggest trap for trend lines):**
  - The A8 appendix tables (through FY2023) use **millions of pieces**.
  - Chapter tables up to FY2023 mostly use **billions of pieces** or **pieces per household per
    week**.
  - FY2024 and later use **pieces per household per year**. For example, FY2024 A-1 gives 348.2
    for 2014, where A8-1 gives 42,830M, which implies about 123M households.
  - Per year = per week × 52; this conversion is in `CONVERSIONS`.
  - **Millions ↔ per household is not converted.** The reports publish household counts only
    for 2014, 2015, 2019, 2020, 2024, and 2025, so these are kept as separate metrics in their
    own units. Converting them would need an outside annual series, such as Census households.
- **Methodology breaks.** Annotate these on charts; don't smooth over them:
  - The contractor changed from NuStats to RCF in FY2024.
  - FY2025 brought a new survey design, though the old survey still covered Q1 of that year.
  - "Large MSA" was redefined in Jan 2025, from the top 30 metros to metros of 1 million or more.
  - Age bands changed. Before FY2025 they were 18–34 / 35–54 / 55+; from FY2025 they are
    Under 45 / 45–64 / 65+.
- **Restatements.** Later reports revise values for earlier years, sometimes by a lot.
  - Example: 2020 Personal correspondence received is 2,345M in the FY2020 report but 2,894M in
    the FY2023 report.
  - Another example: total First-Class Mail received in 2020 is 35,345M in the FY2020 report and
    35,729M in the FY2023 report.
  - Keep every value with its source report.
  - Prefer the most recent non-OCR report. `mark_preferred` in `load_metrics` does this.
  - Because of that rule, a preferred series can switch source reports partway through. Bills
    paid by mail uses FY2023 for 2010–2013 (37% in 2013) but FY2024 for 2014 onward (33%;
    FY2023 said 34%). Charts must show each point's source report.

## Current code state (`main`, plus the `table-browser` branch awaiting review)
- **`dashboard/models.py`:**
  - **Raw layer:** `Table` (metadata plus a `columns` JSON field) and `Row` (`label`, plus
    `data = {col: {"raw": str, "num": float|None}}`). `load_tables` also sets each table's
    `section` (report chapter: E, 1-7, A, B, or Appendix C survey form; chapters mean the same
    topic in every report) and `needs_review` / `review_reason` (OCR values, chart data, or
    "Column N" headers in what the table page shows), via `dashboard/display.py`.
  - **Metric layer:** `Metric`, `Segment`, `Observation`, and `MethodologyBreak`. A break with
    no metrics attached applies to every metric.
- **`dashboard/metric_sources.py`** is the curated mapping that `load_metrics` reads:
  - `METRICS`
  - `SOURCES`: `source_id` → (the table's unit, `RowMap`s)
  - `CONVERSIONS`
  - `BREAKS`
- **23 metrics are loaded (869 observations):**
  - First-Class Mail received: `fcm-received-total`, `-correspondence`, `-transactions`,
    `-advertising` (millions, 2000–2023, A8-1) and `fcm-received-per-household` (2014–2024, A-1).
  - First-Class Mail sent: `fcm-sent-total`, `-correspondence`, `-transactions` (millions,
    2000–2023, A8-3) and `fcm-sent-per-household` (2014–2024, A-3).
  - Bill payment: `bills-paid-by-mail-share` (2000–2025, plus 16 FY2025 household groups) and
    `bills-paid-electronic-share` (2000–2024; A8-6 "Total Electronic" and FY2024 A-6 agree
    exactly for 2014–2023), in percent.
  - Advertising: `advertising-received-total` and `marketing-mail-ads-received` (millions,
    2000–2023, A8-12).
  - All markets from Table E.2, in millions converted from billions (one decimal, so ±50 million):
    `household-mail-total`, `packages-volume`, `periodicals-volume` (2014–2023; FY2021 is OCR
    and skipped). E.2 correspondence is deliberately not mapped: FY2017 reclassified it.
  - Per household per year from FY2024/FY2025 E.2 (2014, 2015, 2019, 2020, 2024, 2025):
    `household-mail-per-household`, `correspondence-`, `transactions-`, `advertising-`,
    `packages-` and `periodicals-per-household`. FY2025 A-3/A-6 add the 16 household groups for
    correspondence and transactions (their all-households rows match E.2).
  - `ads-received-per-household`: FY2025 A-11, all households plus 16 groups. It counts
    First-Class and Marketing Mail ads only, so it is narrower than E.2's advertising market
    (643.6 vs. 658.9 in 2015) and is kept as its own metric.
  - The loader skips "% change" columns after the years, only when the header names exactly that
    many of them.
- **All 869 loaded observations are verified** against their source PDF page by `verify_pdfs`
  (it compares the extracted cell, so converted values are checked too, and it handles "% change"
  columns and labels that wrap onto two lines). See `VERIFICATION.md`.
- **Every table has a corrected title and number.** See `dashboard/titles.py`, `table_titles.json`,
  and `manage.py extract_titles`.
- **Tests:** 113 in total, in `dashboard/tests.py`, `dashboard/test_trends.py` (the Trends
  page), `dashboard/test_browser.py` (sections, review reasons, browser filters, survey forms
  hidden, the table page's review notice and PDF link), `dashboard/test_overview.py` (Overview cards and market mix, Year page, CSV export
  and its formula-injection guard), `dashboard/test_forecast.py` (models, backtest, fit window and breaks, intervals, the
  projection on the Trends page), and `dashboard/test_context.py` (excerpt finding, the FY2021
  transcriptions, `table_context.json`, re-read checks, and the table page).
  `dashboard/tests.py` covers:
  - header parsing, preference, and conversions
  - the mapping, an end-to-end load against `tables.json`, and full reloads that keep review
    flags and notes
  - PDF-text parsing for `verify_pdfs`
  - title recovery
  - the admin pages
  - `rebuild_db` on an empty database and on an existing one
  - column-name tidying (`tidy.py`) and the table page in tidy and raw modes
  - the pinned, integrity-checked Chart.js script on the Trends page
- **`views.py`:**
  - `table_list` searches by title, ID, or number and filters by report years (checkboxes),
    topic, OCR and review status; Appendix C survey forms are hidden unless asked for. Each row
    shows text badges ("Needs review", "OCR"). Unexpected filter values are ignored.
  - `source_pdf` serves `docs/<year>.pdf` (git-ignored, so only where the PDFs are present);
    the table page links to `/dashboard/reports/<year>.pdf#page=N`, or names the page when the
    PDF isn't there.
  - `table_detail` renders one table through `display.display_table()`: the layout re-read
    from the PDF when `table_context.json` has one, otherwise tidied column names
    (`dashboard/tidy.py`). Plus the review notice with its reasons, the topic, the source PDF
    link, a "From the report" box and the caption's units. `?raw=1` shows the extraction as stored.
- **`trend_views.py` (Trends page, `/dashboard/trends/`):**
  - Pick a metric (or "First-Class Mail received by category") and a household segment.
  - The page draws a Chart.js line chart from `/dashboard/trends/data/` (JSON).
  - Methodology breaks are marked on the chart and listed.
  - A values-and-sources table shows each point's report, page, and verification status.
  - Mixed units are refused, and missing years show as gaps.
  - "Mail delays" is a placeholder with no data yet.
  - **Projections** (`dashboard/forecast.py`) for single-metric charts, 5 years ahead:
    - Naive, drift, linear and Holt models are each backtested by rolling origin (fit on the
      first k years, forecast the next 1–5, compare with what USPS published). The one with the
      lowest mean absolute error is used; the page shows every model's MAE, MAPE and ratio to
      naive. A flat series keeps the naive projection.
    - 80%/95% intervals come from the chosen model's backtest error at each horizon (they never
      narrow); percent values stay within 0–100.
    - The fit uses the trailing run of consecutive years, starting at the latest methodology break
      that still leaves 8 years (e.g. FY2010–FY2023 for First-Class totals). Breaks it can't avoid
      are flagged (bills paid by mail crosses FY2024 and FY2025).
    - Series with fewer than 8 consecutive years (the FY2025 demographic segments) and the
      category chart get no projection, with the reason shown.
    - Labelled as projections on the chart, in tooltips, and in a table with both intervals.
- **`overview_views.py`:**
  - **Overview** (`/dashboard/`; the site root redirects here): KPI cards for six headline
    series (`KPIS`) with the latest published value, the change vs. 5 and 10 years earlier
    (percent and absolute; percentage points for shares), and each value's source and
    verification. Below, the market mix per household for the latest year (FY2025 E.2); the
    published markets don't add up to the published total, so shares are of the markets shown,
    and the page says so.
  - **Year page** (`/dashboard/year/<FY>/`, picker at `/dashboard/year/?year=`): every preferred
    value for that fiscal year with its source, the household-group tables (FY2015/2020/2025),
    and a link to that report's tables.
  - **CSV export**: `/dashboard/year/<FY>/csv/` and `/dashboard/trends/csv/?trend=...` (the
    Trends selection: published values with source report, page, table and verification, then
    the projection rows labelled as projections with both intervals and the model). Text cells
    that a spreadsheet would run as formulas are quoted.
- **Templates:** `table_list.html` has no `<html>` wrapper. `table_detail.html`, `trends.html`,
  `overview.html` and `year.html` are full pages; the last three share `_nav.html`.
- **`admin.py`:** all models are registered at `/admin/`. Run `python manage.py createsuperuser`
  to log in.
  - `Table` can be filtered by year and OCR status, with its rows inline.
  - On the Observation list, `verified` is editable, and the `notes` field explains each check.
- **Missing:** any AI (step 4, deferred).
- **Repo hygiene:** `.gitignore` excludes `__pycache__/`, `.env`, `.DS_Store`, and all of
  `docs/`, including the slides. The team decided to keep it out of git.

## Target design (recommended)

### 1. Database: a clean "metric" layer on top of the raw tables (built)
Keep `Table`/`Row` as the raw, auditable source. The metric layer adds the models below:
- **`Metric`** is one tracked series.
  - Fields: `slug`, `name`, `market`, `direction`, `unit`, `description`.
  - `market` is the postal product: correspondence, transactions, advertising, periodicals,
    packages, or total.
  - `direction` is received, sent, or total.
  - `unit` is one of: `millions` (pieces), `per_household_year`, or `percent`.
- **`Segment`** is the demographic dimension, and the slides require it.
  - `dimension`: all, age, income, education, tenure, or MSA. Add household size when it's
    mapped.
  - `value` is the report's own label, for example "65 and Over".
  - Old and new age bands are different segments. Don't merge them. The FY2025 break explains
    the change.
- **`MethodologyBreak`** records a year, a title, a description, and the affected metrics (an
  empty list means all of them).
- **`Observation`** is one data point.
  - Fields: `metric`, `segment`, `fiscal_year`, `value` (normalized), `raw_value`, `raw_unit`,
    `source_table` (FK to `Table`), `report_year`, `is_preferred`, `verified`, `notes`.
  - Unique on (metric, segment, fiscal_year, report_year).

The layer is populated from `dashboard/metric_sources.py`, a mapping from `source_id + row label
(+ nth)` to metric (+ segment). Years are read from each table's own header.

**Done:**
- First-Class Mail received and sent, total and by market
- Bills paid by mail and electronically
- Advertising totals and Marketing Mail ads
- All markets, packages and periodicals (Table E.2), in volume and per household
- FY2025 household groups for bills, correspondence, transactions and ads received

**Still to map:**
- Demographic groups before FY2025 (chapter tables by income, age, education; old age bands
  are separate segments).
- Package and periodical detail from chapters 6 and 7.

A smaller set of correct series is worth more than full coverage. Spot-check the mapped values
against the PDFs in `docs/`, especially around restatements and methodology breaks.

### 2. UI
- **Overview:**
  - KPI cards for the latest year: total household mail, share by market, and mail-payment share.
  - Change versus 5 and 10 years earlier.
  - The AI summary.
- **Trends:**
  - Pick a metric (product) and a segment (demographic) to get a line chart across years.
  - Methodology breaks are marked, and there's a forecast band.
- **Year page:** that year's headline numbers, a breakdown by product and demographic, and the
  list of that year's tables.
- **Table browser:**
  - The existing search, improved with market and OCR filters.
  - A "needs review" badge, and a link to the source PDF page in `docs/`.
- **Export:** a CSV or copy button on charts and summaries, which supports the OIG report-prep
  goal.
- **Charts:** Chart.js from a CDN, rendered through Django templates, with data from small JSON
  views. No SPA framework unless the team decides otherwise.
  - **Pin an exact version and add an `integrity` (SRI) hash.** It's currently 4.5.1.
  - Avoid versions less than about two weeks old.
  - To upgrade, update both the URL and the hash.

### 3. AI: use two different tools
- **Forecasting is statistical, not an LLM.** Each series has roughly 10–25 yearly points, so use
  simple, explainable models:
  - Naive (last value) and drift baselines
  - Linear trend
  - Holt's exponential smoothing

  Show a confidence band and a backtest error. Never let an LLM invent forecast numbers.
  **Decision:** these are written in plain Python in `dashboard/forecast.py`, not `statsmodels`.
  Each model is a few lines, and statsmodels would add numpy, scipy, pandas and patsy (100+ MB) for
  series this short. Revisit if the team needs ARIMA-class models.
- **Summaries and explanations come from an LLM**, the Claude API through the `anthropic` SDK.
  - Send it only the structured observations, the forecast output, and the methodology notes.
  - Ask for trend summaries, year-over-year narratives, and "why it changed" explanations
    grounded in the data it was given.
  - This answers the slides' complaint that the reports "lack actionable insights."
- **Cache LLM output** in the database, for example in an `Insight` model keyed by metric,
  segment, and year. Pages must not call the API on every load. The key goes in `.env`.
- **Optional "Ask the data" box:** turn a question into a metric lookup, then have the LLM answer
  from the returned rows.

## Next steps (priority order)
The plan is to build one thin end-to-end slice first, then broaden it. Steps 1–4 produce a
demoable dashboard. Write tests with each step.

1. ~~**Metric layer for a few series.**~~ **Done and verified.** See "Current code state" and
   `VERIFICATION.md`.
2. ~~**Trends page.**~~ **Done** (from the `year-filter` branch). See `trend_views.py` under
   "Current code state."
3. ~~**Forecasts.**~~ **Done** (`dashboard/forecast.py`). Naive, drift, linear and Holt, chosen by
   rolling-origin backtest; 80%/95% intervals from backtest errors; shown on the Trends chart.
   - Possible follow-ups: forecasts for demographic segments once they have 8+ consecutive
     years, and per-line projections on the category chart.
4. **AI summaries. Deferred** (team decision, 2026-10-31): skipped for now; return to it later.
   - Claude-generated, grounded in the observations and the forecast output.
   - A number-check against the database, cached in `Insight`, labeled as AI-generated.
5. ~~**Broaden.**~~ **Done.**
   - ~~The series under "Still to map"~~ **done**: 23 metrics, 869 verified observations, FY2025
     household groups for four of them.
   - ~~An Overview page with KPI cards~~ **done** (the AI summary waits for step 4).
   - ~~A Year page, and CSV export~~ **done**.
   - Still open: demographic groups before FY2025, and package/periodical detail (see
     "Still to map").
6. ~~**Table browser and raw-data cleanup.**~~ **Done** on the `table-browser` branch (awaiting
   review): titles, numbers, column names, PDF re-reads and excerpts earlier; now survey forms
   hidden, `needs_review` flag and badge, topic and OCR filters, and source PDF links. 208 of
   the 1,046 data tables are flagged (111 OCR, 89 chart data, 116 with "Column N"; some have
   more than one reason).
7. **Data repairs, as needed.** Only if a mapped series needs them:
   - The FY2021 chapter tables. They are OCR'd from scanned pages; the appendix is fine.
   - The FY2019 appendix, which is images. Read it from rendered pages.
   - FY2018 A8-10.
   - Older PDFs. FY2004 is scanned.
8. **Polish and hardening.**
   - Accessibility pass (WCAG 2.1 AA).
   - `pip-audit`.
   - "Ask the data" box (optional).
   - Demo script.
