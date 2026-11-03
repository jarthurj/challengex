"""Curated mapping from raw extracted tables to clean metrics.

`manage.py load_metrics` reads this file. To add a series: declare it in METRICS, then list
every table that reports it in SOURCES. Map by row label (and `nth` when a label repeats);
year columns are read from each table's own year header, so layout differences between
reports don't matter. Only use tables with ocr=False unless the values have been verified.
"""
from dataclasses import dataclass

ALL = ("all", "All households")

METRICS = [
    {
        "slug": "fcm-received-total",
        "name": "First-Class Mail received by households",
        "market": "total",
        "direction": "received",
        "unit": "millions",
        "description": "Total First-Class Mail pieces received by U.S. households (Appendix A8-1).",
    },
    {
        "slug": "fcm-received-correspondence",
        "name": "First-Class correspondence received",
        "market": "correspondence",
        "direction": "received",
        "unit": "millions",
        "description": "Personal, business/government, and social correspondence received (A8-1).",
    },
    {
        "slug": "fcm-received-transactions",
        "name": "First-Class transaction mail received",
        "market": "transactions",
        "direction": "received",
        "unit": "millions",
        "description": "Bills, statements, payments, and donation requests received (A8-1).",
    },
    {
        "slug": "fcm-received-advertising",
        "name": "First-Class advertising received (ads only)",
        "market": "advertising",
        "direction": "received",
        "unit": "millions",
        "description": "First-Class pieces that contain only advertising (A8-1).",
    },
    {
        "slug": "fcm-received-per-household",
        "name": "First-Class Mail received per household",
        "market": "total",
        "direction": "received",
        "unit": "per_household_year",
        "description": "First-Class pieces received per household per year, as reported from FY2024 (A-1).",
    },
    {
        "slug": "bills-paid-by-mail-share",
        "name": "Share of bills paid by mail",
        "market": "transactions",
        "direction": "sent",
        "unit": "percent",
        "description": "Percent of household bill payments made by mail (A8-6, A-6; FY2025 A-9).",
    },
    {
        "slug": "bills-paid-electronic-share",
        "name": "Share of bills paid electronically",
        "market": "transactions",
        "direction": "sent",
        "unit": "percent",
        "description": (
            "Percent of household bill payments made electronically: Internet, automatic deduction, "
            "credit card and phone (A8-6 'Total Electronic'; FY2024 A-6 'Electronic (including "
            "Internet)'). Most of the rest is paid by mail or in person."
        ),
    },
    {
        "slug": "fcm-sent-total",
        "name": "First-Class Mail sent by households",
        "market": "total",
        "direction": "sent",
        "unit": "millions",
        "description": "Total First-Class Mail pieces sent by U.S. households (Appendix A8-3).",
    },
    {
        "slug": "fcm-sent-correspondence",
        "name": "First-Class correspondence sent",
        "market": "correspondence",
        "direction": "sent",
        "unit": "millions",
        "description": "Personal, business/government, and social correspondence sent (A8-3).",
    },
    {
        "slug": "fcm-sent-transactions",
        "name": "First-Class transaction mail sent",
        "market": "transactions",
        "direction": "sent",
        "unit": "millions",
        "description": "Bill payments, orders and rebate requests, and donations sent (A8-3).",
    },
    {
        "slug": "fcm-sent-per-household",
        "name": "First-Class Mail sent per household",
        "market": "total",
        "direction": "sent",
        "unit": "per_household_year",
        "description": "First-Class pieces sent per household per year, as reported from FY2024 (A-3).",
    },
    {
        "slug": "advertising-received-total",
        "name": "Advertising mail received by households",
        "market": "advertising",
        "direction": "received",
        "unit": "millions",
        "description": (
            "'Total Ads' in Appendix A8-12: First-Class advertising (ads-only and secondary) plus "
            "Marketing Mail ads."
        ),
    },
    {
        "slug": "marketing-mail-ads-received",
        "name": "Marketing Mail advertising received",
        "market": "advertising",
        "direction": "received",
        "unit": "millions",
        "description": "Marketing Mail (formerly Standard Mail) advertising pieces received (A8-12).",
    },
    {
        "slug": "household-mail-total",
        "name": "All household mail, sent and received",
        "market": "total",
        "direction": "total",
        "unit": "millions",
        "description": (
            "Mail received and sent by households across all markets (Table E.2, FY2005-FY2023 "
            "reports). Published in billions to one decimal, so values are accurate to about 50 "
            "million pieces. Before 2007, Detached Address Labels were double-counted (about +3 "
            "billion), and through 2007 residential deliveries were underestimated (about -2 to -3)."
        ),
    },
    {
        "slug": "packages-volume",
        "name": "Packages sent and received by households",
        "market": "packages",
        "direction": "total",
        "unit": "millions",
        "description": (
            "Packages market volume (Table E.2), published in billions to one decimal. From 2005 "
            "it includes CD/DVD rentals mailed as First-Class letters (0.8 billion in 2007, 0.6 "
            "in 2014, 0.1 in 2023, per the table notes); 2003-2004 exclude them."
        ),
    },
    {
        "slug": "periodicals-volume",
        "name": "Periodicals received by households",
        "market": "periodicals",
        "direction": "received",
        "unit": "millions",
        "description": "Periodicals market volume (Table E.2), published in billions to one decimal.",
    },
    {
        "slug": "household-mail-per-household",
        "name": "All household mail per household",
        "market": "total",
        "direction": "total",
        "unit": "per_household_year",
        "description": "Pieces sent and received per household per year, all markets (FY2024/FY2025 Table E.2).",
    },
    {
        "slug": "correspondence-per-household",
        "name": "Correspondence per household",
        "market": "correspondence",
        "direction": "total",
        "unit": "per_household_year",
        "description": (
            "Correspondence sent and received per household per year (Table E.2; FY2025 A-3 for "
            "household groups)."
        ),
    },
    {
        "slug": "transactions-per-household",
        "name": "Transaction mail per household",
        "market": "transactions",
        "direction": "total",
        "unit": "per_household_year",
        "description": (
            "Transaction mail sent and received per household per year (Table E.2; FY2025 A-6 for "
            "household groups)."
        ),
    },
    {
        "slug": "advertising-per-household",
        "name": "Advertising mail per household",
        "market": "advertising",
        "direction": "received",
        "unit": "per_household_year",
        "description": "Advertising market pieces per household per year (FY2024/FY2025 Table E.2).",
    },
    {
        "slug": "ads-received-per-household",
        "name": "First-Class and Marketing Mail ads received per household",
        "market": "advertising",
        "direction": "received",
        "unit": "per_household_year",
        "description": (
            "First-Class and Marketing Mail advertising received per household per year, by "
            "household group (FY2025 Table A-11). Narrower than the advertising market in Table E.2."
        ),
    },
    {
        "slug": "packages-per-household",
        "name": "Packages per household",
        "market": "packages",
        "direction": "total",
        "unit": "per_household_year",
        "description": "Packages sent and received per household per year (FY2024/FY2025 Table E.2).",
    },
    {
        "slug": "periodicals-per-household",
        "name": "Periodicals per household",
        "market": "periodicals",
        "direction": "received",
        "unit": "per_household_year",
        "description": "Periodicals received per household per year (FY2024/FY2025 Table E.2).",
    },
]

