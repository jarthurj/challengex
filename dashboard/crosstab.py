"""One-year household-group tables: "X Mail Received by Income and Age" (or "... and Education").

Every report from FY2003 to FY2023 prints them the same way: income bands as rows, the age or
education groups as columns, then an "Average" (FY2003, FY2005: "Total") column and row. The
Average row gives each column group, the Average column each income band, and the corner all
households, for the report's own year. load_metrics reads them from the extracted rows and
verify_pdfs from the PDF text, both through crosstab_values(), so both read them the same way.
"""
import re

ALL = ("all", "All households")

# (segment value, how the band is printed with spaces and "k" removed). The report's own labels;
# the bands are nominal dollars, so their make-up drifts with inflation over 20 years.
INCOME_BANDS = [
    ("Under $35K", "under$35"),
    ("$35K to $65K", "$35to$65"),
    ("$65K to $100K", "$65to$100"),
    ("Over $100K", "over$100"),
]

# Column groups in printed order: (segment value, pattern of its heading). FY2003 and FY2015 print
# "Under 34" for the youngest band. The education groups are the four FY2025 uses, so they share
# its segment names ("Some College or Technical School" there adds "graduate").
COLUMN_GROUPS = {
    "age": [
        ("Under 35", r"\bunder\b(?!\s*\$)"),  # "Under 35", "Under 34", or "Under" wrapped from "35"
        ("35 to 54", r"35\s*to"),
        ("Over 55", r"over\s*55"),
    ],
    "education": [
        ("Less than high school", r"less\s*than"),
        ("High school graduate", r"high\s*school\s*grad"),
        ("Some college or technical school graduate", r"some\s*college"),
        ("College graduate", r"college\s*grad"),
    ],
}
TOTALS = {"average", "total"}


def income_band(label):
    key = re.sub(r"[\sk]", "", label.lower())
    return next((band for band, printed in INCOME_BANDS if printed == key), None)


def check_heading(text, columns):
    """None if the column groups appear in `text` (the table's heading) in the expected order."""
    pos = 0
    for value, pattern in COLUMN_GROUPS[columns]:
        found = re.compile(pattern, re.I).search(text, pos)
        if not found:
            return f"column group {value!r} not found in order in the heading"
        pos = found.end()
    if not re.search(r"\b(average|total)\b", text, re.I):
        return "no Average/Total column in the heading"
    return None


def crosstab_values(rows, columns, margins=True):
    """[((dimension, value), raw)] from [(row label, [values in order])].

    `margins`: also the income bands and all households (the education tables repeat the age
    tables' margins, so only one of the two supplies them). Raises ValueError when the table is
    not the expected shape, rather than guessing.
    """
    groups = [value for value, _ in COLUMN_GROUPS[columns]]
    width = len(groups) + 1
    incomes, total = {}, None
    for label, values in rows:
        band = income_band(label)
        is_total = label.strip().lower() in TOTALS
        if not band and not is_total:
            continue
        if len(values) != width:
            raise ValueError(f"row {label.strip()!r} has {len(values)} values for {width} columns")
        if band:
            if band in incomes:
                raise ValueError(f"row {label.strip()!r} appears twice")
            incomes[band] = values[-1]
        elif total is None:
            total = values
        else:
            raise ValueError("two Average/Total rows")
    missing = [band for band, _ in INCOME_BANDS if band not in incomes]
    if missing or total is None:
        raise ValueError(f"missing rows: {', '.join(missing + ([] if total else ['Average']))}")
    out = [((columns, group), value) for group, value in zip(groups, total[:-1])]
    if margins:
        out += [(("income", band), incomes[band]) for band, _ in INCOME_BANDS]
        out.append((ALL, total[-1]))
    return out
