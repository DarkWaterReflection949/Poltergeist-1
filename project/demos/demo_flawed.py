"""A pipeline that looks fine, passes its own tests, and silently corrupts real-world data."""
from datetime import datetime


def _date(s):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):              # BUG: guesses US month/day order
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()   # BUG: drops the timezone
        except ValueError:
            pass
    raise ValueError(f"bad date {s!r}")


def _num(s, cast):
    try:
        return cast(s.replace(",", "").replace("\u20b9", "").replace("Rs.", "").strip())
    except ValueError:
        return cast(0)                                  # BUG: junk silently becomes zero


def clean(rows):
    return [{
        "order_id": r["order_id"].strip(),
        "customer_id": r["customer_id"].strip(),
        "customer": r["customer"].strip(),
        "email": r["email"].strip().lower(),
        "phone": r["phone"].strip(),
        "city": r["city"].strip().title(),
        "order_date": _date(r["order_date"]),
        "amount": _num(r["amount"], float),
        "quantity": _num(r["quantity"], int),
    } for r in rows]                                    # BUG: no de-duplication, no validation
