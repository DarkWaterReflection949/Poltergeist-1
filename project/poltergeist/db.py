#(CS50 final project policy).
# Replace this note with a description of what YOU changed or wrote.
"""SQLite history: every haunting is stored so you can watch a pipeline get sturdier."""
import datetime
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    csv_name TEXT NOT NULL,
    seed INTEGER NOT NULL,
    rate REAL NOT NULL,
    applied INTEGER NOT NULL,
    silent INTEGER NOT NULL,
    silent_rate REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    mutator TEXT NOT NULL,
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    touched INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    detail TEXT NOT NULL,
    hint TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
"""


def connect():
    conn = sqlite3.connect(os.environ.get("POLTERGEIST_DB", os.path.join(ROOT, "poltergeist.db")))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_run(summary):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs (created_at, pipeline, csv_name, seed, rate, applied, silent, silent_rate) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(timespec="seconds"), summary["pipeline"], summary["csv_name"],
             summary["seed"], summary["rate"], summary["applied"], summary["silent"], summary["silent_rate"]))
        run_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO results (run_id, mutator, kind, description, touched, verdict, detail, hint) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(run_id, r["mutator"], r["kind"], r["desc"], r["touched"], r["verdict"], r["detail"], r["hint"])
             for r in summary["results"]])
    return run_id


def get_run(run_id):
    with connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return None, []
        rows = conn.execute("SELECT * FROM results WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
    return run, rows


def list_runs():
    with connect() as conn:
        return conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
