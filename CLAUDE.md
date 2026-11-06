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
  1. `python manage.py load_tables tables.json tables_2000_2015.json`. Both files are needed:
     metrics use some FY2005–FY2015 tables. This updates tables in place by `source_id` (table IDs
     and URLs stay stable), rebuilds their rows, and applies the corrected titles and numbers from
     `table_titles.json`. It replaces only the report years in the files it's given, so
     `load_tables tables.json` alone keeps the older tables. It refuses to remove a table that
     observations still cite (`Observation.source_table` is `PROTECT`); `rebuild_db` instead
     loads with `--keep-cited --complete`, re-maps the observations, then removes every table no
     longer in either file (`prune_stale`), so a renumbered table never blocks a rebuild.
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
  - `python manage.py extract_old_reports` regenerates `tables_2000_2015.json` from the FY2003-FY2015
    PDFs (about 8 minutes; needs `docs/` and PyMuPDF). `rebuild_db` loads it with `tables.json` and
    stops if either is missing. The output is committed.
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
- **`tables_2000_2015.json`** holds 1,933 tables and 22,639 rows from the **FY2003–FY2015** reports
  (FY2003, 2005–2010, 2012–2015), extracted by `manage.py extract_old_reports`, in the same format
  plus two check fields:
  - Each table is a ruled grid found by PyMuPDF under a "Table X" caption (title, units, years
    and data source come from the caption lines). It is re-read independently by
    `pdftables.py` (`check`: "two readers agree" when every number matches in order), and its
    numbers are looked up in the page text read by pypdf (`text_check`).
  - 1,423 tables pass all three checks; 450 have only one reader; 82 miss some numbers in the
    pypdf text (often spacing quirks like "201 4"). `load_tables` flags both kinds as
    needs-review. Spot-checked tables matched their pages; one-reader tables can have headings
    shifted by a merged cell.
  - Not extracted: **FY2000 and FY2001** are scanned page images with a hidden, error-filled OCR
    text layer ("Periodicol", "Moil") and no table lines; **FY2004** is fully scanned. FY2002 and
    FY2011 are missing. The key 2000-2002 series are already in the FY2020 appendix.
  - **FY2003 numbers its chapters differently** (5 = transactions, 8 = packages, 9 = methodology);
    `display.REPORT_CHAPTERS` maps it. FY2005-FY2025 share one layout (checked by keyword vote).
  - Metrics use Table E.2 (FY2005–FY2015) and the household-group tables (see below). They have no corrected titles
    (`table_titles.json`) or "From the report" excerpts.
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
  - Year tables (the `load_metrics` rule): a row with exactly one value per year column (plus any
    "% change" columns) has its k-th value placed under the k-th year, wherever the extraction
    put it. Other rows (a missing year, a second part's own heading) follow where the aligned
    rows' values went, column by column. Skipped when other named columns sit among the years
    (years heading "Sent / Received" groups). This fixed two-part tables such as `2025-p009-1`,
    whose repeated year row had made values show one year off.
  - Staggered values (Appendix A tables such as `2016-p084-1`): some rows sit one column left or
    right of their year, in an unnamed spacer column. When no row fills both, they move under
    the year, but only when just one neighbour qualifies. Long single-cell note lines become
    footnotes.
  - Column names wrapped onto a second line ("Under / 35", "35 to / 54") that the extraction
    made into an unlabelled first row.
  - Row labels in the second column with the first empty (FY2024/FY2025 tables such as
    `2024-p009-4`); otherwise "Magazines" showed under 2014 and every value one year late.
  - The label column's heading ("Sector") one column right, over an empty column.
  - A row label printed on two lines ("First-Class Ads / Share of Total Ads") that the
    extraction split into a row plus an empty row. The PDF re-read's labels decide which empty
    rows are second lines (`label_joins` in `table_context.json`), so section headings stay.

  With tidying and the PDF re-reads below, 105 of the 1,046 data tables still show a
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

## Current code state (`main`)
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
- **26 metrics are loaded (1,592 observations):**
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
    `household-mail-total`, `packages-volume`, `periodicals-volume` (2003–2023, from the FY2005–
    FY2023 reports; FY2021 is OCR and skipped). E.2 correspondence is deliberately not mapped:
    FY2017 reclassified it. Most overlapping years agree across reports (small revisions are
    listed in `VERIFICATION.md`). The documented changes are methodology breaks attached to the
    metrics they affect: packages include CD/DVD rentals from 2005 (FY2007 restated 2005 from
    2.4 to 3.1 billion); the carrier cost system double-counted Detached Address Labels before
    2007 (about +3 billion) and understated residential deliveries through 2007 (about −2 to −3
    billion), breaks at 2007 and 2008 that also cover the A8-12 advertising series; and FY2014
    restated 2012–2013 "due to weighing by Home Ownership" (total 130.4 → 136.9 billion for
    2012). Projections for the E.2 series therefore fit 2012–2023 only.
  - `BREAKS` entries can name `metrics`; without them a break applies to every metric.
  - Per household per year from FY2024/FY2025 E.2 (2014, 2015, 2019, 2020, 2024, 2025):
    `household-mail-per-household`, `correspondence-`, `transactions-`, `advertising-`,
    `packages-` and `periodicals-per-household`. FY2025 A-3/A-6 add the 16 household groups for
    correspondence and transactions (their all-households rows match E.2).
  - `ads-received-per-household`: FY2025 A-11, all households plus 16 groups. It counts
    First-Class and Marketing Mail ads only, so it is narrower than E.2's advertising market
    (643.6 vs. 658.9 in 2015) and is kept as its own metric.
  - **Household groups before FY2025** (633 values): `transactions-received-per-household`,
    `correspondence-received-per-household` (FY2003–FY2023) and
    `advertising-mail-received-per-household` (FY2005–FY2023), by age, income and education,
    from the one-year chapter tables "... Received by Income and Age" and "... by Income and
    Education" (Tables 3.2/3.4, 4.2/4.4, 5.4/5.5; "Ad Mail Received by ..." before FY2007;
    FY2003 numbers them differently). FY2003's advertising tables (6.3/6.4) count unaddressed
    mail, which later totals exclude, so they aren't used. Pieces per
    household per week ×52. `metric_sources.CrossTab` maps them and `dashboard/crosstab.py`
    reads them, for both `load_metrics` and `verify_pdfs`: income bands as rows, then the
    "Average"/"Total" row gives the age or education groups, the "Average" column the income
    bands and the corner all households, for the report's own year. It checks the column groups'
    order in the heading and refuses any other shape. The education tables repeat the age
    tables' margins: of 260, 254 agree, 2 differ only in print ("14" vs "14.0"), 4 by 0.1 (USPS
    rounding; the age table's value is used), and FY2015's correspondence Table 3.4 was never
    extracted, so its Table 3.2 supplies the margins and FY2015 has no age groups.
    - Segments use the reports' labels: age "Under 35 / 35 to 54 / Over 55" (the
      correspondence and advertising tables, and FY2003's, print "Under 34"), kept separate from FY2025's bands; income "Under $35K … Over $100K",
      nominal dollars, so the bands' make-up drifts with inflation; education shares FY2025's
      four segment names (the same categories).
    - **Each year comes from its own report, which later reports don't restate**, so every
      reclassification shows up as a break, on the metrics it moved: correspondence redefined
      at 2008 (FY2008 p. 27); the correspondence/transactions split at 2012, 2015 and 2017 (the
      reports restated earlier years in E.2, e.g. 2014 correspondence 11.0 → 13.7 billion);
      transactions at 2013 (the 2011 questionnaire, FY2013 pp. 38, 41); weighting by home
      ownership at 2014; and, for advertising, the carrier-system corrections at 2007 and 2008.
      Smaller restatements (FY2007's 2006 transactions +2.6%, FY2022's 2020 correspondence
      +2.7%) are about one rounding step of the weekly values and aren't breaks.
    - FY2017 Tables 4.2–4.4 cite the "HDS Recruitment Sample" (all other years: Diary Sample);
      the observations carry a note.
    - No projections yet: FY2021's tables are OCR, so the latest unbroken run is 2022–2023.
  - The loader skips "% change" columns after the years, only when the header names exactly that
    many of them.
