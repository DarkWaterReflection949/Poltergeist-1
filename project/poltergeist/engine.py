# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Haunt a pipeline and judge what happened.

Verdicts (best to worst):
  absorbed      output identical to the clean run
  quarantined   bad rows were rejected on purpose, and nothing corrupted got through
  caught_loudly the pipeline raised DataQualityError
  crashed       an unplanned exception (KeyError, ValueError ...), or a timeout
  silent_wrong  it returned normally, but the output differs from the clean run
"""
import csv
import io
import json
from collections import Counter

from . import mutators as M
from .sandbox import PipelineLoadError, run_cases
from .schema import infer_schema

VERDICTS = ["absorbed", "quarantined", "caught_loudly", "crashed", "silent_wrong"]
BADNESS = {v: i for i, v in enumerate(["absorbed", "quarantined", "caught_loudly", "crashed", "silent_wrong"])}


def parse_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("The CSV has no data rows.")
    return rows


def to_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def canon(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)


def judge(res, clean_good):
    """Return (verdict, detail) for one sandbox result, relative to the clean output."""
    if res["status"] == "error":
        if res.get("is_dq"):
            return "caught_loudly", res["message"]
        return "crashed", f"{res['exc_type']}: {res['message']}"
    good = [canon(r) for r in res["good"]]
    clean_set, rejected = set(clean_good), res["rejected"]
    if Counter(good) == Counter(clean_good):
        if rejected:
            return "quarantined", f"{len(rejected)} duplicate/bad row(s) rejected; output matches the clean run"
        return "absorbed", "output identical to the clean run"
    bad = [g for g in good if g not in clean_set]
    if rejected and not bad:
        return "quarantined", f"{len(rejected)} row(s) rejected; every row that got through is correct"
    if bad:
        return "silent_wrong", f"{len(bad)} output row(s) differ from the clean run, e.g. {bad[0][:150]}"
    return "silent_wrong", f"row count changed silently: {len(good)} vs {len(clean_good)} in the clean run"


def haunt(pipeline_src, csv_text, *, pipeline_name="pipeline.py", csv_name="data.csv",
          seed=1, rate=0.3, only=None, timeout=30):
    rows = parse_csv(csv_text)
    schema = infer_schema(rows)
    cases = [{"name": "clean", "csv": to_csv(rows)}]
    touched = {}
    for m in M.REGISTRY:
        if only and m.name not in only:
            continue
        mutated, n = m.apply(rows, schema, seed, rate)
        touched[m.name] = n
        if n:
            cases.append({"name": m.name, "csv": to_csv(mutated)})

    results = run_cases(pipeline_src, cases, timeout)
    clean = results["clean"]
    if clean["status"] != "ok":
        raise PipelineLoadError(
            f"Your pipeline already fails on the CLEAN data ({clean.get('exc_type')}: {clean.get('message')}). "
            "Fix that first, then haunt it.")
    clean_good = [canon(r) for r in clean["good"]]

    out, skipped = [], []
    for m in M.REGISTRY:
        if m.name not in touched:
            continue
        if not touched[m.name]:
            skipped.append(m.name)
            continue
        verdict, detail = judge(results[m.name], clean_good)
        out.append({"mutator": m.name, "kind": m.kind, "desc": m.desc, "touched": touched[m.name],
                    "verdict": verdict, "detail": detail,
                    "hint": m.hint if verdict in ("silent_wrong", "crashed") else ""})
    counts = {v: sum(1 for r in out if r["verdict"] == v) for v in VERDICTS}
    applied = len(out)
    return {"pipeline": pipeline_name, "csv_name": csv_name, "seed": seed, "rate": rate,
            "schema": schema, "results": out, "skipped": skipped, "applied": applied,
            "counts": counts, "silent": counts["silent_wrong"],
            "silent_rate": counts["silent_wrong"] / applied if applied else 0.0}
