"""Recover real table titles and numbers from the report PDFs' text.

The extraction in tables.json often has no title, a scrap of body text as the title, or a table
number taken from prose ("Table 1.6 presents..."). Each report has:
  * captions on the table's own page ("Table 3.6: Correspondence Mail ... by Household Size"), and
  * usually a List of Tables near the front with the clean, full title for every number.

A table is matched to a caption by content: rows whose label and exact numbers appear on exactly
one line of the page vote for the caption above that line. Fallbacks only use captions no other
table on the page has claimed. `manage.py extract_titles` runs this and writes table_titles.json,
which `load_tables` applies.
"""
import collections
import re

NUMID = r"(?:[A-Z]{1,2}\d*-\d+[A-Za-z0-9]*|[A-Z]?\d*\.\d+[a-z]?)"  # A8-1, A8-13A2, A-1, E.1, 3.10, 1.4a
CAPTION = re.compile(rf"^\s*(Table|Figure)\s+({NUMID})\s*(?::\s*(.*))?\s*$")
TOC_LINE = re.compile(rf"^\s*(Table|Figure)\s+({NUMID})\s*:\s*(.+?)[\s.]*\s([ivx]+|\d+)\s*$")
NUMTOK = re.compile(r"(?:\d[\d,]*\.?\d*|\.\d+)%?")  # 4,855  81%  2.1  .5
YEAR = re.compile(r"(19|20)\d\d,?")
SUBTITLE = re.compile(r"(Pieces in|Percent of|Years \d{4})")  # appendix subtitles
GENERIC = {"", "total", "totals", "average", "all", "overall", "total households", "all households"}
STOP = set("the of and by in to a for per week household households pieces received sent mail table "
           "total all average year years fy vs".split())

# Cases the text can't settle, checked by hand against the page.
MANUAL = {
    # USPS's List of Tables gives 5.10 and 5.11 the same title; 5.11's header is "Past Business
    # Relationship with Recipient" and the prose says "Table 5.11 illustrates how the existence of
    # a past [business relationship]...". 5.10 is the Yes/Maybe/No table by mail class.
    "2022-p048-1": ("Table 5.11", "Intended Response to Advertising Mail by Past Business Relationship (Percentage of Pieces)"),
    "2022-p048-5": ("Table 5.10", "Intended Response to Advertising Mail by Class (Percentage of Pieces)"),
    "2023-p060-1": ("Table 5.11", "Intended Response to Advertising Mail by Past Business Relationship (Percentage of Pieces)"),
    "2023-p060-5": ("Table 5.10", "Intended Response to Advertising Mail by Class (Percentage of Pieces)"),
    # FY2021 chapter pages are scanned; the OCR'd caption on both tables reads 6.4/6.5 "Number of
    # Adults". Rows decide: "One person, Two, ..." is household size, "One, Two, Three or more" is adults.
    "2021-p061-2": ("Table 6.5", "Periodicals by Number of Adults in Household"),
    "2021-p061-3": ("Table 6.4", "Periodicals by Size of Household"),
}

