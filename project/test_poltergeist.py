#(CS50 final project policy).
# Replace this note with a description of what YOU changed or wrote.
"""Run with:  python -m unittest -v"""
import os
import unittest

from poltergeist import mutators
from poltergeist.engine import canon, haunt, judge, parse_csv, to_csv
from poltergeist.sandbox import PipelineLoadError, run_cases
from poltergeist.schema import infer_schema

HERE = os.path.dirname(os.path.abspath(__file__))


def read(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8", newline="") as f:
        return f.read()


ORDERS = read("demos", "orders.csv")
FLAWED, HARDENED = read("demos", "demo_flawed.py"), read("demos", "demo_hardened.py")


class Schema(unittest.TestCase):
    def test_orders_columns_are_understood(self):
        s = infer_schema(parse_csv(ORDERS))
        self.assertEqual(s["order_id"], "id")
        self.assertEqual(s["customer_id"], "id")
        self.assertEqual(s["email"], "email")
        self.assertEqual(s["phone"], "phone")
        self.assertEqual(s["city"], "category")
        self.assertEqual(s["customer"], "text")
        self.assertEqual(s["order_date"], "date")
        self.assertEqual(s["amount"], "money")
        self.assertEqual(s["quantity"], "int")


class Mutators(unittest.TestCase):
    def setUp(self):
        self.rows = parse_csv(ORDERS)
        self.schema = infer_schema(self.rows)

    def test_same_seed_same_haunting(self):
        for m in mutators.REGISTRY:
            a, _ = m.apply(self.rows, self.schema, 5, 0.3)
            b, _ = m.apply(self.rows, self.schema, 5, 0.3)
            self.assertEqual(a, b, m.name)

    def test_different_seed_changes_something(self):
        m = mutators.by_name("null_spellings")
        self.assertNotEqual(m.apply(self.rows, self.schema, 1, 0.3)[0], m.apply(self.rows, self.schema, 2, 0.3)[0])

    def test_inputs_are_never_modified(self):
        before = to_csv(self.rows)
        for m in mutators.REGISTRY:
            m.apply(self.rows, self.schema, 1, 0.5)
        self.assertEqual(before, to_csv(self.rows))

    def test_every_mutator_touches_the_sample(self):
        for m in mutators.REGISTRY:
            self.assertGreater(m.apply(self.rows, self.schema, 1, 0.3)[1], 0, m.name)

    def test_indian_grouping(self):
        self.assertEqual(mutators._indian(1234567.5), "12,34,567.50")
        self.assertEqual(mutators._indian(999.0), "999.00")
        self.assertEqual(mutators._indian(12567.0), "12,567.00")

    def test_date_ambiguity_only_hits_truly_ambiguous_dates(self):
        out, n = mutators.by_name("date_ambiguity").apply(self.rows, self.schema, 1, 1.0)
        for old, new in zip(self.rows, out):
            if new["order_date"] != old["order_date"]:
                y, m, d = old["order_date"].split("-")
                self.assertTrue(int(d) <= 12 and d != m)
                self.assertEqual(new["order_date"], f"{d}/{m}/{y}")


class Judge(unittest.TestCase):
    clean = [canon({"a": 1}), canon({"a": 2})]

    def ok(self, good, rejected=()):
        return {"status": "ok", "good": good, "rejected": list(rejected)}

    def test_absorbed(self):
        self.assertEqual(judge(self.ok([{"a": 2}, {"a": 1}]), self.clean)[0], "absorbed")

    def test_silent_wrong(self):
        self.assertEqual(judge(self.ok([{"a": 1}, {"a": 99}]), self.clean)[0], "silent_wrong")

    def test_silently_duplicated_rows_are_wrong(self):
        self.assertEqual(judge(self.ok([{"a": 1}, {"a": 2}, {"a": 2}]), self.clean)[0], "silent_wrong")

    def test_quarantine_needs_every_surviving_row_correct(self):
        self.assertEqual(judge(self.ok([{"a": 1}], ["x"]), self.clean)[0], "quarantined")
        self.assertEqual(judge(self.ok([{"a": 1}, {"a": 99}], ["x"]), self.clean)[0], "silent_wrong")

    def test_crash_vs_loud(self):
        err = {"status": "error", "exc_type": "KeyError", "message": "'x'", "is_dq": False}
        self.assertEqual(judge(err, self.clean)[0], "crashed")
        self.assertEqual(judge({**err, "is_dq": True}, self.clean)[0], "caught_loudly")


class EndToEnd(unittest.TestCase):
    def test_flawed_pipeline_leaks(self):
        s = haunt(FLAWED, ORDERS, seed=1, rate=0.3)
        self.assertGreaterEqual(s["silent_rate"], 0.4)
        self.assertEqual(s["applied"], len(mutators.REGISTRY))

    def test_hardened_pipeline_is_clean(self):
        for seed in (1, 2, 3):
            s = haunt(HARDENED, ORDERS, seed=seed, rate=0.3)
            self.assertEqual(s["silent"], 0, f"seed {seed}: {[r for r in s['results'] if r['verdict'] == 'silent_wrong']}")

    def test_hardened_absorbs_every_benign_mutation(self):
        s = haunt(HARDENED, ORDERS)
        for r in s["results"]:
            if r["kind"] == "benign":
                self.assertEqual(r["verdict"], "absorbed", r["mutator"])

    def test_pipeline_that_fails_on_clean_data_is_rejected(self):
        with self.assertRaises(PipelineLoadError):
            haunt("def clean(rows):\n    return rows[0]['nope']\n", ORDERS)


class Sandbox(unittest.TestCase):
    cases = [{"name": "clean", "csv": "a\n1\n"}]

    def load(self, src):
        return run_cases(src, self.cases, timeout=10)

    def test_blocks_dangerous_imports(self):
        for mod in ("os", "subprocess", "socket", "sys", "pathlib"):
            with self.assertRaises(PipelineLoadError, msg=mod):
                self.load(f"import {mod}\ndef clean(rows):\n    return rows\n")

    def test_blocks_open_and_eval(self):
        r = self.load("def clean(rows):\n    return [{'x': open('/etc/passwd').read()}]\n")
        self.assertEqual(r["clean"]["status"], "error")
        r = self.load("def clean(rows):\n    return [{'x': eval('1')}]\n")
        self.assertEqual(r["clean"]["status"], "error")

    def test_print_does_not_break_the_protocol(self):
        r = self.load("def clean(rows):\n    print('hello')\n    return rows\n")
        self.assertEqual(r["clean"]["status"], "ok")

    def test_infinite_loop_times_out(self):
        r = run_cases("def clean(rows):\n    while True:\n        pass\n", self.cases, timeout=2)
        self.assertEqual(r["clean"]["exc_type"], "Timeout")

    def test_secrets_in_environment_do_not_reach_pipeline(self):
        os.environ["MY_SECRET_KEY"] = "hunter2"
        os.environ["POLTERGEIST_ALLOW"] = "os"  # let the test pipeline import os so it can look
        try:
            src = "import os\ndef clean(rows):\n    return [{'v': os.environ.get('MY_SECRET_KEY', 'absent')}]\n"
            out = self.load(src)["clean"]["good"]
            self.assertEqual(out, [{"v": "absent"}])
        finally:
            del os.environ["MY_SECRET_KEY"], os.environ["POLTERGEIST_ALLOW"]


if __name__ == "__main__":
    unittest.main()