# Household groups in the FY2025 demographic tables (A-3, A-6, A-9, A-11), as labelled there.
FY2025_SEGMENTS = [
    ("age", "Under 45"),
    ("age", "45-64"),
    ("age", "65 and Over"),
    ("income", "Less than $50,000"),
    ("income", "$50,000-$99,999"),
    ("income", "$100,000-$149,999"),
    ("income", "$150,000 and Over"),
    ("education", "Less than high school"),
    ("education", "High school graduate"),
    ("education", "Some college or technical school graduate"),
    ("education", "College graduate"),
    ("tenure", "Own"),
    ("tenure", "Rent"),
    ("msa", "Large MSA"),
    ("msa", "Other MSA"),
    ("msa", "Non-MSA"),
]


@dataclass(frozen=True)
class RowMap:
    label: str  # text of the row's first cell
    metric: str  # Metric slug
    nth: int = 1  # which occurrence, when the label repeats (e.g. "Total")
    segment: tuple = ALL  # (dimension, value)


A8_1_ROWS = [
    RowMap("Total", "fcm-received-correspondence", nth=1),
    RowMap("Total", "fcm-received-transactions", nth=2),
    RowMap("Advertising (Ads Only)", "fcm-received-advertising"),
    RowMap("Total First-Class Received", "fcm-received-total"),
]

A8_3_ROWS = [
    RowMap("Total", "fcm-sent-correspondence", nth=1),
    RowMap("Total", "fcm-sent-transactions", nth=2),
    RowMap("Total First-Class Sent", "fcm-sent-total"),
]

A8_6_ROWS = [
    RowMap("Mail", "bills-paid-by-mail-share"),
    RowMap("Total Electronic 1", "bills-paid-electronic-share"),
]

A8_12_ROWS = [
    RowMap("Total Ads", "advertising-received-total"),
    RowMap("Marketing Ads 1", "marketing-mail-ads-received"),
]

# Correspondence isn't read from the billions version of E.2: the FY2017 report reclassified it
# (2015 is 13.9 billion in FY2016 and 16.3 in FY2017), so the reports don't form one series.
E2_ROWS = [
    RowMap("Total", "household-mail-total"),
    RowMap("Packages", "packages-volume"),
    RowMap("Periodicals", "periodicals-volume"),
]