# Pages with no usable text, read from the rendered page image and matched to each extracted table
# by its rows (or, for charts, by its values/legend; two charts on a page in top-to-bottom order).
# Mostly FY2021's scanned chapter pages; "Figure" entries are charts whose extracted values are OCR noise.
FROM_PAGE_IMAGES = {
    "2016-p025-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
    "2016-p053-1": ("Figure 5.3", "Advertising Mail Behavioral Trends, FY 1987, 2014, 2015, and 2016"),
    "2018-p022-2": ("Figure 2.1b", "Internet Access by Age and Type"),
    "2018-p023-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
    "2019-p022-2": ("Figure 2.1b", "Internet Access by Age and Type"),
    "2019-p023-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
    "2020-p024-2": ("Figure 2.1b", "Internet Access by Age and Type"),
    "2020-p025-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
    "2021-p010-1": ("Table E.3", "Bill Payment Methods"),
    "2021-p010-2": ("Table E.2", "Household Mail Volume Received and Sent by Market Served (Billions of Pieces)"),
    "2021-p011-1": ("Table E.4", "Advertising by Mail Class"),
    "2021-p011-3": ("Table E.6", "Packages Received and Sent via the U.S. Postal Service (Millions of Pieces)"),
    "2021-p015-2": ("Table 1.2", "Total Domestic Mail Flows (Billions of Pieces)"),
    "2021-p015-4": ("Table 1.3", "Total Domestic Mail Flows"),
    "2021-p016-1": ("Table 1.6", "Pieces Received and Sent per Household"),
    "2021-p019-1": ("Table 2.1", "Mail Volume and Demographics, Average Annual Growth, 1981-2021"),
    "2021-p023-1": ("Table 2.6", "Households by Number of Adults (Millions of Households)"),
    "2021-p023-2": ("Table 2.8", "Households by Type of Internet Access (Millions of Households)"),
    "2021-p023-3": ("Table 2.7", "Households by Size (Millions of Households)"),
    "2021-p024-1": ("Figure 2.1a", "Internet Access by Income and Type"),
    "2021-p024-2": ("Figure 2.1b", "Internet Access by Age and Type"),
    "2021-p025-1": ("Figure 2.2", "Broadband Subscribers"),
    "2021-p025-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
    "2021-p030-1": ("Table 3.6", "Correspondence Mail Received and Sent by Household Size (Pieces per Household per Week)"),
    "2021-p030-3": ("Table 3.9", "Income and Education by Type of Internet Access"),
    "2021-p030-4": ("Table 3.7", "Correspondence Mail Received and Sent by Number of Adults in Household (Pieces per Household per Week)"),
    "2021-p032-1": ("Figure 3.1", "Personal Correspondence Sent by Income Group (Pieces per Household per Year)"),
    "2021-p032-2": ("Figure 3.2", "Personal Correspondence Sent by Age Cohort (Pieces per Household per Year)"),
    "2021-p033-1": ("Figure 3.3", "Holiday Greetings Sent by Age and Income, FY 2019, 2020, and 2021"),
    "2021-p038-1": ("Table 4.5", "Transactions Mail Sent by Income and Age (Pieces per Household per Week)"),
    "2021-p038-2": ("Table 4.7", "Transactions Mail Received and Sent by Number of Adults in Household (Pieces per Household per Week)"),
    "2021-p038-3": ("Table 4.6", "Transactions Mail Received and Sent by Household Size (Pieces per Household per Week)"),
    "2021-p038-4": ("Table 4.8", "Transactions Mail Received and Sent by Internet Access (Pieces per Household per Week)"),
    "2021-p039-1": ("Table 4.9", "Income and Education by Type of Internet Access"),
    # p40 holds two charts but only one was extracted, and its values are OCR noise: can't tell which.
    "2021-p040-2": ("Figure 4.1/4.2", "Chart on this page: Figure 4.1 Monthly Average Household Bill Payment by "
                                      "Method, or Figure 4.2 Average Monthly Automatic Deductions per Household"),
    "2021-p042-1": ("Figure 4.4", "Bill Payment Method by Age"),
    "2021-p044-1": ("Figure 4.5a", "Bills Received by Mail Per Week by Income"),
    "2021-p044-2": ("Figure 4.5b", "Statements Received by Mail Per Week by Income"),
    "2021-p045-2": ("Figure 4.6", "Shares of Bills Received by Methods and by Age"),
    "2021-p047-1": ("Figure 5.1", "Direct Mail as a Share of Total Advertising, 2011-2021"),
    "2021-p047-2": ("Table 5.1", "U.S. Advertising Spending Growth by Medium, 2019-2021 (Percent Growth from Prior Year)"),
    "2021-p051-1": ("Table 5.8", "Advertising Mail Received by Internet Access (Pieces per Household per Week)"),
    "2021-p051-2": ("Table 5.7", "Advertising Mail Received by Number of Adults (Pieces per Household per Week)"),
    "2021-p051-3": ("Table 5.9", "Income and Education by Type of Internet Access"),
    "2021-p052-1": ("Figure 5.2", "Advertising Volumes for First-Class and Marketing Mail Advertising by Sender Type"),
    "2021-p052-2": ("Figure 5.2", "Advertising Volumes for First-Class and Marketing Mail Advertising by Sender Type"),
    "2021-p053-1": ("Figure 5.3", "Advertising Mail Behavioral Trends, FY 1987, 2019, 2020, and 2021"),
    "2021-p053-2": ("Figure 5.4", "Treatment of Marketing Mail Advertising by Type"),
    "2021-p054-1": ("Figure 5.5", "Treatment of Advertising Mail by Number of Marketing Mail Pieces Received per Week"),
    "2021-p055-1": ("Figure 5.6", "Marketing Mail Reading Rates by Household Demographics - FY 2021"),
    "2021-p056-2": ("Figure 5.7", "Weekly Number of Intended Responses by Income"),
    "2021-p059-2": ("Figure 6.3", "Newspaper Circulation, 1990-2020"),
    "2021-p062-1": ("Figure 6.4", "Subscription Type by Year"),
    "2021-p063-1": ("Figure 6.5", "Number of Periodicals Received per Week by Households by Income Group"),
    "2021-p065-1": ("Figure 7.1", "Packages Sent and Received by Household Income (Pieces per Household per Week)"),
    "2021-p067-2": ("Table 7.6", "Postal Service Received and Sent Packages by Number of Adults in Household (Pieces per Household per Week)"),
    "2021-p067-3": ("Table 7.5", "Postal Service Received and Sent Packages by Size of Household (Pieces per Household per Week)"),
    "2021-p068-1": ("Table 7.8", "Received and Sent Packages by Household Online Shopping Behavior (Pieces per Household per Week)"),
    "2021-p068-2": ("Table 7.7", "Received and Sent Packages by Household Internet Access (Pieces per Household per Week)"),
    "2021-p090-1": ("Table B.1", "Sample by Postal Quarter"),
    "2021-p090-2": ("Table B.2", "Sample by Recruitment Type"),
    "2021-p095-3": ("Table B.9", "HDS 2021 Recruitment Data: Urban/Rural Location"),
    "2022-p017-2": ("Figure 2.3", "Household Visits to Post Office in Past Month"),
}

