#(CS50 final project policy).
# Replace this note with a description of what YOU changed or wrote.
"""Parent side of the sandbox: start the worker, feed it cases, collect results."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_ENV = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "LANG")


class PipelineLoadError(Exception):
    """The pipeline could not be loaded or run at all."""


def run_cases(src, cases, timeout=30):
    """Run pipeline source against every case; return {case_name: result dict}."""
    payload = json.dumps({"src": src, "cases": cases, "allow": os.environ.get("POLTERGEIST_ALLOW", "")})
    env = {k: v for k, v in os.environ.items() if k in KEEP_ENV}  # no API keys leak to user code
    env.update(PYTHONIOENCODING="utf-8", PYTHONPATH=ROOT)
    proc = subprocess.Popen([sys.executable, "-m", "poltergeist.worker"], cwd=ROOT, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8")
    timed_out = False
    try:
        stdout, stderr = proc.communicate(payload, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        timed_out = True

    results = {}
    for line in (stdout or "").splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if "fatal" in obj:
            raise PipelineLoadError(obj["fatal"])
        results[obj["name"]] = obj
    for case in cases:
        if case["name"] not in results:
            why = "Timeout" if timed_out else "WorkerDied"
            msg = f"no result within {timeout}s" if timed_out else (stderr or "")[-200:]
            results[case["name"]] = {"name": case["name"], "status": "error", "exc_type": why,
                                     "is_dq": False, "message": msg}
    return results