E2_PER_HOUSEHOLD_ROWS = [
    RowMap("Total", "household-mail-per-household"),
    RowMap("Correspondence", "correspondence-per-household"),
    RowMap("Transactions", "transactions-per-household"),
    RowMap("Advertising", "advertising-per-household"),
    RowMap("Packages", "packages-per-household"),
    RowMap("Periodicals", "periodicals-per-household"),
]


def segment_rows(metric):
    """One row per FY2025 household group, read by the group's own label in the table."""
    return [RowMap(value, metric, segment=(dim, value)) for dim, value in FY2025_SEGMENTS]


# source_id -> (unit the table reports in, rows to read)
SOURCES = {
    # Table A8-1, First-Class Mail received by type, millions of pieces
    "2020-p072-1": ("millions", A8_1_ROWS),  # 2000-2020
    "2022-p064-1": ("millions", A8_1_ROWS),  # 2010-2022
    "2023-p077-1": ("millions", A8_1_ROWS),  # 2010-2023
    # Table A-1 (FY2024), First-Class Mail received by type, per household per year
    "2024-p057-1": ("per_household_year", [
        RowMap("Total First-Class Mail Received", "fcm-received-per-household"),
    ]),  # 2014-2024
    # Bills paid by method, percent. A8-6 "Total Electronic" and FY2024 A-6 "Electronic
    # (including Internet)" agree exactly for 2014-2023.
    "2020-p077-1": ("percent", A8_6_ROWS),  # A8-6, 2000-2020
    "2022-p069-1": ("percent", A8_6_ROWS),  # A8-6, 2010-2022
    "2023-p082-1": ("percent", A8_6_ROWS),  # A8-6, 2010-2023
    "2024-p062-1": ("percent", [  # A-6, 2014-2024
        RowMap("Mail", "bills-paid-by-mail-share"),
        RowMap("Electronic (including Internet)", "bills-paid-electronic-share"),
    ]),
    "2025-p062-1": ("percent", [  # A-9, 2015/2020/2025; "All Households" matches A-6 "Mail"
        RowMap("All Households", "bills-paid-by-mail-share"),
        *segment_rows("bills-paid-by-mail-share"),
    ]),
    # Table A8-3, First-Class Mail sent by type, millions of pieces
    "2020-p074-1": ("millions", A8_3_ROWS),  # 2000-2020
    "2022-p066-1": ("millions", A8_3_ROWS),  # 2010-2022
    "2023-p079-1": ("millions", A8_3_ROWS),  # 2010-2023
    # Table A-3 (FY2024), First-Class Mail sent by type, per household per year
    "2024-p059-1": ("per_household_year", [
        RowMap("Total First-Class Mail Sent", "fcm-sent-per-household"),
    ]),  # 2014-2024
    # Table A8-12, First-Class and Marketing Mail advertising, millions of pieces
    "2020-p082-2": ("millions", A8_12_ROWS),  # 2000-2020
    "2022-p075-1": ("millions", A8_12_ROWS),  # 2010-2022
    "2023-p088-1": ("millions", A8_12_ROWS),  # 2010-2023
    # Table E.2, household mail by market, billions; three years per report (FY2021 is OCR).
    # FY2005-FY2015 come from tables_2000_2015.json; FY2003's E.2 is a different table.
    **{source_id: ("billions", E2_ROWS) for source_id in (
        "2005-p008-2", "2006-p009-2", "2007-p009-1", "2008-p008-1", "2009-p010-2", "2010-p010-1",
        "2012-p010-2", "2013-p010-2", "2014-p010-2", "2015-p012-2",
        "2016-p010-1", "2017-p010-1", "2018-p010-1", "2019-p010-1", "2020-p010-2",
        "2022-p004-1", "2023-p011-1",
    )},
    # Table E.2 from FY2024/FY2025, per household per year (2014/2019/2024, 2015/2020/2025)
    "2024-p007-1": ("per_household_year", E2_PER_HOUSEHOLD_ROWS),
    "2025-p007-2": ("per_household_year", E2_PER_HOUSEHOLD_ROWS),
    # FY2025 demographic tables, per household per year. Their "All Households" rows match E.2,
    # which supplies them, except A-11, a narrower definition of advertising than E.2's market.
    "2025-p057-1": ("per_household_year", segment_rows("correspondence-per-household")),  # A-3
    "2025-p059-1": ("per_household_year", segment_rows("transactions-per-household")),  # A-6
    "2025-p064-1": ("per_household_year", [  # A-11
        RowMap("All Households", "ads-received-per-household"),
        *segment_rows("ads-received-per-household"),
    ]),
}