- **All 1,592 loaded observations are verified** against their source PDF page by `verify_pdfs`
  (it compares the extracted cell, so converted values are checked too, and it handles "% change"
  columns and labels that wrap onto two lines, and reads only rows below the year header, since
  FY2005–FY2006 print Table E.1 with the same row labels above E.2). Household-group tables are
  read from their caption ("Table 5. 4:" too) to the next caption, through the same
  `crosstab_values()` as the loader. See `VERIFICATION.md`.
- **Every table has a corrected title and number.** See `dashboard/titles.py`, `table_titles.json`,
  and `manage.py extract_titles`.
- **Tests:** 156 in total, in `dashboard/tests.py`, `dashboard/test_ai_summary.py` (AI summary
  validation, storage and display), `dashboard/test_demographics.py` (household-group
  tables, their PDF reading and loaded values), `dashboard/test_trends.py` (the Trends page), `dashboard/test_accessibility.py` (lang, title, skip link, one main landmark and h1,
  heading order, labelled controls, chart band contrast), `dashboard/test_old_reports.py`
  (FY2003-FY2015 extraction helpers, loading two table files), `dashboard/test_browser.py`
  (sections incl. FY2003, review reasons, browser filters, survey forms
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
- **Templates:** `overview.html`, `trends.html`, `year.html`, `table_list.html` and
  `table_detail.html` are full pages. All include `_head.html` (after the `<meta>` tags) and
  `_nav.html` (skip link, logo, main navigation with a ☰ menu button below the `md` width), and
  wrap their content in one `<main id="main">`. `_ai_summary.html` renders one stored summary.
- **Styling (Tailwind, from 2026-11-04):** `_head.html` loads the Tailwind 4.1.11 browser build,
  pinned to the package's own `dist/index.global.js` with an SRI hash (not the bare URL, which
  jsDelivr minifies on the fly), and holds the whole design as `@apply` rules in a
  `<style type="text/tailwindcss">` block; templates use only those semantic class names
  (`.card`, `.notice`, `.badge` …). The browser compiles it on each load, so pages need the
  internet (as Chart.js does) and can flash unstyled for a moment. To upgrade: change the
  version, check the file against the npm package, and hash it
  (`openssl dgst -sha384 -binary index.global.js | openssl base64 -A`). Compiling the block once
  into a static CSS file with the Tailwind CLI would remove the CDN script entirely; that needs
  the standalone CLI binary (no Node here), so ask before downloading it. `base.css` is gone.
