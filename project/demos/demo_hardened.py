"""The same pipeline after listening to Poltergeist: validate, normalise, quarantine, fail loudly."""
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from poltergeist import DataQualityError

IST = timezone(timedelta(hours=5, minutes=30))
COLUMNS = ["order_id", "customer_id", "customer", "email", "phone", "city", "order_date", "amount", "quantity"]
ORDER_ID = re.compile(r"^ORD-\d{4}$")
CUSTOMER_ID = re.compile(r"^\d{5}$")
PHONE = re.compile(r"^[6-9]\d{9}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
CITY = re.compile(r"^[A-Za-z ]+$")


def _text(s):
    return " ".join(unicodedata.normalize("NFKC", s).split())


def _looks_mojibake(s):
    try:
        return s.encode("latin-1").decode("utf-8") != s
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


def _money(s):
    s = s.replace("\u20b9", "").replace("Rs.", "").replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d{1,2})?", s):
        raise ValueError(f"bad amount {s!r}")
    return float(s)


def _date(s):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T[\d:]+(Z|[+-]\d{2}:\d{2})", s):
        stamp = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return stamp.astimezone(IST).date().isoformat()       # business timezone, then the date
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        a, b, year = int(m[1]), int(m[2]), int(m[3])
        if a == b:
            return date(year, a, b).isoformat()
        if a > 12 >= b:
            return date(year, b, a).isoformat()
        if b > 12 >= a:
            return date(year, a, b).isoformat()
        raise ValueError(f"ambiguous date {s!r} (day/month or month/day?)")
    raise ValueError(f"bad date {s!r}")


def _row(r):
    if _looks_mojibake(r["customer"].strip()):   # check BEFORE NFKC: it rewrites characters like U+00AF
        raise ValueError(f"mojibake in customer {r['customer']!r}")
    row = {
        "order_id": _text(r["order_id"]),
        "customer_id": _text(r["customer_id"]),
        "customer": _text(r["customer"]),
        "email": _text(r["email"]).lower(),
        "phone": _text(r["phone"]),
        "city": _text(r["city"]),
    }
    for key, pattern in (("order_id", ORDER_ID), ("customer_id", CUSTOMER_ID), ("phone", PHONE),
                         ("email", EMAIL), ("city", CITY)):
        if not pattern.match(row[key]):
            raise ValueError(f"bad {key} {row[key]!r}")
    row["city"] = row["city"].title()
    row["order_date"] = _date(_text(r["order_date"]))
    row["amount"] = _money(_text(r["amount"]))
    quantity = _text(r["quantity"])
    if not re.fullmatch(r"\d+", quantity):
        raise ValueError(f"bad quantity {quantity!r}")
    row["quantity"] = int(quantity)
    return row


def clean(rows):
    if not rows:
        raise DataQualityError("no rows to process")
    missing = [c for c in COLUMNS if c not in rows[0]]
    if missing:
        raise DataQualityError(f"missing expected columns: {missing}")
    good, rejected, seen = [], [], {}
    for r in rows:
        try:
            row = _row(r)
        except (ValueError, KeyError) as e:
            rejected.append({"row": r, "reason": str(e)})
            continue
        fingerprint = {k: str(v).casefold() for k, v in row.items()}
        if row["order_id"] in seen:
            if seen[row["order_id"]] != fingerprint:
                rejected.append({"row": r, "reason": "conflicting duplicate order_id"})
            continue                                          # exact duplicate: drop quietly
        seen[row["order_id"]] = fingerprint
        good.append(row)
    if len(rejected) > len(rows) / 2:
        raise DataQualityError(f"{len(rejected)} of {len(rows)} rows rejected; refusing to continue")
    return good, rejected
