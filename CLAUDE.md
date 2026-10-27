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
- Django 6.1, SQLite (`db.sqlite3` is committed), Python 3.15. The project is `mysite/` and the
  app is `dashboard/`.
- Hosting is local only. `SECRET_KEY` is hard-coded in `mysite/settings.py` and `DEBUG=True`,
  which is fine because nothing is deployed. Never commit API keys. Put them in `.env`, which
  `python-dotenv` reads.
- Run the server: `python manage.py runserver`, then open `/dashboard/tables/`.
- Reload data: `python manage.py load_tables tables.json`. This **wipes** every Table and Row
  first.
- The team decided against ModelForms. Don't add them.

## Source material
- **`docs/`** (git-ignored, local only, about 200 MB; each teammate keeps their own copy):
  - The original report PDFs for **2000, 2001, 2003–2010, and 2012–2025**. 2002 and 2011 are
    missing.
  - The assignment slides.
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
- **2021 is 88% OCR (112 of 128 tables) and its values are wrong.**
  - Example: `2021-p009-1` gives 395.1 billion First-Class pieces received. The real figure is
    about 32 billion.
  - Treat every `ocr=True` table as unverified. 2021 is the only year with OCR.
  - The impact is limited: the 2021 values also appear in the non-OCR FY2022, FY2023, and FY2024
    appendices. Prefer those.
- **Appendix gaps:**
  - FY2019 has no Appendix A tables at all. The extraction skipped pp. 68–85.
  - FY2018 is missing A8-10.
  - Both gaps are covered by later reports' appendices, so they're low priority.
- **Appendix layout: values sit one column to the left of their year header.**
  - Example: in `2023-p077-1`, the label "2010" is at index 2, but the value `4,855` is at index
    1.
  - Many A8 tables alternate value and blank columns.
  - The first data row holds the years, and `columns[0]` holds the real title.
  - Map cells explicitly in the loader. Never zip the header row with the values.
- **Back-matter noise.** There are 49 tables beyond page 110, in 2016, 2017, and 2021. They are
  mostly 2-column questionnaire or tabulation fragments. Exclude them from metrics.