# Conversions into a metric's unit. Values already in the metric's unit pass through.
# Millions <-> per household needs an annual household count, which the reports don't
# publish (only 2014/2015/2019/2020/2024/2025), so it is deliberately not converted.
CONVERSIONS = {
    ("per_household_week", "per_household_year"): lambda v: v * 52,
    ("billions", "millions"): lambda v: v * 1000,  # E.2 publishes one decimal: +/- 50 million
}

# Notes attached to specific observations on every load: (metric, fiscal year, report year) -> note.
REVIEW_NOTES = {
    ("fcm-received-correspondence", 2007, 2020): (
        "Source inconsistency in USPS FY2020 Table A8-1: correspondence + transactions + advertising + "
        "other categories exceed the printed total by 9M for 2007. The FY2017/FY2018 reports give 18,820, "
        "which adds up. Kept as published (matches the cited page); difference is under 0.1%."
    ),
    ("fcm-received-correspondence", 2008, 2020): (
        "Source inconsistency in USPS FY2020 Table A8-1: correspondence + transactions + advertising + "
        "other categories exceed the printed total by 7M for 2008. The FY2017/FY2018 reports give 18,087, "
        "which adds up. Kept as published (matches the cited page); difference is under 0.1%."
    ),
}

BREAKS = [
    {
        "fiscal_year": 2005,
        "title": "Packages include CD/DVD rentals",
        "description": (
            "From the FY2007 report, Table E.2's packages include CD/DVD rentals mailed as "
            "First-Class letters (0.8 billion pieces in 2007), and 2005 was restated from 2.4 to 3.1 "
            "billion. The 2003 and 2004 values come from the FY2005 and FY2006 reports, whose notes "
            "count only ground and expedited packages."
        ),
        "metrics": ["packages-volume"],
    },
    {
        "fiscal_year": 2007,
        "title": "Detached Address Labels no longer double-counted",
        "description": (
            "\"Prior to 2007, Standard mail volumes were inflated by about 3 billion pieces due to a "
            "double count of Detached Address Labels\" in the Carrier Cost System, whose volumes are "
            "the control for the survey results (FY2008 Table E.2 and FY2016 Table A8-12 notes). The "
            "FY2020 A8-12 drops the note but its pre-2007 values are no lower."
        ),
        "metrics": ["household-mail-total", "advertising-received-total", "marketing-mail-ads-received"],
    },
    {
        "fiscal_year": 2008,
        "title": "Residential delivery estimates corrected",
        "description": (
            "\"Volumes through 2007 were understated by about 2 to 3 billion pieces due to a change in "
            "the methodology used by the carrier cost system for estimating deliveries to residential "
            "addresses\" (FY2008 Table E.2 note; also FY2016 Table A8-12). Before 2007 this roughly "
            "offsets the Detached Address Label double count; 2007 itself is understated."
        ),
        "metrics": ["household-mail-total", "advertising-received-total", "marketing-mail-ads-received"],
    },
    {
        "fiscal_year": 2010,
        "title": "Diary data restated with new weighting",
        "description": (
            "Beginning in 2010, diary data were restated because of changes in weighting "
            "methodology (Appendix A8 table notes). Values before 2010 use the earlier weighting."
        ),
    },
    {
        "fiscal_year": 2012,
        "title": "FY2014 report restated 2012 and 2013 (weighting by home ownership)",
        "description": (
            "\"Beginning in 2012 data was restated due to weighing by Home Ownership\" (FY2014 "
            "Appendix A, p. 249). Its Table E.2 raised 2012 and 2013 (2012 total: 131.7 billion in "
            "FY2012, 130.4 in FY2013, 136.9 in FY2014; packages 3.3 to 3.9; periodicals 5.1 to 5.9), "
            "and its notes newly exclude pieces counted as both sent and received. Later reports agree "
            "with FY2014, so values from 2012 on share one basis; values through 2011 are on the old one."
        ),
        "metrics": ["household-mail-total", "packages-volume", "periodicals-volume"],
    },
    {
        "fiscal_year": 2024,
        "title": "New contractor and per-household reporting",
        "description": (
            "From the FY2024 report, results are published as pieces per household per year, and "
            "the survey contractor changed (NuStats to RCF). The FY2024 report restated 2014-2023 "
            "on its own basis, so its values for those years can differ slightly from earlier "
            "reports (e.g. bills paid by mail in 2014: 34% in FY2023, 33% in FY2024)."
        ),
    },
    {
        "fiscal_year": 2025,
        "title": "Household Mail Survey redesign",
        "description": (
            "FY2025 used a new survey design (renamed the Household Mail Survey); Q1 was still "
            "covered by the old survey. Age bands changed to Under 45 / 45-64 / 65+ (previously "
            "18-34 / 35-54 / 55+), and 'Large MSA' was redefined in January 2025 from the top 30 "
            "metros to metros of 1 million or more."
        ),
    },
]
