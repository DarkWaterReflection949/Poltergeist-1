# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Command-line Poltergeist.  Example:  python cli.py demos/demo_flawed.py demos/orders.csv"""
import argparse
import json
import os
import sys

from poltergeist import db, mutators
from poltergeist.engine import haunt
from poltergeist.sandbox import PipelineLoadError

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Haunt a data pipeline with realistic dirty data.")
    ap.add_argument("pipeline", nargs="?", default=os.path.join(HERE, "demos", "demo_flawed.py"),
                    help="Python file defining clean(rows)")
    ap.add_argument("csv", nargs="?", default=os.path.join(HERE, "demos", "orders.csv"), help="clean sample CSV")
    ap.add_argument("--seed", type=int, default=1, help="same seed = same haunting (default 1)")
    ap.add_argument("--rate", type=float, default=0.3, help="share of rows to corrupt, 0.05-0.6 (default 0.3)")
    ap.add_argument("--only", help="comma-separated mutator names")
    ap.add_argument("--save", action="store_true", help="store this run in the SQLite history")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    ap.add_argument("--max-silent", type=float, help="exit 1 if the Silent Corruption Rate (0-1) exceeds this")
    ap.add_argument("--list", action="store_true", help="list the mutators and exit")
    args = ap.parse_args()

    if args.list:
        for m in mutators.REGISTRY:
            print(f"{m.name:22} {m.kind:8} {m.desc}")
        return 0
    try:
        with open(args.pipeline, encoding="utf-8") as f:
            src = f.read()
        with open(args.csv, encoding="utf-8", newline="") as f:
            text = f.read()
        summary = haunt(src, text, pipeline_name=os.path.basename(args.pipeline),
                        csv_name=os.path.basename(args.csv), seed=args.seed,
                        rate=min(max(args.rate, 0.05), 0.6),
                        only=set(args.only.split(",")) if args.only else None)
    except (OSError, ValueError, PipelineLoadError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.save:
        summary["run_id"] = db.save_run(summary)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"\nHaunting {summary['pipeline']} with {summary['csv_name']} (seed {args.seed}, rate {args.rate})\n")
        for r in summary["results"]:
            print(f"  {r['mutator']:22} {r['kind']:8} {r['verdict']:14} {r['detail'][:70]}")
        c = summary["counts"]
        print(f"\n  absorbed {c['absorbed']} | quarantined {c['quarantined']} | caught loudly {c['caught_loudly']} "
              f"| crashed {c['crashed']} | silently wrong {c['silent_wrong']}")
        print(f"  Silent Corruption Rate: {summary['silent_rate']:.0%} "
              f"({summary['silent']} of {summary['applied']} mutations got through unnoticed)\n")
        if "run_id" in summary:
            print(f"  saved as run #{summary['run_id']}\n")
    if args.max_silent is not None and summary["silent_rate"] > args.max_silent:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
