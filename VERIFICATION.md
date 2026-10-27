# Data verification: loaded metrics vs. the source reports

**Result: all 313 loaded values match their source PDF pages exactly, so none needed
correcting.** I also checked them against every other file in `docs/`. Where reports disagree, the
cause is a documented restatement or reclassification, or in two cases a small inconsistency in
USPS's own table, not an extraction error.

Checked 2026-10-27, against the six metrics in `dashboard/metric_sources.py`.

## Headline numbers

| Check | Result |
|---|---|
| Loaded values vs. the text of their own source page | **313 / 313 match** |
| Headline (all-households) preferred values also confirmed by a *different* report | 112 / 133 |
| FY2025 bills-by-mail values (incl. 16 demographic segments) vs. `2025.docx` | 51 / 51 match |
| Same, vs. `2025_Household_Mail_Survey_extracted.xlsx` | 51 / 51 match |
| Parts add up to totals within each source table | 4 of 5 tables in every year; FY2020 A8-1 is off by 7–9M in 2007 and 2008 (see Findings) |

The 21 headline values with no second report are expected:
- **Latest-year values** that only one report has published so far: First-Class Mail for 2023,
  bills by mail for 2024 and 2025.
- **The FY2024 per-household series.** No other report uses that unit.
- **Correspondence for 2005–2008.** See Findings.

Each of these has instead been checked against its own source page, internal totals, or the
report's executive summary.

## How it was checked

1. **Extracted the text of every PDF in `docs/`** with `pypdf`. This reads the PDF's own text
   layer, so the numbers are exact, with no OCR involved.
2. **Compared each loaded value with its source page.** For every value, I found the same row on
   the same page and compared each year. This step is now a command:
   `python manage.py verify_pdfs`. It sets `verified` on each observation and writes a
   `[pdf-check]` note saying where the value was matched.
3. **Pulled the same rows from every other report** (Appendix A8-1/A-1 and A8-6/A-6/A-9) to see
   where the reports agree and where values were restated.
4. **Rendered and read by eye the pages that have no text layer**, using PyMuPDF: the FY2019
   appendix (images) and FY2004 (fully scanned).
5. **Ran internal consistency checks.** Within each table, the categories should add up to the
   printed total, and the executive-summary figures should match the appendix.

## Every file in `docs/`

| File | Text layer | What was checked | Result |
|---|---|---|---|
| `2000.pdf` | yes | Prose: "Of the 57 billion pieces of First-class mail received by households in 2000" | Matches 56,805M |
| `2001.pdf` | yes | Prose: 10.5 and 11.1 pieces/household/week received in 2000 and 2001 | Consistent with 56,805M and 60,512M (both imply about 104M households) |
| `2003.pdf` | yes | Table 5.12 bills by method, and the "three quarters of bills paid through the mail" prose | 75% (2002) and 74% (2003) match |
| `2004.pdf` | **none, scanned** | Rendered Table 1.5 (p.14) and Table 4.12 (p.34) | First-Class received 57.3B ✓; bills by mail 69% ✓ |
| `2005.pdf` | yes | Table 1.5, Table 4.12 | First-Class received 58.8B ✓; 2005 share 67% ✓ |
| `2006.pdf` | yes | Table 1.5, Table 4.12 | First-Class received 59.3B (loaded 59.4B, restated); share 62.0% ✓ |
| `2007.pdf` … `2018.pdf` (11 files) | yes | Appendix A8-1 and A8-6, all years | Agree with loaded values except documented restatements |
| `2019.pdf` | appendix is **images** | Rendered A8-1 (p.69) and A8-6 (p.74) | Totals, advertising, and bills match for every year 2000–2019 (bills 2014: 34%, restated to 33% in FY2024) |
| `2020.pdf` | yes | **Source page** A8-1 p.72, A8-6 p.77 | 105 / 105 loaded values match |
| `2021.pdf` | chapters scanned, appendix yes | A8-1, A8-6, and all 16 A8 tables in `tables.json` | 3,572 / 3,572 cells match the PDF text |
| `2022.pdf` | yes | **Source page** A8-1 p.64, A8-6 p.69 | 65 / 65 match |
| `2023.pdf` | yes | **Source page** A8-1 p.77, A8-6 p.82, plus E.1 | 70 / 70 match; E.1 32.2B ✓ |
| `2024.pdf` | yes | **Source page** A-1 p.57, A-6 p.62, plus exec summary | 22 / 22 match; "33% … 2014 … 13% … 2024" ✓ |
| `2025.pdf` | yes | **Source page** A-9 p.62, plus Table E.4 | 51 / 51 match; E.4 "31% 21% 14%" ✓ |
| `2025.docx` | n/a | Table A-9 | 51 / 51 match |
| `2025_Household_Mail_Survey_extracted.xlsx` | n/a | Sheet `P62_T01` (Table A-9) | 51 / 51 match |
| `USPS Analysing … .pptx.pdf` | yes | Assignment slides, no data | n/a |
| `tables.xlsx - Index.pdf` | yes | Printed index of `tables.json`, no values | n/a |

