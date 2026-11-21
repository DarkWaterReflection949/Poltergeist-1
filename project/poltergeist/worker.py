# AI disclosure (CS50 final project policy): first draft generated with Claude (Anthropic).
# Replace this note with a description of what YOU changed or wrote.
"""Runs the user's pipeline in a separate process and reports one JSON line per test case.

SECURITY NOTE: this is defence in depth, NOT a security boundary. It blocks the usual
accidents (file/network/process access via imports, open(), eval/exec) and caps CPU/memory
on Linux/macOS, but a determined attacker can escape a Python-level sandbox.
Only haunt code you wrote or trust, and keep the web app on 127.0.0.1.
"""
import builtins
import csv
import io
import json
import sys

SAFE_MODULES = {
    "re", "csv", "io", "json", "datetime", "decimal", "unicodedata", "math", "collections",
    "itertools", "functools", "typing", "string", "statistics", "dataclasses", "fractions",
    "operator", "enum", "copy", "html", "calendar", "textwrap", "zoneinfo", "__future__",
    "poltergeist",
    # C-level helpers that allowed modules import on the pipeline's behalf (e.g. strptime)
    "_strptime", "_datetime", "_pydatetime", "_decimal", "_pydecimal", "_zoneinfo", "_json", "_csv",
}
REMOVED_BUILTINS = {"open", "exec", "eval", "compile", "input", "breakpoint", "exit", "quit", "help"}


def _limit():
    try:  # Linux/macOS only
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    except Exception:
        pass


def main():
    payload = json.loads(sys.stdin.read())
    out, sys.stdout = sys.stdout, sys.stderr  # pipeline print() must not corrupt our protocol

    def emit(obj):
        out.write(json.dumps(obj, default=str, ensure_ascii=False) + "\n")
        out.flush()

    allow = SAFE_MODULES | {m.strip() for m in payload["allow"].split(",") if m.strip()}
    _limit()
    real_import = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if globals is not None and globals.get("__name__") == "pipeline_user":
            if level or name.split(".")[0] not in allow:
                raise ImportError(f"'{name}' is not allowed in Poltergeist's sandbox")
        return real_import(name, globals, locals, fromlist, level)

    safe = {k: v for k, v in vars(builtins).items() if k not in REMOVED_BUILTINS}
    safe["__import__"] = guarded
    ns = {"__name__": "pipeline_user", "__builtins__": safe}
    try:
        exec(compile(payload["src"], "pipeline.py", "exec"), ns)
        clean = ns.get("clean")
        if not callable(clean):
            raise TypeError("your pipeline file must define a function clean(rows)")
    except BaseException as e:
        emit({"fatal": f"{type(e).__name__}: {e}"})
        return 2

    for case in payload["cases"]:
        try:
            rows = list(csv.DictReader(io.StringIO(case["csv"])))
            res = clean(rows)
            good, rejected = res if isinstance(res, tuple) and len(res) == 2 else (res, [])
            good, rejected = list(good), list(rejected)
            if not all(isinstance(r, dict) for r in good):
                raise TypeError("clean(rows) must return a list of dicts (or a (good, rejected) tuple)")
            emit({"name": case["name"], "status": "ok", "good": good, "rejected": rejected})
        except Exception as e:
            is_dq = any(c.__name__ == "DataQualityError" for c in type(e).__mro__)
            emit({"name": case["name"], "status": "error", "exc_type": type(e).__name__,
                  "is_dq": is_dq, "message": str(e)[:300]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
