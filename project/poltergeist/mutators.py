# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Mutators: each one injects ONE kind of realistic corruption into clean rows.

kind == "benign":  a careful pipeline should absorb it (same output as the clean run).
kind == "harmful": a careful pipeline should reject / flag the affected rows,
                   or recover the exact original value. Silent wrong output is the bug.
"""
import copy
import random
import re
from datetime import datetime, timedelta, timezone

from .schema import ISO

IST = timezone(timedelta(hours=5, minutes=30))
NULLS = ["", "N/A", "NA", "null", "-", "None", "NULL", "n/a", "--", "#N/A"]
LOOKALIKES = {"a": "\u0430", "e": "\u0435", "o": "\u043e", "p": "\u0440", "c": "\u0441"}  # Cyrillic
FULLWIDTH = {ord(str(d)): ord(str(d)) + 0xFEE0 for d in range(10)}
REGISTRY = []


class Mutator:
    def __init__(self, name, kind, needs, desc, hint, fn):
        self.name, self.kind, self.needs = name, kind, needs
        self.desc, self.hint, self.fn = desc, hint, fn

    def apply(self, rows, schema, seed, rate):
        """Return (mutated copy, number of rows/cells touched). 0 means 'not applicable'."""
        rng = random.Random(f"{seed}:{self.name}")  # str seeds are deterministic
        if self.needs and not _cols(schema, *self.needs):
            return rows, 0
        return self.fn(copy.deepcopy(rows), schema, rng, rate)


def mutator(name, kind, needs, desc, hint):
    def deco(fn):
        REGISTRY.append(Mutator(name, kind, needs, desc, hint, fn))
        return fn
    return deco


def _cols(schema, *kinds):
    return [c for c, k in schema.items() if k in kinds]


def _pick(rows, rng, rate, ok=lambda r: True):
    idx = [i for i, r in enumerate(rows) if ok(r)]
    if not idx:
        return []
    return rng.sample(idx, min(len(idx), max(1, round(len(idx) * rate))))


def _num(v):
    try:
        return float(v)
    except ValueError:
        return -1.0


def _indian(n):
    whole, frac = f"{n:.2f}".split(".")
    if len(whole) > 3:
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", whole[:-3])
        whole = head + "," + whole[-3:]
    return f"{whole}.{frac}"


def _pad(rows, rng, rate, pad):
    idx = _pick(rows, rng, rate)
    for i in idx:
        for c in rows[i]:
            rows[i][c] = pad() + rows[i][c] + pad()
    return rows, len(idx)


# ---------------------------------------------------------------- benign ---

@mutator("whitespace_padding", "benign", (), "Spaces around cell values",
         "Strip every text cell before comparing or storing it.")
def whitespace_padding(rows, schema, rng, rate):
    return _pad(rows, rng, rate, lambda: " " * rng.randint(1, 3))


@mutator("nbsp_padding", "benign", (), "Non-breaking spaces around cell values",
         "Use str.strip() (it removes U+00A0) or normalise with unicodedata NFKC first.")
def nbsp_padding(rows, schema, rng, rate):
    return _pad(rows, rng, rate, lambda: "\u00a0" * rng.randint(1, 2))


@mutator("case_noise", "benign", ("email", "category"), "UPPER / lower / sWAP case in emails and categories",
         "Normalise case (lower() for emails, title() or casefold() for categories).")
def case_noise(rows, schema, rng, rate):
    cols = _cols(schema, "email", "category")
    idx = _pick(rows, rng, rate)
    for i in idx:
        for c in cols:
            rows[i][c] = rng.choice([str.upper, str.lower, str.swapcase])(rows[i][c])
    return rows, len(idx)


@mutator("fullwidth_digits", "benign", ("money", "int", "phone", "date", "id"),
         "Full-width digits (\uff11\uff12\uff13) from East-Asian keyboards",
         "Run unicodedata.normalize('NFKC', value) on every cell before parsing or comparing.")
def fullwidth_digits(rows, schema, rng, rate):
    cols = _cols(schema, "money", "int", "phone", "date", "id")
    idx = _pick(rows, rng, rate)
    for i in idx:
        for c in cols:
            rows[i][c] = rows[i][c].translate(FULLWIDTH)
    return rows, len(idx)


@mutator("thousands_commas", "benign", ("money",), "Western thousands separators: 1,299.50",
         "Remove separators with replace(',', '') before float(), and validate the result.")
def thousands_commas(rows, schema, rng, rate):
    cols = _cols(schema, "money")
    idx = _pick(rows, rng, rate, lambda r: any(_num(r[c]) >= 1000 for c in cols))
    for i in idx:
        for c in cols:
            if _num(rows[i][c]) >= 1000:
                rows[i][c] = f"{_num(rows[i][c]):,.2f}"
    return rows, len(idx)


@mutator("indian_currency", "benign", ("money",), "\u20b9, Rs. and lakh/crore grouping: \u20b912,34,567.00",
         "Strip currency symbols and ALL commas before parsing (Indian grouping is not every 3 digits).")
def indian_currency(rows, schema, rng, rate):
    cols = _cols(schema, "money")
    idx = _pick(rows, rng, rate)
    styles = [lambda v: "\u20b9" + _indian(v), lambda v: "Rs. " + f"{v:.2f}", _indian]
    for i in idx:
        for c in cols:
            if _num(rows[i][c]) >= 0:
                rows[i][c] = rng.choice(styles)(_num(rows[i][c]))
    return rows, len(idx)


# --------------------------------------------------------------- harmful ---

@mutator("null_spellings", "harmful", ("money", "int"), "Missing numbers spelled N/A, NA, null, -, empty ...",
         "Never turn a failed parse into 0. Reject the row or raise DataQualityError.")
def null_spellings(rows, schema, rng, rate):
    cols = _cols(schema, "money", "int")
    idx = _pick(rows, rng, rate)
    for i in idx:
        rows[i][rng.choice(cols)] = rng.choice(NULLS)
    return rows, len(idx)


def _ambiguous(v):
    m = ISO.match(v)
    return bool(m) and int(m[3]) <= 12 and int(m[3]) != int(m[2])


@mutator("date_ambiguity", "harmful", ("date",), "2026-05-04 becomes 04/05/2026 (4 May or 5 April?)",
         "Accept one explicit date format. Reject slash dates where day and month are both <= 12.")
def date_ambiguity(rows, schema, rng, rate):
    cols = _cols(schema, "date")
    idx = _pick(rows, rng, rate, lambda r: any(_ambiguous(r[c]) for c in cols))
    for i in idx:
        for c in cols:
            if _ambiguous(rows[i][c]):
                y, m, d = ISO.match(rows[i][c]).groups()
                rows[i][c] = f"{d}/{m}/{y}"
    return rows, len(idx)


@mutator("timezone_shift", "harmful", ("date",), "Local midnight exported as UTC, so the date moves back a day",
         "Parse the full timestamp with its offset, convert to the business timezone, THEN take the date.")
def timezone_shift(rows, schema, rng, rate):
    cols = _cols(schema, "date")
    idx = _pick(rows, rng, rate, lambda r: any(ISO.match(r[c]) for c in cols))
    for i in idx:
        for c in cols:
            m = ISO.match(rows[i][c])
            if m:
                dt = datetime(*map(int, m.groups()), tzinfo=IST).astimezone(timezone.utc)
                rows[i][c] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return rows, len(idx)


@mutator("duplicate_rows", "harmful", (), "Near-duplicate rows (different case or trailing space)",
         "De-duplicate on a normalised business key (e.g. order_id) and reject conflicting duplicates.")
def duplicate_rows(rows, schema, rng, rate):
    dupes = set(_pick(rows, rng, min(rate, 0.15)))
    cols = _cols(schema, "email", "category", "text")
    out = []
    for i, r in enumerate(rows):
        out.append(r)
        if i in dupes:
            v = dict(r)
            for c in cols:
                v[c] = rng.choice([str.upper, str.lower, lambda s: s + " "])(v[c])
            out.append(v)
    return out, len(dupes)


@mutator("homoglyph", "harmful", ("category",), "A Latin letter swapped for an identical-looking Cyrillic one",
         "Validate text fields against an allowed alphabet (e.g. ^[A-Za-z ]+$) or reject mixed scripts.")
def homoglyph(rows, schema, rng, rate):
    cols = _cols(schema, "category")
    has = lambda r: [c for c in cols if any(ch in r[c] for ch in LOOKALIKES)]
    idx = _pick(rows, rng, rate, lambda r: bool(has(r)))
    for i in idx:
        c = rng.choice(has(rows[i]))
        ch = rng.choice([x for x in LOOKALIKES if x in rows[i][c]])
        rows[i][c] = rows[i][c].replace(ch, LOOKALIKES[ch], 1)
    return rows, len(idx)


@mutator("mojibake", "harmful", ("text",), "Accents corrupted by a wrong encoding (Ren\u00e9e becomes Ren\u00c3\u00a9e)",
         "Detect it: value.encode('latin-1').decode('utf-8') succeeding and changing the text is a tell.")
def mojibake(rows, schema, rng, rate):
    cols = _cols(schema, "text")
    idx = [i for i, r in enumerate(rows) if any(not r[c].isascii() for c in cols)]
    for i in idx:
        for c in cols:
            if not rows[i][c].isascii():
                rows[i][c] = rows[i][c].encode("utf-8").decode("latin-1")
    return rows, len(idx)


@mutator("leading_zero_loss", "harmful", ("id",), "ID 00123 becomes 123 (a spreadsheet ate the zeros)",
         "Treat IDs as strings and validate their exact shape, e.g. ^\\d{5}$.")
def leading_zero_loss(rows, schema, rng, rate):
    cols = _cols(schema, "id")
    idx = _pick(rows, rng, rate, lambda r: any(re.fullmatch(r"0\d+", r[c]) for c in cols))
    for i in idx:
        for c in cols:
            if re.fullmatch(r"0\d+", rows[i][c]):
                rows[i][c] = rows[i][c].lstrip("0") or "0"
    return rows, len(idx)


@mutator("scientific_notation", "harmful", ("phone",), "Phone 9876543210 becomes 9.88E+09",
         "Validate phone numbers with a strict pattern such as ^[6-9]\\d{9}$ and reject the rest.")
def scientific_notation(rows, schema, rng, rate):
    cols = _cols(schema, "phone")
    idx = _pick(rows, rng, rate, lambda r: any(re.fullmatch(r"\d{10,}", r[c]) for c in cols))
    for i in idx:
        for c in cols:
            if re.fullmatch(r"\d{10,}", rows[i][c]):
                rows[i][c] = f"{int(rows[i][c]):.2E}"
    return rows, len(idx)


@mutator("extra_header_row", "harmful", (), "A header row repeated in the middle (two exports pasted together)",
         "Validate every row's shape (IDs, dates, numbers) so a stray header is rejected, not parsed.")
def extra_header_row(rows, schema, rng, rate):
    header = {c: c for c in rows[0]}
    n = min(max(1, round(len(rows) * rate / 10)), len(rows) - 1)
    if n < 1:
        return rows, 0
    for p in sorted(rng.sample(range(1, len(rows)), n), reverse=True):
        rows.insert(p, dict(header))
    return rows, n


@mutator("swapped_columns", "harmful", ("money",), "Amount and quantity values swapped in some rows",
         "Check each numeric column's range and type (quantity must be a whole number).")
def swapped_columns(rows, schema, rng, rate):
    money, ints = _cols(schema, "money"), _cols(schema, "int")
    if not (money and ints):
        return rows, 0
    a, b = money[0], ints[0]
    idx = _pick(rows, rng, rate)
    for i in idx:
        rows[i][a], rows[i][b] = rows[i][b], rows[i][a]
    return rows, len(idx)


@mutator("column_drift", "harmful", ("money",), "A column header renamed upstream (amount becomes Amount (INR))",
         "Compare the header to the expected columns and raise DataQualityError listing what is missing.")
def column_drift(rows, schema, rng, rate):
    col = _cols(schema, "money")[0]
    new = col.title() + " (INR)"
    return [{(new if k == col else k): v for k, v in r.items()} for r in rows], len(rows)


def by_name(name):
    return next(m for m in REGISTRY if m.name == name)