- **Accessibility (WCAG 2.1 AA), re-checked 2026-11-05 with the Tailwind styling:** axe-core
  4.10.2 in Chrome finds 0 violations of the WCAG 2.0/2.1 A and AA rules and 0 best-practice
  issues on all 13 page types checked (including household groups and AI summaries), after the
  styles have applied; links in text are underlined (colour alone failed link-in-text-block);
  every control is reachable by Tab with a visible focus ring (36 stops on Trends; white on the
  navy nav, where the page-wide navy ring measured 1.3:1); the ☰ menu
  opens and closes with Enter/Space and updates `aria-expanded`; the skip link is the
  first Tab stop; no page scrolls sideways at 320 px; the projection band has 4.5:1 edges and
  its values are also in a table. `dashboard/test_accessibility.py` guards the structure. To
  re-run the browser checks, use Playwright with the installed Chrome and inject axe-core
  (no Node needed).
- **Dependencies:** `python -m pip_audit -r requirements.txt -r requirements-dev.txt` reports no
  known vulnerabilities (pypdf moved to 6.21.4 for three CVEs; outputs re-checked unchanged).
- **`admin.py`:** all models are registered at `/admin/`. Run `python manage.py createsuperuser`
  to log in.
  - `Table` can be filtered by year and OCR status, with its rows inline.
  - On the Observation list, `verified` is editable, and the `notes` field explains each check.
