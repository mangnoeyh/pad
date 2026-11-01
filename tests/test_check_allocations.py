"""Original expected-value checks; no candidate-generator imports or expectations."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "check_allocations.py"
SPEC = importlib.util.spec_from_file_location("check_allocations", MODULE_PATH)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
DIGEST = "a" * 64


def trap():
    # Choosing J1 -> R1 first loses one item. Full coverage costs exactly 3.
    return {"schema_version": 1,
            "resources": [{"id": "R1", "capacity": 1}, {"id": "R2", "capacity": 1}],
            "items": [{"id": "J1", "costs": {"R1": 0, "R2": 2}},
                      {"id": "J2", "costs": {"R1": 1}}]}


def candidate(assignment, method="greedy", digest=DIGEST):
    return {"schema_version": 1, "method": method, "input_sha256": digest,
            "assignment": assignment}


class ValidationTests(unittest.TestCase):
    def test_valid_input_copy_preserves_order_and_zero(self):
        problem = trap()
        result = checker.validate_problem(problem)
        self.assertEqual(result, problem)
        result["items"][0]["costs"]["R1"] = 999
        self.assertEqual(problem["items"][0]["costs"]["R1"], 0)

    def test_bad_numeric_types_and_negative_values(self):
        for value in (True, False, -1, 1.0, float("nan"), float("inf"), "1", None):
            for field in ("capacity", "cost"):
                with self.subTest(value=value, field=field):
                    problem = trap()
                    if field == "capacity":
                        problem["resources"][0]["capacity"] = value
                    else:
                        problem["items"][0]["costs"]["R1"] = value
                    with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                        checker.validate_problem(problem)

    def test_schema_version_requires_integer_one(self):
        for value in (True, 1.0, 2, "1", None):
            with self.subTest(value=value):
                problem = trap()
                problem["schema_version"] = value
                with self.assertRaisesRegex(ValueError, "schema_version"):
                    checker.validate_problem(problem)

    def test_duplicate_and_invalid_ids(self):
        for group in ("resources", "items"):
            with self.subTest(group=group):
                problem = trap()
                problem[group][1]["id"] = problem[group][0]["id"]
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    checker.validate_problem(problem)
        for iid in (None, 1, "", " ", " J1", "J1 ", "J\n1", "x" * 129):
            with self.subTest(iid=iid):
                problem = trap()
                problem["items"][0]["id"] = iid
                with self.assertRaisesRegex(ValueError, "ID"):
                    checker.validate_problem(problem)

    def test_unknown_resource_and_unknown_schema_fields(self):
        problem = trap()
        problem["items"][0]["costs"]["R9"] = 1
        with self.assertRaisesRegex(ValueError, "unknown resource"):
            checker.validate_problem(problem)
        for location in ("root", "resource", "item"):
            with self.subTest(location=location):
                problem = trap()
                node = (problem if location == "root" else problem[location + "s"][0])
                node["status"] = "valid"
                with self.assertRaisesRegex(ValueError, "exactly"):
                    checker.validate_problem(problem)

    def test_input_size_dimensions_are_bounded(self):
        problem = trap()
        with patch.object(checker, "MAX_RESOURCES", 1):
            with self.assertRaisesRegex(ValueError, "resources"):
                checker.validate_problem(problem)
        with patch.object(checker, "MAX_ITEMS", 1):
            with self.assertRaisesRegex(ValueError, "items"):
                checker.validate_problem(problem)
        with patch.object(checker, "MAX_EDGES", 2):
            with self.assertRaisesRegex(ValueError, "edges"):
                checker.validate_problem(problem)


class CandidateTests(unittest.TestCase):
    def check(self, value, problem=None):
        return checker.check_candidate(problem or trap(), value, DIGEST)

    def codes(self, result):
        return {entry["code"] for entry in result["violations"]}

    def test_partial_is_valid_and_explicit(self):
        result = self.check(candidate({"J1": "R1", "J2": None}))
        self.assertTrue(result["valid"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["completeness"], "partial")
        self.assertEqual(result["objective"], {"assigned_count": 1, "total_cost": 0})
        self.assertEqual(result["metrics"]["unassigned_item_ids"], ["J2"])
        self.assertEqual(result["metrics"]["resource_load"], {"R1": 1, "R2": 0})

    def test_full_candidate_cost_and_capacity_recomputed(self):
        result = self.check(candidate({"J1": "R2", "J2": "R1"}, "scarcity"))
        self.assertTrue(result["valid"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["objective"], {"assigned_count": 2, "total_cost": 3})
        self.assertEqual(result["metrics"]["resource_load"], {"R1": 1, "R2": 1})

    def test_over_capacity_forbidden_and_unknown(self):
        cases = [({"J1": "R1", "J2": "R1"}, "over_capacity"),
                 ({"J1": None, "J2": "R2"}, "forbidden_resource"),
                 ({"J1": "R9", "J2": None}, "unknown_resource")]
        for assignment, code in cases:
            with self.subTest(code=code):
                result = self.check(candidate(assignment))
                self.assertFalse(result["valid"])
                self.assertIsNone(result["objective"])
                self.assertIn(code, self.codes(result))

    def test_missing_and_extra_assignments(self):
        result = self.check(candidate({"J1": None, "J9": None}))
        self.assertEqual(result["coverage"]["missing_item_ids"], ["J2"])
        self.assertEqual(result["coverage"]["extra_item_ids"], ["J9"])
        self.assertEqual(self.codes(result), {"missing_item_ids", "extra_item_ids"})

    def test_assignment_types_and_all_required_fields(self):
        for value in (True, 1, [], {}, 1.0):
            with self.subTest(value=value):
                result = self.check(candidate({"J1": value, "J2": None}))
                self.assertIn("assignment_value_type", self.codes(result))
        result = self.check(candidate(["R1", None]))
        self.assertIn("assignment_type", self.codes(result))
        for field in ("schema_version", "method", "input_sha256", "assignment"):
            with self.subTest(missing=field):
                value = candidate({"J1": None, "J2": None})
                del value[field]
                self.assertIn("candidate_fields", self.codes(self.check(value)))

    def test_cannot_trust_claimed_status_or_changed_input(self):
        value = candidate({"J1": None, "J2": None}, digest="b" * 64)
        value["status"] = "optimal"
        value["total_cost"] = -100
        result = self.check(value)
        self.assertIn("candidate_fields", self.codes(result))
        self.assertIn("input_hash_mismatch", self.codes(result))
        self.assertIsNone(result["objective"])
        self.assertEqual(result["metrics"]["total_cost"], 0)

    def test_method_and_schema_validation(self):
        for field, value, code in (("method", "exact", "method"),
                                   ("method", [], "method"),
                                   ("schema_version", True, "schema_version")):
            with self.subTest(field=field, value=value):
                value_candidate = candidate({"J1": None, "J2": None})
                value_candidate[field] = value
                self.assertIn(code, self.codes(self.check(value_candidate)))


class ExactReferenceTests(unittest.TestCase):
    def test_greedy_trap_known_optimum(self):
        result = checker.exact_reference(trap())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["combinations"], 6)
        self.assertEqual(result["states_examined"], 6)
        self.assertEqual(result["objective"], {"assigned_count": 2, "total_cost": 3})
        self.assertEqual(result["assignment"], {"J1": "R2", "J2": "R1"})

    def test_cost_breaks_coverage_tie_not_the_reverse(self):
        problem = {"schema_version": 1,
                   "resources": [{"id": "R", "capacity": 1}],
                   "items": [{"id": "expensive", "costs": {"R": 10}},
                             {"id": "cheap", "costs": {"R": 2}}]}
        result = checker.exact_reference(problem)
        self.assertEqual(result["objective"], {"assigned_count": 1, "total_cost": 2})
        self.assertEqual(result["assignment"], {"expensive": None, "cheap": "R"})
        self.assertFalse(result["complete"])

    def test_zero_capacity_and_no_allowed_edges(self):
        problem = {"schema_version": 1, "resources": [{"id": "R", "capacity": 0}],
                   "items": [{"id": "blocked", "costs": {"R": 0}},
                             {"id": "isolated", "costs": {}}]}
        result = checker.exact_reference(problem)
        self.assertEqual(result["objective"], {"assigned_count": 0, "total_cost": 0})
        self.assertEqual(result["assignment"], {"blocked": None, "isolated": None})
        self.assertFalse(result["complete"])

    def test_empty_boundaries(self):
        for resources, items in (([], []), ([{"id": "R", "capacity": 0}], []),
                                 ([], [{"id": "J", "costs": {}}])):
            with self.subTest(resources=resources, items=items):
                problem = {"schema_version": 1, "resources": resources, "items": items}
                reference = checker.exact_reference(problem)
                self.assertEqual(reference["objective"], {"assigned_count": 0, "total_cost": 0})
                self.assertEqual(reference["states_examined"], 1)
                self.assertEqual(reference["complete"], not items)
                checked = checker.check_candidate(problem, candidate(reference["assignment"]), DIGEST)
                self.assertTrue(checked["valid"])
                self.assertEqual(checked["complete"], not items)

    def test_limit_skip_never_enumerates(self):
        with patch.object(checker.itertools, "product", side_effect=AssertionError("enumerated")):
            result = checker.exact_reference(trap(), limit=5)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "combination_limit_exceeded")
        self.assertEqual(result["states_examined"], 0)
        self.assertIsNone(result["objective"])

    def test_hard_bound_cannot_be_bypassed_and_item_bound(self):
        problem = {"schema_version": 1, "resources": [{"id": "R", "capacity": 25}],
                   "items": [{"id": f"J{i}", "costs": {"R": 1}} for i in range(20)]}
        result = checker.exact_reference(problem, limit=10 ** 30)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["effective_limit"], checker.HARD_ORACLE_LIMIT)
        self.assertEqual(result["combinations"], 2 ** 20)
        many = {"schema_version": 1, "resources": [],
                "items": [{"id": f"J{i}", "costs": {}} for i in range(201)]}
        result = checker.exact_reference(many)
        self.assertEqual(result["reason"], "item_limit_exceeded")

    def test_invalid_oracle_limit(self):
        for limit in (True, 0, -1, 2.0):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    checker.exact_reference(trap(), limit)


class CLITests(unittest.TestCase):
    def setUp(self):
        # All transient fixtures remain under the task workspace.
        temporary_root = MODULE_PATH.parents[1] / "tmp" / "checker-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.write("input.json", trap())
        self.digest = hashlib.sha256(self.input.read_bytes()).hexdigest()

    def write(self, name, data):
        path = self.root / name
        path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode("utf-8"))
        return path

    def run_cli(self, *candidates, output="report.json", extra=()):
        args = ["--input", str(self.input), "--candidates", *map(str, candidates),
                "--output", str(self.root / output), *extra]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = checker.main(args)
        path = self.root / output
        return code, json.loads(path.read_text("utf-8")) if path.is_file() else None

    def test_end_to_end_best_candidate_and_oracle(self):
        greedy = self.write("greedy.json", candidate({"J1": "R1", "J2": None}, digest=self.digest))
        scarcity = self.write("scarcity.json", candidate({"J1": "R2", "J2": "R1"}, "scarcity", self.digest))
        before = [path.read_bytes() for path in (self.input, greedy, scarcity)]
        code, report = self.run_cli(greedy, scarcity)
        self.assertEqual(code, 0)
        self.assertEqual(report["contract_id"], "single-choice-capacity-v1")
        self.assertEqual(report["input_sha256"], self.digest)
        self.assertEqual(report["best_candidates"], [str(scarcity)])
        self.assertEqual(report["best_objective"], {"assigned_count": 2, "total_cost": 3})
        self.assertEqual([entry["matches_oracle"] for entry in report["candidates"]], [False, True])
        self.assertEqual(before, [path.read_bytes() for path in (self.input, greedy, scarcity)])

    def test_invalid_excluded_partial_remains_and_ties_preserved(self):
        valid = candidate({"J1": "R1", "J2": None}, digest=self.digest)
        first, second = self.write("first.json", valid), self.write("second.json", valid)
        invalid = self.write("invalid.json", candidate({"J1": "R1", "J2": "R1"}, digest=self.digest))
        code, report = self.run_cli(first, invalid, second)
        self.assertEqual(code, 1)
        self.assertEqual(report["best_candidates"], [str(first), str(second)])
        self.assertEqual(report["best_objective"], {"assigned_count": 1, "total_cost": 0})
        self.assertEqual(len(report["candidates"]), 3)
        self.assertEqual(report["candidates"][0]["completeness"], "partial")

    def test_no_valid_candidate_has_no_winner(self):
        invalid = self.write("bad.json", candidate({"J1": "R1", "J2": None}))
        code, report = self.run_cli(invalid)
        self.assertEqual(code, 1)
        self.assertEqual(report["best_candidates"], [])
        self.assertIsNone(report["best_objective"])

    def test_exact_input_bytes_hash_includes_whitespace(self):
        valid = self.write("valid.json", candidate({"J1": None, "J2": None}, digest=self.digest))
        self.input.write_bytes(self.input.read_bytes() + b"\n")
        code, report = self.run_cli(valid)
        self.assertEqual(code, 1)
        self.assertIn("input_hash_mismatch", {entry["code"] for entry in report["candidates"][0]["violations"]})

    def test_duplicate_json_keys_and_nan_are_rejected(self):
        for i, raw in enumerate((b'{"schema_version":1,"schema_version":1}',
                                 b'{"assignment":{"J1":null,"J1":"R1"}}',
                                 b'{"value":NaN}', b'{"value":Infinity}', b'no JSON')):
            with self.subTest(raw=raw):
                bad = self.write(f"bad{i}.json", raw)
                with self.assertRaises(ValueError):
                    checker.read_json(bad)
                code, report = self.run_cli(bad, output=f"report{i}.json")
                self.assertEqual(code, 1)
                self.assertEqual(report["candidates"][0]["violations"][0]["code"], "candidate_json")

    def test_utf8_bom_and_remote_paths_rejected(self):
        path = self.write("bom.json", b"\xef\xbb\xbf{}")
        with self.assertRaises(ValueError):
            checker.read_json(path)
        for path in ("https://example.com/input.json", "//server/share/input.json", "\\\\server\\share\\input.json"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "local filesystem"):
                    checker.read_json(path)

    def test_invalid_unicode_candidate_still_gets_a_valid_failure_report(self):
        value = candidate({"J1": None, "J2": None}, digest=self.digest)
        value["method"] = "\ud800"
        bad = self.write("surrogate.json", value)
        code, report = self.run_cli(bad)
        self.assertEqual(code, 1)
        self.assertFalse(report["candidates"][0]["valid"])

    def test_input_failure_io_failure_and_no_overwrite(self):
        valid = self.write("valid.json", candidate({"J1": None, "J2": None}, digest=self.digest))
        code, _ = self.run_cli(self.root / "absent.json")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "report.json").exists())
        existing = self.write("report.json", b'{"sentinel":true}\n')
        before = existing.read_bytes()
        code, _ = self.run_cli(valid)
        self.assertEqual(code, 2)
        self.assertEqual(existing.read_bytes(), before)
        self.input.write_bytes(b'{"schema_version":1,"resources":[],"items":[],"extra":1}')
        code, _ = self.run_cli(valid, output="other.json")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "other.json").exists())

    def test_dangling_output_link_does_not_create_target(self):
        valid = self.write("valid.json", candidate({"J1": None, "J2": None}, digest=self.digest))
        target = self.root / "absent-target.json"
        link = self.root / "report.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        code, _ = self.run_cli(valid)
        self.assertEqual(code, 2)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_oversize_file_rejected(self):
        path = self.write("oversize.json", b" " * 17)
        with patch.object(checker, "MAX_FILE_BYTES", 16):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                checker.read_json(path)

    def test_disabled_or_bounded_oracle_is_honest(self):
        valid = self.write("valid.json", candidate({"J1": None, "J2": None}, digest=self.digest))
        for i, args in enumerate((("--no-oracle",), ("--oracle-limit", "1"))):
            with self.subTest(args=args):
                code, report = self.run_cli(valid, output=f"skip{i}.json", extra=args)
                self.assertEqual(code, 0)
                self.assertEqual(report["oracle"]["status"], "skipped")
                self.assertIsNone(report["oracle"]["objective"])
                self.assertIsNone(report["candidates"][0]["matches_oracle"])

    def test_real_cli_exit_codes(self):
        valid = self.write("valid.json", candidate({"J1": None, "J2": None}, digest=self.digest))
        invalid = self.write("invalid.json", candidate({"J1": "R1", "J2": "R1"}, digest=self.digest))
        for name, path, expected in (("valid", valid, 0), ("invalid", invalid, 1),
                                     ("missing", self.root / "missing.json", 2)):
            with self.subTest(name=name):
                result = subprocess.run([sys.executable, str(MODULE_PATH), "--input", str(self.input),
                                         "--candidates", str(path), "--output", str(self.root / f"{name}-cli.json")],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
