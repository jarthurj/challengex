"""Find the report's own sentences about a table, to quote verbatim on the table page.

Reports discuss their tables in the body text ("As shown in Table 7.7, households with
broadband..."). For each table we collect the sentences that mention its number, anywhere in the
same report, quoted exactly; nothing is paraphrased or generated. Only paragraph text is
searched: table cells, captions, page headers and lists of tables are left out.

Used by `manage.py extract_context`, which writes table_context.json.
"""
import re

ABBREV = re.compile(r"(?:\b(?:U\.S|vs|e\.g|i\.e|No|Fig|approx|etc|Inc|Co|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)|\b[A-Z])\.$")
# "...advertisers in the U.S. Although there is..." -- U.S. ends the sentence before these words
STARTER = re.compile(r"(?:Although|However|The|This|These|In|As|While|For|Since|It|Over|By)\b")
NUM_TOKEN = re.compile(r"[\d,.]*\d%?")
REF = r"\b(?:Tables?|Figures?|Figs?\.?)\s+(?:[A-Z]?\d*[.\-]\d+[a-z]?\d*(?:\s*(?:,|and|&|through|–|-)\s*)?)+"


def norm(text):
    return " ".join((text or "").split())


def _is_prose(text):
    """Paragraph text: enough words, few numbers, not a caption/source/header line."""
    words = text.split()
    if len(words) < 8:
        return False
    if re.match(r"^\s*(Table|Figure)\s+[^:]{1,10}:", text) or re.match(r"^\s*(Source|Note)s?\s*:", text):
        return False
    numeric = sum(1 for w in words if NUM_TOKEN.fullmatch(w.strip("(),;")))
    if numeric / len(words) > 0.3:
        return False
    if re.search(r"\.{4,}", text):  # list-of-tables leader dots
        return False
    return True


def join_lines(lines):
    """Join a paragraph's lines; a line ending in a hyphen joins the next without a space."""
    out = ""
    for line in lines:
        line = norm(line)
        if not line:
            continue
        if out.endswith("-") and (line[:1].islower() or (out[-2:-1].isdigit() and line[:1].isdigit())):
            out += line  # "house-" / "hold", "35-" / "54"
        else:
            out = f"{out} {line}" if out else line
    return out