# Extracted "tables" from these pages on are pieces of Appendix C, the survey instruments (cover
# letter, diary instructions, blank answer sheets), not data. Checked by reading the pages.
SURVEY_FORMS_FROM_PAGE = {2016: 131, 2017: 127, 2021: 147}
SURVEY_FORM_TITLE = "Survey form (Appendix C: diary letter, instructions, or blank answer sheet), not a data table"


def norm(text):
    return " ".join((text or "").split())


def fix_line(line):
    """Undo PDF spacing inside numbers: "Table 7. 1:" -> "Table 7.1:", "Table B.1 1:" -> "Table B.11:"."""
    line = re.sub(r"((?:Table|Figure)\s+[A-Z]?\d*\.)\s+(\d)", r"\1\2", line)
    return re.sub(r"((?:Table|Figure)\s+[A-Z]?\d*\.\d+)\s+(\d+\s*:)", r"\1\2", line)


def list_of_tables(pages):
    """{"Table 3.6": title} from List of Tables/Figures pages near the front of a report."""
    titles = {}
    for p in sorted(pages)[:15]:
        hits = [TOC_LINE.match(line) for line in pages[p]]
        if sum(bool(h) for h in hits) >= 4:
            for m in filter(None, hits):
                titles.setdefault(f"{m.group(1)} {m.group(2)}", norm(m.group(3)).rstrip(" ."))
    return titles


