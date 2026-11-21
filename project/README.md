# Poltergeist

**Chaos testing for Python data-cleaning pipelines.** Poltergeist deliberately introduces realistic data problems into a clean CSV, runs your `clean(rows)` function against each mutated copy, and measures how often bad data produces an incorrect result without raising an error.

> The headline metric is the **Silent Corruption Rate**: the percentage of applied mutations that pass through your pipeline and produce output that differs from the clean-data baseline.

## Why this project exists

A pipeline that crashes on malformed input is inconvenient, but a pipeline that quietly returns incorrect data is much harder to detect. Common examples include ambiguous dates, missing values represented as `N/A`, phone numbers converted to scientific notation, lost leading zeros, duplicate rows, and renamed columns.

Ordinary tests often use clean fixtures and miss these cases. Poltergeist tests the same cleaning function against 17 repeatable corruption scenarios.

## Features

- **17 data mutations:** 6 benign formatting variations and 11 harmful data-quality changes.
- **Repeatable runs:** a seed makes a run reproducible.
- **Metamorphic comparison:** each mutated result is compared with the pipeline's output on the original CSV, so expected outputs do not need to be hand-written.
- **Five verdicts:** `absorbed`, `quarantined`, `caught_loudly`, `crashed`, and `silent_wrong`.
- **Two interfaces:** a Flask web interface and a command-line interface.
- **Run history:** SQLite stores results and supports before/after comparisons.
- **CI-friendly exit status:** `--max-silent` can fail a command when the silent corruption rate exceeds a threshold.
- **Subprocess isolation:** the pipeline runs in a separate worker process with restricted imports, selected built-ins removed, a timeout, and resource limits where supported.

## Project structure

```text
.
├── app.py                    # Flask web application and routes
├── cli.py                    # Command-line interface
├── requirements.txt          # Runtime dependency (Flask)
├── test_poltergeist.py       # 21 unit and integration tests
├── demos/
│   ├── orders.csv            # Synthetic sample orders
│   ├── demo_flawed.py        # Example pipeline with silent data bugs
│   ├── demo_hardened.py      # Defensive version of the example pipeline
│   ├── test_demo_flawed.py   # Demonstrates why clean-only tests are insufficient
│   └── make_orders.py        # Regenerates sample data
├── docs/
│   ├── PROJECT_ANALYSIS.md   # Architecture, verification, and limitations
│   └── VIDEO_SCRIPT.md       # Suggested CS50 project video outline
├── poltergeist/
│   ├── __init__.py           # Public package exports
│   ├── schema.py             # Infers column data types
│   ├── mutators.py           # Registry of corruption strategies
│   ├── engine.py             # Runs cases and judges outcomes
│   ├── sandbox.py            # Parent process / worker orchestration
│   ├── worker.py              # Executes the pipeline in a child process
│   └── db.py                 # SQLite run-history persistence
├── static/
│   └── style.css             # Web interface styling
└── templates/                # Jinja templates for the Flask pages
```

## Requirements

- Python 3.10 or newer
- pip
- Flask (installed from `requirements.txt`)

## Installation

```bash
git clone https://github.com/YOUR-USERNAME/poltergeist.git
cd poltergeist

python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the command-line version

List the available mutations:

```bash
python cli.py --list
```

Run the deliberately flawed example:

```bash
python cli.py demos/demo_flawed.py demos/orders.csv
```

Run the hardened example:

```bash
python cli.py demos/demo_hardened.py demos/orders.csv
```

Use JSON output, save a run to SQLite, or set a CI threshold:

```bash
python cli.py demos/demo_hardened.py demos/orders.csv --json
python cli.py demos/demo_hardened.py demos/orders.csv --save
python cli.py demos/demo_hardened.py demos/orders.csv --max-silent 0.10
```

Useful options:

| Option | Purpose |
|---|---|
| `--seed N` | Set the random seed (default: `1`) |
| `--rate N` | Set the mutation rate; clamped to `0.05` through `0.6` (default: `0.3`) |
| `--only a,b` | Run only the named mutators |
| `--save` | Save the run in the SQLite history database |
| `--json` | Print the complete result as JSON |
| `--max-silent N` | Exit with status `1` if the silent rate exceeds `N` |
| `--list` | List registered mutators and exit |

## Run the web application

Start the Flask development server:

```bash
flask --app app run
```

Open <http://127.0.0.1:5000>. The interface lets you run the bundled examples or upload a Python pipeline and CSV, inspect verdicts, view saved history, and compare runs.

The app binds to localhost when started through `app.py` directly. Do not expose this development application to the public internet.

## Use Poltergeist with your own pipeline

Create a Python file that defines `clean(rows)`. `rows` is a list of dictionaries whose values are CSV strings.

The function may return either:

```python
def clean(rows):
    # Validate and clean rows here.
    good_rows = []
    rejected_rows = []
    return good_rows, rejected_rows
```

Or simply return a list of cleaned dictionaries if no rows are rejected:

```python
def clean(rows):
    return rows
```

To deliberately report a data-quality failure, raise `poltergeist.DataQualityError`. Only modules in the worker's allow-list can be imported by default. Additional imports can be allowed with the `POLTERGEIST_ALLOW` environment variable, for example `POLTERGEIST_ALLOW=pandas`.

## Verdict meanings

| Verdict | Meaning |
|---|---|
| `absorbed` | Output matches the clean-data baseline. |
| `quarantined` | Bad rows were rejected and the surviving output is correct. |
| `caught_loudly` | The pipeline raised `DataQualityError`. |
| `crashed` | An unexpected exception or timeout stopped the case. |
| `silent_wrong` | The pipeline returned normally, but its output was incorrect or changed unexpectedly. |

The rate is calculated as `silent_wrong / applied mutations`. Mutations that do not affect the supplied sample are skipped and are not included in the denominator.

## Tests

Run the full test suite with the Python standard library:

```bash
python -m unittest discover -v
```

The test suite covers schema inference, mutation determinism, input immutability, verdict classification, end-to-end flawed and hardened examples, import restrictions, timeout handling, and environment-variable isolation.

## Security note

The worker process provides **defence in depth, not a secure sandbox**. Python-level restrictions are not a security boundary, and resource limits vary by operating system. Run only pipelines you wrote or trust. Keep the web app bound to `127.0.0.1`; do not use it as a public service for untrusted uploads.

## Project information

- **Video demonstration:** add your submitted video URL here when it is ready.
- **License:** no license file is included yet. Add a license only after choosing the terms under which you want others to use the project.
- **AI assistance disclosure:** the source files and original project description state that the first draft was generated with Claude (Anthropic). Keep this disclosure accurate and update it to describe your own contributions in line with your course's academic-integrity requirements.
