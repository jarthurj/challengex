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
]

# FY2025 Table A-9 breaks the bills-by-mail share down by household group.
FY2025_BILL_SEGMENTS = [
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
    # Bills paid by method, percent
    "2020-p077-1": ("percent", [RowMap("Mail", "bills-paid-by-mail-share")]),  # A8-6, 2000-2020
    "2022-p069-1": ("percent", [RowMap("Mail", "bills-paid-by-mail-share")]),  # A8-6, 2010-2022
    "2023-p082-1": ("percent", [RowMap("Mail", "bills-paid-by-mail-share")]),  # A8-6, 2010-2023
    "2024-p062-1": ("percent", [RowMap("Mail", "bills-paid-by-mail-share")]),  # A-6, 2014-2024
    "2025-p062-1": ("percent", [  # A-9, 2015/2020/2025; "All Households" matches A-6 "Mail"
        RowMap("All Households", "bills-paid-by-mail-share"),
        *[RowMap(value, "bills-paid-by-mail-share", segment=(dim, value))
          for dim, value in FY2025_BILL_SEGMENTS],
    ]),
}

# Conversions into a metric's unit. Values already in the metric's unit pass through.
# Millions <-> per household needs an annual household count, which the reports don't
# publish (only 2014/2015/2019/2020/2024/2025), so it is deliberately not converted.
CONVERSIONS = {
    ("per_household_week", "per_household_year"): lambda v: v * 52,
}

BREAKS = [
    {
        "fiscal_year": 2010,
        "title": "Diary data restated with new weighting",
        "description": (
            "Beginning in 2010, diary data were restated because of changes in weighting "
            "methodology (Appendix A8 table notes). Values before 2010 use the earlier weighting."
        ),
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
