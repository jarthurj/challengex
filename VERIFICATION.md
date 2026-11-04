# Data verification: loaded metrics vs. the source reports

**Result: all 313 loaded values match their source PDF pages exactly, so none needed
correcting.** I also checked them against every other file in `docs/`. Where reports disagree, the
cause is a documented restatement or reclassification, or in two cases a small inconsistency in
USPS's own table, not an extraction error.

Checked 2026-10-27, against the six metrics in `dashboard/metric_sources.py`.

**Update 2026-10-31: 23 metrics, 869 values, all 869 match their source page** (`python manage.py
verify_pdfs`: 869 match, 0 mismatch, 0 unchecked). The new series come from A8-3/A-3 (First-Class
Mail sent), A8-6/A-6 (bills paid electronically), A8-12 (advertising), Table E.2 (all markets,
packages, periodicals; in billions, and per household from FY2024), and FY2025 A-3, A-6 and A-11
(household groups). Cross-report checks done while mapping them:

| Check | Result |
|---|---|
| A8-3 sent totals and splits, FY2020 vs. FY2023 | identical for 2010–2019; 2020 restated in FY2023 |
| A8-6 "Total Electronic" (FY2023) vs. A-6 "Electronic (including Internet)" (FY2024) | identical for 2014–2023 |
| A8-12 total and Marketing Mail ads, FY2020 vs. FY2023 | identical for 2010–2019 |
| FY2025 A-3 / A-6 "All Households" vs. FY2025 E.2 per household | identical (2015, 2020, 2025) |
| FY2025 A-11 "All Households" vs. E.2 advertising | differ (643.6 vs. 658.9 in 2015): A-11 is First-Class and Marketing Mail ads only, so it is a separate metric |
| E.2 correspondence in billions, FY2016 vs. FY2017 | differ (13.9 vs. 16.3 for 2015): reclassified, so not mapped |

**Update 2026-11-03 (household groups): 1,592 values, all 1,592 match their source page.** 633
new values come from the one-year tables "... Mail Received by Income and Age" and "... by Income
and Education" (transactions and correspondence FY2003–FY2023, advertising FY2005–FY2023; not
FY2021, which is OCR). `verify_pdfs` reads each table from its caption on the PDF page through the
same code as the loader. The education tables repeat the age tables' income and all-households
margins, an independent check:

| Check | Result |
|---|---|
| Margins of the education tables vs. the age tables (260 values) | 254 identical; 2 differ only in print ("14" vs. "14.0", FY2015 advertising); 4 differ by 0.1 (FY2005 transactions $65K–$100K 6.1 vs. 6.2; FY2006 advertising $35K–$65K 16.3 vs. 16.2; FY2012 advertising Under $35K 8.1 vs. 8.2 and Over $100K 19.2 vs. 19.1), USPS rounding, and the age table's value is used |
| Own-year values vs. later reports (Table E.2) | these one-year series aren't restated, so each reclassification is a break on the metrics it moved: FY2008 redefined correspondence (2007: 14.6 → 16.9 billion, from unclassified; p. 27); FY2012, FY2015 and FY2017 moved mail between correspondence and transactions (e.g. 2014 correspondence 11.0 → 13.7); FY2013 restated transactions after the 2011 questionnaire (2012: 34.3 → 33.1; pp. 38, 41). Smaller ones (FY2007: 2006 transactions 41.6 → 42.7; FY2022: 2020 correspondence 14.6 → 15.0) are within about one rounding step of the weekly values and aren't breaks |
| FY2003 advertising (Tables 6.3/6.4) | "Base: Total Advertising Mail (including Unaddressed)"; from FY2005 totals exclude unaddressed mail (FY2005 Table 5.3 restates 2003 at 15.9 a week vs. FY2003's 14.3), so FY2003 isn't used |
| FY2017 Tables 4.2–4.4 | cite the "HDS Recruitment Sample" instead of the Diary Sample; kept as published, with a note |
| FY2015 correspondence | Table 3.4 (by income and age, p. 30) was not extracted; Table 3.2 supplies the margins, so FY2015 has no age groups |

**Update 2026-11-03: 959 values, all 959 match their source page.** Table E.2 from the FY2005–
FY2015 reports (`tables_2000_2015.json`) extends `household-mail-total`, `packages-volume` and
`periodicals-volume` back to 2003 (90 values). Every overlapping year was compared across reports:

| Check | Result |
|---|---|
| Total, packages, periodicals: each year in 2 or 3 reports, FY2005–FY2017 | mostly identical; the differences are the rows below |
| Packages 2005: FY2005/FY2006 2.4 vs. FY2007 3.1 billion | FY2007 counts CD/DVD rentals as packages (its note); break at 2005 |
| 2006: total 168.6 (FY2006) vs. 170.2 (FY2007, FY2008); packages 3.3 vs. 3.2 | small revision in FY2007, not explained; the FY2008 value is preferred |
| Total through 2007 | carrier cost system: Detached Address Labels double-counted before 2007 (about +3 billion) and residential deliveries understated through 2007 (about −2 to −3 billion), per the FY2008 E.2 and FY2016 A8-12 notes; breaks at 2007 and 2008, also on the A8-12 advertising series |
| Total 2010: 141.1 (FY2010) vs. 141.2 (FY2012); 2011: 139.1 (FY2012) vs. 138.3 (FY2013) | small revisions, not explained |
| 2012–2013: total 2012 131.7 (FY2012), 130.4 (FY2013), 136.9 (FY2014); packages 3.3 vs. 3.9; periodicals 5.1 vs. 5.9 | FY2014: "Beginning in 2012 data was restated due to weighing by Home Ownership" (Appendix A, p. 249); FY2015 and FY2016 agree with FY2014; break at 2012 |
| 2015: total 126.8 vs. 128.4, packages 4.7 vs. 4.3, periodicals 4.9 vs. 5.1 (FY2016 vs. FY2017) | restated in FY2017 (already loaded before this update; FY2017 is preferred) |

`verify_pdfs` first skipped the FY2005 and FY2006 pages: Table E.1 above E.2 has rows with the same
labels. It now reads only rows below the year header, and the original 869 values still match.

The rest of this document describes the original six-metric check.

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
python manage.py rebuild_db
```

or step by step:

```
python manage.py load_tables tables.json tables_2000_2015.json
python manage.py load_metrics
python manage.py verify_pdfs
```

The PDFs must be in `docs/`; they're git-ignored. `verify_pdfs` checks each loaded value against
its own source page. The cross-report comparison and the rendered-page checks above were done
once, for this report. Repeat them when a new series is mapped.
