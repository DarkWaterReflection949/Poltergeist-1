# Project analysis

## 1. What the application does

Poltergeist is a testing tool for CSV cleaning functions. It starts with a clean CSV, infers basic column types, creates altered copies of the input, and executes a user-supplied `clean(rows)` function against each copy. The engine compares each result with the clean-data result and classifies the outcome.

The goal is not simply to count exceptions. It is to identify transformations that complete successfully while returning incorrect data.

## 2. Folder and file responsibilities

### Root files

- `app.py`: Flask entry point. It defines the home page, run submission, result page, history page, and run comparison routes. It accepts pipeline and CSV uploads and delegates execution to the engine.
- `cli.py`: command-line entry point. It accepts pipeline and CSV paths, seed/rate controls, optional mutator selection, JSON output, persistence, and a silent-rate threshold.
- `requirements.txt`: declares Flask as the only third-party runtime dependency.
- `test_poltergeist.py`: unit and integration tests for schema inference, mutation behavior, judging, end-to-end runs, and worker restrictions.
- `.gitignore`: excludes Python cache files, the SQLite database, and virtual environments.

### `poltergeist/`

- `__init__.py`: exposes the package's public `DataQualityError` exception.
- `schema.py`: infers a simple type for each CSV column using column names and sample values. Types include email, date, phone, id, money, integer, category, and text.
- `mutators.py`: defines the mutation registry and the 17 corruption strategies. Each strategy receives the original rows, inferred schema, seeded random generator, and mutation rate.
- `engine.py`: parses CSV input, creates mutation cases, calls the worker, compares output with the clean baseline, and computes verdict counts and the silent-corruption rate.
- `sandbox.py`: starts the worker subprocess, passes the cases as JSON, enforces a timeout, and collects worker responses.
- `worker.py`: loads the supplied `clean(rows)` function, applies restricted built-ins/import handling, runs each case, and emits JSON results.
- `db.py`: creates and accesses the SQLite `runs` and `results` tables used by web history and comparisons.

### User interface and examples

- `templates/`: Jinja templates for the shared page layout, home form, individual run report, run history, and run comparison.
- `static/style.css`: styles the Flask interface.
- `demos/orders.csv`: synthetic sample order data.
- `demos/demo_flawed.py`: intentionally weak cleaning logic used to demonstrate silent corruption.
- `demos/demo_hardened.py`: defensive example that validates and quarantines problematic rows.
- `demos/test_demo_flawed.py`: a deliberately limited test demonstrating that clean-data tests can pass while dirty-data behavior remains unsafe.
- `demos/make_orders.py`: helper for generating the sample orders dataset.
- `docs/VIDEO_SCRIPT.md`: suggested outline for the short project demonstration.

## 3. Mutation design

The registry contains 17 mutations:

**Benign formatting changes (6):** whitespace padding, non-breaking-space padding, case changes, full-width digits, Western thousands separators, and Indian currency/grouping formats.

**Harmful data changes (11):** alternate null spellings, ambiguous dates, timezone shifts, duplicate rows, Unicode homoglyphs, mojibake, leading-zero loss, scientific-notation phone values, repeated header rows, swapped columns, and column-name drift.

The distinction is important: a robust cleaner should generally normalize benign representation changes, while harmful changes should be rejected, reported, or safely corrected without silently changing meaning.

## 4. Verdict and metric logic

The engine compares each case to the output produced from the clean CSV. It classifies results as:

1. `absorbed`: output is identical to the clean baseline.
2. `quarantined`: rejected rows are reported and surviving output is correct.
3. `caught_loudly`: the pipeline raises the project's `DataQualityError`.
4. `crashed`: an unexpected error or timeout occurs.
5. `silent_wrong`: execution completes but the output differs from the clean baseline.

The silent-corruption rate is the count of `silent_wrong` outcomes divided by the number of applied mutations. Mutations that did not touch any sample rows are listed as skipped and excluded from the denominator.

## 5. Verification performed on the supplied archive

The following checks were run against the original extracted project:

- `python -m unittest -v`: **21 tests passed**.
- `python -m compileall -q .`: completed successfully.
- `python cli.py --list`: listed all 17 registered mutators.
- Flawed sample pipeline, seed `1`, rate `0.3`: **9 silent-wrong outcomes out of 17 applied mutations**, giving **53%**.
- Hardened sample pipeline, seed `1`, rate `0.3`: **0 silent-wrong outcomes out of 17 applied mutations**, giving **0%**.

These results describe the supplied sample data and default run settings. They are not a guarantee for every CSV or every user pipeline.

## 6. Important limitations and review notes

- **Sandbox is not a security boundary.** The worker's import and built-in restrictions are useful guardrails, but Python-level restrictions can be bypassed. The source itself warns against running untrusted code and recommends localhost-only use.
- **Schema inference is heuristic.** It inspects column names and observed values. A small or unrepresentative CSV can lead to an incorrect inferred type.
- **Metamorphic comparison has assumptions.** The engine treats the clean run as the reference output. If the pipeline is already wrong on clean data, the engine cannot independently know the intended business answer; it only rejects pipelines that fail to run on the clean input.
- **Sample-dependent mutation coverage.** A mutation may be skipped when the sample has no eligible values. The number of applied mutations can therefore vary with the CSV and seed.
- **No license is supplied.** The repository should not imply an open-source license until the owner selects one.
- **Video URL is a placeholder in the original README.** Add the actual video URL before final CS50 submission if a video is required.
- **AI disclosure needs the owner's accurate contribution statement.** Several source files contain a CS50 AI-assistance note saying the first draft was generated with Claude. Do not replace that disclosure with a claim that is not true.

## 7. Overall assessment

The archive is a coherent, runnable Python project with a clear purpose, separated engine/UI/persistence responsibilities, two user interfaces, examples, and a meaningful test suite. Its strongest design decision is measuring silent incorrect output rather than treating every crash as the main failure. The main caution is the sandbox: this should be presented as a local testing aid for trusted code, not as a secure hosted execution service.