- **AI summaries (`dashboard/ai_summary.py`, added 2026-11-05 by the team, using Google Gemini,
  `gemini-2.5-flash`):** `python -m dashboard.ai_summary` builds each section's data packet,
  asks Gemini for a headline, statements and caveats, checks the numbers and stores the result in
  `dashboard/ai_summaries/<section>.json` (model, prompt version, input hash, `reviewed`). Pages
  only read those files; the commented-out live-call code in the views stays off. Needs
  `GEMINI_API_KEY` in `.env` only to generate (see `.env.example`). A subagent review on
  2026-11-05 found the number check too loose and every stored summary stale; see To do A1.
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

- Household groups FY2003–FY2023 for transactions, correspondence and advertising received

**Still to map:**
- The same household-group tables for mail *sent*, periodicals and packages (also in every
  report; same `CrossTab` mapping).
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
  - **Pin an exact version and add an `integrity` (SRI) hash.** It's currently 4.5.1. The same
    rule applies to the Tailwind script in `_head.html` (4.1.11).
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
Updated 2026-11-03. Write tests with every change, keep `verify_pdfs` at 0 mismatches, have the
reviewer subagent check each branch before merging, and update this file when a step finishes.

### Done
1. **Metric layer:** 26 metrics, 1,592 observations, all verified against their PDF pages.
2. **Trends page:** chart, methodology breaks, values and sources table.
3. **Forecasts:** naive, drift, linear and Holt, chosen by backtest; 80%/95% bands (`forecast.py`).
4. **Broaden:** new series, FY2025 household groups, Overview, Year page, CSV export.
5. **Table browser:** titles, column repair, PDF re-reads, "From the report" excerpts, topics,
   needs-review flags, OCR filter, source PDF links.
6. **Data repairs:** checked; none needed for the current series.
7. **Polish:** WCAG 2.1 AA pass, `pip-audit` clean, `DEMO.md`.
8. **FY2003–FY2015 tables extracted** (`tables_2000_2015.json`, 1,933 tables; see Source material).
9. **Longer market series:** Table E.2 from FY2005–FY2015, so total, packages and periodicals
   run 2003–2023; restatements are methodology breaks.
10. **Household groups before FY2025:** transactions and correspondence received (FY2003–FY2023)
    and advertising received (FY2005–FY2023) by age, income and education, with every
    reclassification marked as a break (reviewed twice by a subagent).

### To do
Measured against the slides' required capabilities and the quality bar above.

**A. Required by the challenge, not built yet**
1. **AI-generated summaries** of yearly and long-term changes (slide requirement 3). Built by
   the team with Gemini on 2026-11-05 (see Current code state); being hardened after a review
   (number check tied to cited metric and years, direction and percentage-point checks,
   break-crossing changes, staleness). The original design notes follow. Covers the Overview's
   AI summary card and plain-language "what changed and why" text an analyst can copy into a
   report with its citations.
   - Design: an `Insight` model; a `generate_insights` command run offline (pages never call the
     API); Claude sees only one series' values, sources, precomputed changes, projection and
     methodology notes; structured JSON output where every statement cites its fiscal years.
   - Safeguards (Generative AI quality bar): an automated check that every number in the text
     matches the input (failures are stored but never shown); an "AI-generated, not yet
     reviewed" label until a person ticks `reviewed` in the admin; model ID, prompt version and
     input hash stored; a small eval set of known facts; `--max-calls` cost cap and `--dry-run`.
   - Needs `ANTHROPIC_API_KEY` in `.env` (git-ignored) and the `anthropic` package pinned in
     `requirements.txt`. Then the optional "Ask the data" box, with its input treated as
     untrusted.
