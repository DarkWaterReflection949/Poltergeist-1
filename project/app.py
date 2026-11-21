# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Poltergeist web app.  Run:  flask --app app run   (then open http://127.0.0.1:5000)"""
import os

from flask import Flask, abort, redirect, render_template, request, url_for

from poltergeist import db
from poltergeist.engine import BADNESS, VERDICTS, haunt
from poltergeist.sandbox import PipelineLoadError

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(HERE, "demos")
DEMOS = {"demo_flawed.py": "A pipeline that passes its own tests",
         "demo_hardened.py": "The same pipeline, hardened"}
VERDICT_LABELS = {"absorbed": "Absorbed", "quarantined": "Quarantined", "caught_loudly": "Caught loudly",
                  "crashed": "Crashed", "silent_wrong": "Silently wrong"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # 1 MB uploads


@app.context_processor
def helpers():
    return {"labels": VERDICT_LABELS, "verdicts": VERDICTS}


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


@app.get("/")
def index():
    return render_template("index.html", demos=DEMOS, error=None)


@app.post("/run")
def run():
    try:
        seed = int(request.form.get("seed", 1))
        rate = min(max(float(request.form.get("rate", 0.3)), 0.05), 0.6)
        choice = request.form.get("pipeline", "demo_flawed.py")
        if choice in DEMOS:
            src, name = _read(os.path.join(DEMO_DIR, choice)), choice
        else:
            upload = request.files.get("pipeline_file")
            if not upload or not upload.filename.endswith(".py"):
                raise ValueError("Choose a .py file that defines clean(rows).")
            src, name = upload.read().decode("utf-8"), os.path.basename(upload.filename)
        data = request.files.get("csv_file")
        if data and data.filename:
            text, csv_name = data.read().decode("utf-8-sig"), os.path.basename(data.filename)
        else:
            text, csv_name = _read(os.path.join(DEMO_DIR, "orders.csv")), "orders.csv"
        summary = haunt(src, text, pipeline_name=name, csv_name=csv_name, seed=seed, rate=rate)
    except (ValueError, UnicodeDecodeError, PipelineLoadError) as e:
        return render_template("index.html", demos=DEMOS, error=str(e)), 400
    return redirect(url_for("show_run", run_id=db.save_run(summary)))


@app.get("/run/<int:run_id>")
def show_run(run_id):
    run, results = db.get_run(run_id)
    if run is None:
        abort(404)
    counts = {v: sum(1 for r in results if r["verdict"] == v) for v in VERDICTS}
    return render_template("run.html", run=run, results=results, counts=counts)


@app.get("/history")
def history():
    return render_template("history.html", runs=db.list_runs())


@app.get("/compare")
def compare():
    try:
        a, b = int(request.args["a"]), int(request.args["b"])
    except (KeyError, ValueError):
        return redirect(url_for("history"))
    (run_a, res_a), (run_b, res_b) = db.get_run(a), db.get_run(b)
    if run_a is None or run_b is None:
        abort(404)
    before = {r["mutator"]: r for r in res_a}
    after = {r["mutator"]: r for r in res_b}
    rows = []
    for name in list(before) + [n for n in after if n not in before]:
        va = before[name]["verdict"] if name in before else None
        vb = after[name]["verdict"] if name in after else None
        if va and vb:
            change = "fixed" if BADNESS[vb] < BADNESS[va] else "regressed" if BADNESS[vb] > BADNESS[va] else "same"
        else:
            change = "n/a"
        rows.append({"mutator": name, "a": va, "b": vb, "change": change})
    return render_template("compare.html", run_a=run_a, run_b=run_b, rows=rows)


@app.errorhandler(404)
def not_found(_):
    return render_template("index.html", demos=DEMOS, error="That page or run does not exist."), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
