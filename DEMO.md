# Demo script: Postal Insights dashboard (about 7 minutes)

For whoever presents to the USPS / OIG judges. Every number below is a published value checked
against its source PDF page, so it's safe to say out loud.

## Before the demo (10 minutes, the day before)

1. `git pull`, then `pip install -r requirements.txt` and `python manage.py rebuild_db`.
   It should end with **1604 match, 0 mismatch** (that line needs the PDFs in `docs/`).
2. `python manage.py test dashboard`: all tests pass.
3. Put the report PDFs in `docs/` so the "Open the report at page N" links work.
4. `python manage.py runserver`, open `http://127.0.0.1:8000/`, and click through every stop below
   once. The charts load Chart.js from a CDN, so check the venue's internet. Without it, each chart
   says it couldn't load and the data table underneath still has every value.
5. Zoom the browser to 125% so the room can read it.

## The story in one line

USPS publishes an 80-page report a year; we turned 10 years of them (and the trend appendices
reaching back to 2000) into a dashboard where every number is one click from its source page, with
honest projections.

## Walk-through

| Time | Where | What to show and say | Challenge requirement |
|---|---|---|---|
| 0:00 | **Overview** (`/dashboard/`) | Six headline cards: all household mail is **637.3 pieces per household in FY2025, down 38.8% from FY2015**; bills paid by mail **14%, down 17 points** in ten years; packages **41.5 per household, up 29.3%**. Point at "Source: FY2025 report, page 7 — verified against the PDF" on a card. | Annual results, long-term change, easy navigation |
| 1:00 | Overview, market table | Advertising is about 61% of household mail. Note the honest caveat under the table: USPS's market figures don't add up to its own total, and we say so instead of hiding it. | Visualizations by postal product |
| 1:30 | **Trends** → "First-Class Mail received by households" | 2000–2023 from the Appendix A tables. The dashed line marks the FY2010 methodology change. Hover a point: the tooltip names its report and page. | 15+ years; methodology transparency |
| 2:15 | Same chart, projection | Dashed projection with the shaded 80% band, labelled "statistical projection, not a published figure". Scroll to **Track record**: four models were tested on years they hadn't seen; drift won with **0.24× the naive model's error**. The forecast is chosen by evidence, not by preference. | Longitudinal trend forecasting |
| 3:15 | Trends → "Share of bills paid by mail" → household group "Age of householder: 65 and Over" | FY2025 by age: **22%** of bills paid by mail for 65+, against **6%** for under 45. Then switch the group back: the page flags that the FY2024 and FY2025 survey changes affect comparisons. | Demographics (required) |
| 4:00 | "Download these values as CSV" | Opens in Excel with the source report, page and verification for every value, and the projections marked. This is the OIG report-prep workflow. | Export for the "How Americans Use Mail" report |
| 4:30 | **By year** → FY2025 | Every published FY2025 value on one page, plus the breakdowns by age, income, education, homeownership and metro area. | Visualizations by year |
| 5:15 | **Browse tables** → Topic "Transactions", years 2021 | All 1,095 extracted tables are searchable. Point at the **Needs review** and **OCR** badges: FY2021's chapters were scanned images, and we flag them rather than trust them. | Database design, data quality |
| 5:45 | Open FY2021 Table 4.1 (search `2021-p035-1`) | The "Check this table against the PDF" box explains why it's flagged. **From the report** quotes the report's own sentence about the table, transcribed from the scanned page. "Open the FY2021 report at page 35" jumps to the source. | Provenance |
| 6:30 | Close | 26 series, 1,604 values, every one matched to its PDF page; keyboard- and screen-reader-accessible (WCAG 2.1 AA checks pass). Next: AI-written summaries grounded in these numbers. | |

## Likely questions

- **"Where's the AI?"** The forecasting is the analytical layer: four statistical models compete on a
  backtest, and the winner and its error are shown. AI-written summaries were designed (grounded only
  in our data, every number checked against the database, labelled and human-reviewed) but deferred
  by the team; they're next on the roadmap.
- **"How do you know the numbers are right?"** `verify_pdfs` re-reads every loaded value from the text of
  its source PDF page: 1,604 of 1,604 match. `VERIFICATION.md` has the cross-report checks.
- **"Reports disagree with each other. Which do you use?"** The most recent non-OCR report that gives
  the value (later reports restate earlier years). Every point shows which report it came from.
- **"Why do some series have gaps?"** USPS only published those figures for some years (per-household
  values exist for 2014, 2015, 2019, 2020, 2024 and 2025). Gaps are shown, never filled in.
- **"Why no projection for the age groups?"** They have three data points each; we require eight
  consecutive years before projecting anything.
- **"What about years before 2016?"** The Appendix A tables already reach back to 2000. Extracting the
  older reports themselves is planned.

## If something goes wrong

- **Chart doesn't appear:** no internet for the Chart.js CDN. Use the values table under the chart.
- **PDF link says the file isn't there:** `docs/` is missing on this computer; the page still names the report and page.
- **Empty pages:** the database wasn't built; run `python manage.py rebuild_db` (a few seconds).