- **Titles:**
  - 706 tables have an empty title.
  - Many others hold a scrap of body text instead of the caption (for example "presents these
    data in two other forms,").
- **Table numbers are unreliable:**
  - 127 are blank, and some are wrong. `2021-p010-1` is labeled "Table E.2" but contains E.3.
  - The same number means different things in different years. "Table 1.1" in 2023 is not
    "Table 1.1" in 2024. **Never join across years on `table_number`.**
- **Headers:** 740 tables have blank column headers, which load as `col_N`. 174 repeat the header
  as their first data row.
- **Unit changes (the biggest trap for trend lines):**
  - Up to FY2023, reports mostly use **billions of pieces** or **pieces per household per week**.
  - FY2024 and later use **pieces per household per year**.
  - Per year = per week × 52. Total = per household × households (about 123–135 million).
- **Methodology breaks.** Annotate these on charts; don't smooth over them:
  - The contractor changed from NuStats to RCF in FY2024.
  - FY2025 brought a new survey design, though the old survey still covered Q1 of that year.
  - "Large MSA" was redefined in Jan 2025, from the top 30 metros to metros of 1 million or more.
  - Age bands changed. Before FY2025 they were 18–34 / 35–54 / 55+; from FY2025 they are
    Under 45 / 45–64 / 65+.
- **Restatements.** Later reports revise values for earlier years, sometimes by a lot.
  - Example: 2020 Personal correspondence received is 2,345M in the FY2020 report but 2,894M in
    the FY2023 report.
  - Keep every value with its source report.
  - Prefer the most recent non-OCR report, unless a methodology break makes it incomparable.

## Current code state (branch `test_titles`)
- **`dashboard/models.py`**: `Table` (metadata plus a `columns` JSON field) and `Row` (`label`,
  plus `data = {col: {"raw": str, "num": float|None}}`). This is a raw staging layer and can't
  be queried across years.
- **`views.py`:**
  - `table_list` searches by title, ID, or number and filters by year.
  - `table_detail` renders one table.
  - `dashboard` is a "Hello world" placeholder.
- **Templates:** `table_list.html` has no styling or `<html>` wrapper. `table_detail.html` is
  styled.
- **`admin.py`:** `Table` (filter by year/OCR, rows inline) and `Row` are registered for data
  review at `/admin/`. Run `python manage.py createsuperuser` to log in.
- **Missing:** tests, charts, and any AI.
- **Repo hygiene:** `.gitignore` excludes `__pycache__/`, `.env`, `.DS_Store`, and all of
  `docs/`, including the slides. The team decided to keep it out of git.

## Target design (recommended)

### 1. Database: add a clean "metric" layer on top of the raw tables
Keep `Table`/`Row` as the raw, auditable source, and add three models:
- **`Metric`** is one tracked series.
  - Fields: `slug`, `name`, `market`, `direction`, `unit`, `description`.
  - `market` is the postal product: correspondence, transactions, advertising, periodicals,
    packages, or total.
  - `direction` is received, sent, or total.
  - `unit` is canonical: pieces per household per year, billions, or percent.
- **`Segment`** is the demographic dimension, and the slides require it.
  - `dimension`: all, age, income, education, tenure, MSA, or household size.
  - `value`: for example "65+" or "$100K+".
  - Includes a note mapping old age bands to new ones.
- **`Observation`** is one data point.
  - Fields: `metric`, `segment`, `fiscal_year`, `value` (normalized), `raw_value`, `raw_unit`,
    `source_table` (FK to `Table`), `report_year`, `is_preferred`, `verified`, `notes`.
  - Unique on (metric, segment, fiscal_year, report_year).

Populate it with a curated mapping: a management command plus a YAML or Python mapping from
`source_id + row label + column index` to metric and year. Use the column index, not the
header, because of the appendix offset. Start with these headline series:
- Total mail received and sent (E.1)
- Mail by market (E.2 / 1.x)
- Bill-payment and bill-receipt mail shares
- Ad reading and response rates
- Periodicals by type
- Packages received and sent

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

### 3. AI: use two different tools
- **Forecasting is statistical, not an LLM.** Each series has roughly 10–25 yearly points, so use
  simple, explainable models:
  - Linear or log-linear trend
  - Holt's exponential smoothing (`statsmodels`)
  - CAGR extrapolation

  Show a confidence band and a backtest error. Never let an LLM invent forecast numbers.
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

1. **Metric layer for a few series.**
   - Add the `Metric`/`Segment`/`Observation` models and the mapping-driven loader.
   - Map 3–5 headline series from the non-OCR Appendix A tables, covering 2000–2025 (see
     "Source material"):
     - Total First-Class Mail received
     - Mail by market
     - Packages received
   - Handle the column offset, the unit normalization, and the methodology-break metadata for
     these series now. A trend line is wrong without them.
   - Spot-check against the PDFs.
2. **Trends page.**
   - A Chart.js line chart from a JSON view.
   - Methodology breaks annotated, source links, units, and a data-table fallback.
3. **Forecasts.**
   - Naive baseline vs. linear and Holt (`statsmodels`).
   - Backtest error and a prediction band on the Trends chart.
4. **AI summaries.**
   - Claude-generated, grounded in the observations and the forecast output.
   - A number-check against the database, cached in `Insight`, labeled as AI-generated.
   - *This is the end-to-end demo.*
5. **Broaden.**
   - More series, plus demographic `Segment`s (a slide requirement). Map old age bands to new
     ones.
   - An Overview page with KPI cards and the AI summary.
   - A Year page, and CSV export.
6. **Table browser and raw-data cleanup.** In `load_tables`:
   - Drop repeated header rows.
   - Skip the back-matter tables beyond page 110.
   - Add a `needs_review` flag, plus a badge, and market and OCR filters in the browser.
7. **Data repairs, as needed.** Only if a mapped series needs them:
   - The 2021 OCR values.
   - The FY2019 appendix and FY2018 A8-10.
   - Older PDFs.
8. **Polish and hardening.**
   - Accessibility pass (WCAG 2.1 AA).
   - `pip-audit`.
   - "Ask the data" box (optional).
   - Demo script.