def captions(lines):
    """Real captions on a page (not prose references), with the lines that continue the title."""
    out = []
    for i, line in enumerate(lines):
        m = CAPTION.match(line)
        if not m:
            continue
        inline, follow = norm(m.group(3)), []
        for nxt in lines[i + 1:i + 6]:
            n = norm(nxt)
            data = [x for x in NUMTOK.findall(n) if not YEAR.fullmatch(x)]
            if not n or len(data) >= 2 or len(n) > 90 or CAPTION.match(nxt) or re.match(r"(Source|Note)s?\b", n):
                break
            prev = follow[-1] if follow else inline
            units = (n.startswith("(") and n.endswith(")")) or bool(SUBTITLE.match(n))
            wraps = n[0].islower() or re.search(r"(\b(by|and|of|for|in|to|the|with|vs\.?)|[-–,:])$", prev)
            if prev and not (units or wraps):
                break  # an uppercase line that doesn't continue the title is a column header
            follow.append(n)
            if units and not n.startswith(("Pieces in", "Percent of")):
                break
        out.append({"line": i, "num": f"{m.group(1)} {m.group(2)}", "inline": inline, "follow": follow})
    return out


def row_lines(table, lines):
    """Line indexes where a distinctive row appears exactly once: its label, then only its numbers."""
    normed = [norm(l) for l in lines]
    hits = []
    for r in table["rows"]:
        label = norm(r[0])
        nums = [c.strip() for c in r[1:] if NUMTOK.fullmatch(c.strip())]
        # totals/averages, unlabelled rows, year headers and all-100% rows repeat across tables
        if (not nums or label.lower() in GENERIC or all(YEAR.fullmatch(x) for x in nums)
                or all(x.rstrip("%").rstrip("0").rstrip(".") == "1" for x in nums)):
            continue
        found = [i for i, n in enumerate(normed)
                 if n.startswith(label) and re.fullmatch(r"[\s\d,.%$()\-–]*", n[len(label):])
                 and NUMTOK.findall(n[len(label):]) == nums]
        if len(found) == 1:
            hits.append(found[0])
    return hits


def stems(text):
    return {w[:5] for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}


def table_words(t):
    return stems(" ".join([*t["columns"], *(r[0] for r in t["rows"]), *(c for r in t["rows"][:2] for c in r)]))


def caption_words(c):
    return stems(" ".join([c["inline"], *c["follow"]]).split("(")[0])


def title_for(cap, toc):
    is_sub = lambda f: (f.startswith("(") and f.endswith(")")) or SUBTITLE.match(f)
    main = norm(" ".join([cap["inline"], *(f for f in cap["follow"] if not is_sub(f))]))
    title = toc.get(cap["num"]) or main
    subs = [f for f in cap["follow"] if is_sub(f) and f not in title]
    if title and subs:
        title = f"{title} {', '.join(subs)}" if subs[0].startswith("(") else f"{title}, {', '.join(subs)}"
    return title or None


