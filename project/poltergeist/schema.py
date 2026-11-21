# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Guess what kind of data each column holds, so mutators know where to strike."""
import re

ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MONEY_NAMES = {"amount", "price", "total", "cost", "salary"}


def infer_schema(rows):
    """Return {column: kind}. Kinds: email, date, phone, id, money, int, category, text."""
    schema = {}
    for col in rows[0]:
        vals = [r[col] for r in rows if r[col] != ""]
        low = col.lower()
        if vals and all("@" in v for v in vals):
            kind = "email"
        elif vals and all(ISO.match(v) for v in vals):
            kind = "date"
        elif "phone" in low or "mobile" in low:
            kind = "phone"
        elif low.endswith("id"):
            kind = "id"
        elif low in MONEY_NAMES:
            kind = "money"
        elif vals and all(re.fullmatch(r"\d+", v) for v in vals):
            kind = "int"
        elif vals and all(re.fullmatch(r"-?\d+(\.\d+)?", v) for v in vals):
            kind = "money"
        elif len(set(vals)) <= max(2, len(vals) // 3):
            kind = "category"
        else:
            kind = "text"
        schema[col] = kind
    return schema
