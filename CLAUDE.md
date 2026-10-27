# ChallengeX: USPS Household Mail Dashboard (CYSE 130, Group 2)

## Goal (from `docs/USPS Analysing Mail Usage Through an Interactive Dashboard.pptx.pdf`)
GMU Challenge X use case: **"Postal Insights: Analyzing US Mail Usage Through an Interactive Dashboard."**

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
- **Getting to "15+ years".** The extracted reports cover 10 years. Two ways to get further back:
  - **Appendix A trend tables** (A8-x before FY2024, A-x from FY2024) already reach back to 2010.
    Some go back to 2000.
  - Extract headline tables from the `docs/` PDFs for 2000–2015.

  Use both, starting with the Appendix A tables.
- **How comparison years work:**
  - Up to FY2023, reports compare against the 2 prior years.
  - From FY2024, reports compare against the years 5 and 10 earlier (2014/2019/2024 and
    2015/2020/2025).

## Known data-quality problems (verify before trusting a number)
- **2021 is 88% OCR (112 of 128 tables) and its values are wrong.**
  - Example: `2021-p009-1` gives 395.1 billion First-Class pieces received. The real figure is
    about 32 billion.
  - Treat every `ocr=True` table as unverified.
- **Appendix gaps:**
  - **FY2019 has no Appendix A tables at all.** The extraction skipped pp. 68–85.
  - FY2018 is missing A8-10.
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
- **Restatements.** Later reports sometimes revise values for earlier years. Keep every value
  with its source report, and mark one as preferred.

## Current code state (as of commit f8ddfd6)
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
`source_id + row label + column` to metric and year. Start with these headline series:
- Total mail received and sent (E.1)
- Mail by market (E.2 / 1.x)
- Bill-payment and bill-receipt mail shares
- Ad reading and response rates
- Periodicals by type
- Packages received and sent

A smaller set of correct series is worth more than full coverage. Hand-check every 2021 and OCR
value against the PDF in `docs/`.

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
1. **Cleanup pass in `load_tables`:**
   - Drop a first data row that repeats the header.
   - Skip or flag the back-matter tables beyond page 110.
   - Add a `needs_review` flag, set for OCR tables, tables with no title, and tables with
     `col_N` headers.
2. **Fill the data gaps:**
   - Fix the 2021 values by re-extracting or entering them by hand from `docs/2021.pdf`.
   - Extract the missing FY2019 Appendix A tables and FY2018 A8-10.
3. **Build `Metric`/`Segment`/`Observation`** and the mapping-driven loader. Start with about 10
   headline series, sourced from Appendix A where possible.
4. **Unit normalization and methodology-break metadata:** per week → per year, billions ↔ per
   household, and age-band mapping.
5. **Extend history to 15+ years:** pull headline series for 2000–2015 from the `docs/` PDFs or
   the Appendix A back-years.
6. **Overview, Trends, and Year pages** with Chart.js, filterable by product and demographic.
7. **Forecast module** (`statsmodels`), with backtests and confidence bands.
8. **Claude-generated summaries**, cached and shown next to the charts, plus export.
9. **Tests** for unit conversion, the loader mapping, and the forecast functions.