def assign_page(tables, lines, toc):
    """{table id: (caption, method)} for the extracted tables on one page (tables in page order)."""
    caps = captions(lines)
    out = {}
    if not caps:
        return out
    # 1. Content: each uniquely located row votes for the caption above it.
    for t in tables:
        votes = collections.Counter()
        for h in row_lines(t, lines):
            above = [c for c in caps if c["line"] <= h]
            votes[(above[-1] if above else caps[0])["num"], bool(above)] += 1
        if votes:
            (num, is_above), _ = votes.most_common(1)[0]
            out[t["id"]] = (next(c for c in caps if c["num"] == num),
                            "caption above content" if is_above else "caption below content")
    # 2. Two-column pages can put a table's text after a later caption. If the voted caption shares
    #    no words with its table but an unclaimed caption (or the List of Tables entry for the
    #    table's own extracted number) does, trust the words.
    by_id = {t["id"]: t for t in tables}
    for t in tables:
        if t["id"] not in out:
            continue
        body = table_words(t)
        if caption_words(out[t["id"]][0]) & body:
            continue
        claimed = {c["num"] for k, (c, _) in out.items()
                   if k != t["id"] and caption_words(c) & table_words(by_id[k])}
        candidates = [c for c in caps if c["num"] not in claimed and caption_words(c) & body]
        own = t["table_number"]
        if own in toc and own not in claimed and own not in {c["num"] for c in caps}:
            listed = {"num": own, "inline": toc[own], "follow": [], "line": -1}
            if caption_words(listed) & body:
                candidates.append(listed)
        if candidates:
            out[t["id"]] = (max(candidates, key=lambda c: len(caption_words(c) & body)),
                            "caption words match table (text order unreliable)")
    # 3. Elimination among captions no table has claimed.
    left = [t for t in tables if t["id"] not in out]
    free = [c for c in caps if c["num"] not in {c["num"] for c, _ in out.values()}]
    if left and free:
        if len(left) == len(free):
            for t, c in zip(left, free):
                out[t["id"]] = (c, "only unclaimed caption" if len(free) == 1 else "unclaimed captions, page order")
        else:
            counts = collections.Counter(t["table_number"] for t in left)
            for t in left:
                c = next((c for c in free if c["num"] == t["table_number"]), None)
                if c and counts[t["table_number"]] == 1:
                    out[t["id"]] = (c, "extracted number is an unclaimed caption")
    return out


def assign_report(tables, pages):
    """Title records for every extracted table of one report.

    `pages` maps PDF page number -> list of text lines (empty for scanned pages).
    """
    pages = {p: [fix_line(l) for l in lines] for p, lines in pages.items()}
    toc = list_of_tables(pages)
    by_page = collections.defaultdict(list)
    for t in tables:
        by_page[t["page"]].append(t)
    assigned = {}
    for page, on_page in by_page.items():
        on_page.sort(key=lambda t: int(t["id"].rsplit("-", 1)[1]))
        assigned.update(assign_page(on_page, pages.get(page, []), toc))

    records = {}
    for t in tables:
        lines = pages.get(t["page"], [])
        rec = {"was_number": t["table_number"], "was_title": t["title"]}
        if t["id"] in MANUAL:
            num, title = MANUAL[t["id"]]
            rec.update(table_number=num, title=title, method="manual (see dashboard/titles.py)")
        elif t["id"] in FROM_PAGE_IMAGES:
            num, title = FROM_PAGE_IMAGES[t["id"]]
            rec.update(table_number=num, title=title, method="read from the page image (scanned or chart page)")
        elif t["page"] >= SURVEY_FORMS_FROM_PAGE.get(t["year"], 10_000):
            rec.update(table_number="", title=SURVEY_FORM_TITLE, method="survey instrument page (Appendix C)")
        elif t["id"] in assigned:
            cap, method = assigned[t["id"]]
            rec.update(table_number=cap["num"], title=title_for(cap, toc), method=method)
        elif not any(l.strip() for l in lines) and toc:
            # Scanned page: accept the OCR'd caption only if it contains a List of Tables title.
            ocr = re.sub(r"[^a-z]", "", (t["title"] or "").lower())
            found = [(n, ti) for n, ti in toc.items() if len(ti) > 12 and re.sub(r"[^a-z]", "", ti.lower()) in ocr]
            if found:
                num, title = max(found, key=lambda x: len(x[1]))
                rec.update(table_number=num, title=title, method="OCR caption matches List of Tables")
        if "method" not in rec:
            rec["method"] = "none: " + ("scanned page" if not any(l.strip() for l in lines)
                                        else "no caption on page" if not captions(lines) else "content not located")
        records[t["id"]] = rec
    return records