There are no reports for FY2002 or FY2011 in `docs/`. Their years are still covered by the
appendix tables of later reports.

## Findings

1. **No extraction errors in the loaded data.** `tables.json` reproduced every mapped cell
   exactly.
2. **FY2021's appendix is clean.** Only its chapter pages (9–69) are scanned and OCR'd. Its 16
   Appendix A tables are `ocr=False`, and all 3,572 of their numbers match the PDF. The note in
   `CLAUDE.md` saying "2021 is OCR" was too broad, and it has been corrected.
3. **FY2019's appendix tables are images in the PDF.** That's why `tables.json` has none of
   them. They were read from rendered pages. Their values agree with the loaded data.
4. **Restatements are common.** Later reports revise earlier years:
   - Total First-Class Mail received from 2010 onward was restated by the FY2014/FY2015 reports.
     The A8 notes say the 2010 restatement was a weighting change.
   - 2020 was restated from 35,345M (FY2020) to 35,729M (FY2021–2023).
   - Bills paid by mail shifts by 1–4 points for some years. For example, 2009 is 54% in FY2009
     and FY2012 but 50% everywhere else, and 2014 is 34% in FY2018–2023 but 33% in FY2014–2017
     and FY2024.

   The loader keeps every report's value and prefers the latest one.
5. **The correspondence/transactions split was reclassified several times.** The total is
   unchanged, but the split for 2000 is 16,304M / 27,680M in FY2007–2014, 18,311M / 25,673M in
   FY2015–2016, and 19,470M / 24,514M from FY2017 on.
   - The loaded preferred series uses FY2020 (2000–2009) and FY2023 (2010+). Both use the current
     classification, and they agree where they overlap.
   - Don't mix split values from different reports without checking this.
6. **A small inconsistency in USPS's FY2020 Table A8-1.** For 2007 and 2008, the categories add
   up to 9M and 7M more than the printed total. FY2017/FY2018 give correspondence 8–9M lower,
   which does add up.
   - The loaded values match the FY2020 page, so they're kept as published (a difference under
     0.1%).
   - Both observations carry a note explaining this.

## What could not be checked

- **The FY2024 per-household series (2014–2024)** has no second source. No other report uses
  that unit, and the report's summary tables cover all mail classes rather than First-Class
  only. It does match its own page, its categories add up to its totals in all 11 years, and it
  agrees with the A8 millions series (implied households about 123M in 2014).
- **FY2000 and FY2001** don't publish a bills-by-mail share, so for those reports only the
  First-Class Mail totals were checked.

## Re-running

```
pip install -r requirements.txt
python manage.py load_tables tables.json
python manage.py load_metrics
python manage.py verify_pdfs
```

The PDFs must be in `docs/`; they're git-ignored. `verify_pdfs` checks each loaded value against
its own source page. The cross-report comparison and the rendered-page checks above were done
once, for this report. Repeat them when a new series is mapped.