2. **Copy into a report.** CSV export exists (Year and Trends pages), but there is no copy
   button on charts, numbers or summaries. The OIG goal is halving report-prep time: add a copy
   button for a chart's values with their sources, and later for summaries.

**B. Data**
3. **FY2021 household-group tables** are OCR'd and wrong. Transcribe its six tables (3.2, 3.4,
   4.2, 4.4, 5.4, 5.5; about 130 numbers) from the page images, checked by eye. This closes the
   2021 gap. Advertising groups would then have 2014–2023 (10 years) for projections;
   correspondence and transactions only 2017–2023 (7) after the 2017 reclassification, so their
   projections would fit from 2015 and be flagged as crossing it. Decide first whether to show
   those flagged projections, fit 7 years, or show none.
4. **More household-group series:** mail sent, periodicals and packages by income and
   age/education are in the same reports; add them with `crosstabs(...)`, and compare each
   market's own-year values with later reports' Table E.2 first, as for correspondence.
5. **Package and periodical detail** from chapters 6 and 7 isn't mapped.
6. **FY2015 correspondence by age:** Table 3.4 (p. 30) was never extracted, so FY2015 has no
   correspondence age groups. Fix `extract_old_reports` for that page, or add the table by hand
   from the pypdf text (it has a text layer).
7. **The older tables (FY2003–FY2015):**
   - Titles and excerpts: run them through `extract_titles` (corrected titles and numbers) and
     `extract_context` ("From the report" quotes). Both currently read only `tables.json`.
   - Review the 672 flagged ones. Most are "one reader" (the values are there but headings can
     be shifted by merged cells). Improving `extract_old_reports` for merged header cells would
     clear many of them; check a sample by eye first.
   - About 408 tables still show some "Column N" headers (105 from FY2016–FY2025, 303 from the
     older reports).

**C. Forecasts and UI**
8. **Projections for household groups**, after item 3.
9. **One projection per line** on the "by category" chart.
10. ~~Re-run the accessibility checks~~ (done 2026-11-05 after the Tailwind styling: 0
    violations). Re-run them after any styling change. Optional: compile Tailwind to a static CSS
    file (see Styling) so the demo doesn't need the CDN for styles.

**D. Before the demo** (whoever presents)
11. Follow the checklist in `DEMO.md` on the demo laptop: `pip install -r requirements.txt`,
    `python manage.py rebuild_db` (expect 1592 match, 0 mismatch), tests pass, PDFs in `docs/`,
    internet for the Chart.js CDN. Update the walk-through to show a household-group chart
    (e.g. transactions received by age, with its breaks), then rehearse the 7 minutes once.
12. Re-run `python -m pip_audit -r requirements.txt -r requirements-dev.txt`.

**E. Low priority**
13. **Data gaps:** FY2000, FY2001 and FY2004 are scanned; extracting them needs OCR, and every
    value would have to be checked by eye. Their key series are already in the FY2020 appendix
    (from 2000). FY2002 and FY2011 PDFs are missing from `docs/`; request them from USPS if
    needed. The FY2019 appendix is images and FY2018 lacks A8-10; only repair these if a mapped
    series needs them (none does now).
14. **Upkeep:** Chart.js (4.5.1) and Tailwind (4.1.11) are pinned with SRI hashes; to upgrade,
    change both the URL and the hash. Re-run `pip-audit` after any dependency change.
15. **Only if the dashboard is ever deployed:** set `DEBUG=False`, read `SECRET_KEY` from the
    environment, set `ALLOWED_HOSTS`, serve over HTTPS, and put authentication in front of the
    admin (see the Security quality bar).