def sentences(paragraph):
    """Split a paragraph into sentences, without splitting at 'U.S.', 'vs.', '4.7' and the like."""
    parts, start = [], 0
    for m in re.finditer(r"[.!?][\"”')\]]?\s+(?=[A-Z(“\"])", paragraph):
        head = paragraph[start:m.start() + 1]
        if ABBREV.search(head) and not (head.endswith("U.S.") and STARTER.match(paragraph, m.end())):
            continue
        parts.append(paragraph[start:m.end()].strip())
        start = m.end()
    tail = paragraph[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def mentions(sentence, number):
    """True if the sentence refers to this table/figure number (also 'Tables 5.6 and 5.7').

    A combined chart numbered "Figure 4.1/4.2" matches a mention of either figure.
    """
    kind, _, num = number.partition(" ")
    if not num:
        return False
    wanted = set(num.split("/"))
    for ref in re.finditer(REF, sentence):
        text = ref.group(0)
        if text[:3].lower() != kind[:3].lower():  # "Fig. 7.1" counts as "Figure 7.1"
            continue
        if wanted & set(re.findall(r"[A-Z]?\d*[.\-]\d+[a-z]?\d*", text)):
            return True
    return False


def paragraphs_from_blocks(blocks):
    """Prose paragraphs from PyMuPDF text blocks (x0, y0, x1, y1, text, ...), in reading order."""
    out = []
    for b in blocks:
        # A block can hold a "Source:" line, a blank line, then a paragraph: split at blank lines.
        for chunk in re.split(r"\n\s*\n", b[4]):
            lines = [line for line in chunk.splitlines() if line.strip() and not _letter_spaced(line)]
            # A short run-in heading ("Household Size") on the paragraph's first line
            if (len(lines) > 1 and len(lines[0].split()) <= 4 and not re.search(r"[.,;:]\s*$", lines[0])
                    and all(w[0].isupper() or w in ("and", "of", "the", "by") for w in lines[0].split())
                    and lines[1].lstrip()[:1].isupper()):
                lines = lines[1:]
            if lines:
                out.append(join_lines(lines))
    # Rejoin sentences broken across columns. A footnote or a few table cells can sit between the
    # two parts, but another paragraph can't.
    i = 0
    while i < len(out):
        nxt = None
        if _wordy(out[i]):
            for j in range(i + 1, min(i + 4, len(out))):
                if continues(out[i], out[j]):
                    nxt = j
                    break
                if _is_prose(out[j]) and not re.match(r"\d+ [A-Z]", out[j]):  # footnotes don't count
                    break
        if nxt is None:
            i += 1
        else:
            out[i] = join_lines([out[i], out.pop(nxt)])
    return [text for text in out if _is_prose(text)]


def _letter_spaced(line):
    """A running page header set in spaced capitals: "2 0 2 5 H O U S E H O L D  M A I L ..."."""
    tokens = line.split()
    return len(tokens) >= 4 and sum(1 for t in tokens if len(t) == 1) / len(tokens) >= 0.6


def _wordy(text):
    """Mostly words, unlike a row of table cells ("Total Periodicals 4.9 100%")."""
    words = text.split()
    return len(words) >= 2 and sum(1 for w in words if NUM_TOKEN.fullmatch(w.strip("(),;$"))) / len(words) <= 0.3


def continues(previous, text):
    """A sentence broken across columns or pages: no closing punctuation, then a lowercase start
    (or a number then a lowercase word: "12 mutually exclusive...", but not footnote "1 Core-Based")."""
    starts = text[:1].islower() or re.match(r"[\d,.%]+ [a-z]", text)
    return bool(starts) and not re.search(r"[.!?:;\"”]\s*$", previous)


def stitch(report_paragraphs):
    """Join a paragraph that carries over from one page to the next; it's quoted at its first page."""
    pages = dict(sorted((p, list(paras)) for p, paras in report_paragraphs.items()))
    previous = None
    for page, paras in pages.items():
        if (previous is not None and page == previous + 1 and pages[previous] and paras
                and continues(pages[previous][-1], paras[0])):
            pages[previous][-1] = join_lines([pages[previous][-1], paras.pop(0)])
        previous = page
    return pages


def paragraphs_from_lines(lines):
    """Prose paragraphs from OCR lines: consecutive prose-looking lines form a paragraph."""
    out, cur = [], []
    for line in lines:
        line = norm(line)
        looks_prose = len(line.split()) >= 4 and not re.match(r"^\s*(Table|Figure)\s+\S+\s*:", line)
        if looks_prose:
            cur.append(line)
        else:
            if cur:
                out.append(join_lines(cur))
            cur = []
    if cur:
        out.append(join_lines(cur))
    return [p for p in out if _is_prose(p)]


def is_caption(sentence, number, title):
    """The table's own caption ("Table A8-5a Bills and Statements Received...") isn't discussion."""
    key = lambda text: re.sub(r"\W", "", text.lower())
    if len(key(title)) < 8:
        return False  # too little title to tell a caption from "Table 2.1 shows..."
    return key(sentence).startswith(key(f"{number} {title}")[:30])


def excerpts(report_paragraphs, number, table_page, title="", limit=3):
    """[(page, text)] of sentences mentioning `number`, nearest pages first.

    `report_paragraphs` maps page -> list of paragraph strings. A sentence that is only a lead-in
    (short, or ending in a colon) brings the following sentence with it.
    """
    found = []
    for page, paras in report_paragraphs.items():
        for para in paras:
            sents = sentences(para)
            for i, s in enumerate(sents):
                if mentions(s, number) and not is_caption(s, number, title):
                    text = s
                    if (len(s) < 60 or s.rstrip().endswith(":")) and i + 1 < len(sents):
                        text = f"{s} {sents[i + 1]}"
                    found.append((page, text))
    seen, unique = set(), []
    for page, text in sorted(found, key=lambda pt: (abs(pt[0] - table_page), pt[0])):
        key = re.sub(r"\W", "", text.lower())
        if key not in seen:
            seen.add(key)
            unique.append((page, text))
    return unique[:limit]
