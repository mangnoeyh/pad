"""Exercise the saved-file boundary between two independently written tools."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "examples" / "allocation_lab.py"
CHECKER = ROOT / "tools" / "check_allocations.py"
SAMPLE = ROOT / "examples" / "allocation_input.json"


class AllocationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="allocation integration ")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def command(self, script, *args, expected=0):
        result = subprocess.run([sys.executable, str(script), *map(str, args)],
                                cwd=self.directory, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def generate(self, name, *options, source=SAMPLE):
        output = self.directory / name
        self.command(GENERATOR, "--input", source, "--output-dir", output, *options)
        return output

    def check(self, output, name="comparison.json", candidates=None, expected=0):
        candidates = candidates or [output / "greedy.json", output / "scarcity.json"]
        target = output / name
        self.command(CHECKER, "--input", output / "effective-input.json",
                     "--candidates", *candidates, "--output", target, expected=expected)
        return json.loads(target.read_text(encoding="utf-8"))

    @staticmethod
    def results(report):
        return {row["method"]: row for row in report["candidates"]}

    def test_default_real_files_and_independent_reference(self):
        before = SAMPLE.read_bytes()
        output = self.generate("first run")
        report = self.check(output)
        rows = self.results(report)
        self.assertEqual(rows["greedy"]["objective"], {"assigned_count": 7, "total_cost": 9})
        self.assertEqual(rows["scarcity"]["objective"], {"assigned_count": 8, "total_cost": 13})
        self.assertEqual(rows["greedy"]["metrics"]["unassigned_item_ids"], ["J3"])
        self.assertEqual(rows["scarcity"]["completeness"], "complete")
        self.assertTrue(rows["scarcity"]["matches_oracle"])
        self.assertEqual(report["best_candidates"], [str(output / "scarcity.json")])
        self.assertEqual(report["oracle"]["status"], "completed")
        self.assertEqual(SAMPLE.read_bytes(), before)
        self.assertEqual(report["input_sha256"], hashlib.sha256(
            (output / "effective-input.json").read_bytes()).hexdigest())

    def test_current_capacity_recomputes_without_mutating_source(self):
        before = SAMPLE.read_bytes()
        output = self.generate("larger", "--capacity", "R1=3")
        report = self.check(output)
        effective = json.loads((output / "effective-input.json").read_text(encoding="utf-8"))
        self.assertEqual(effective["resources"][0]["capacity"], 3)
        self.assertEqual(report["best_objective"], {"assigned_count": 8, "total_cost": 11})
        self.assertTrue(all(row["complete"] for row in report["candidates"]))
        self.assertEqual(SAMPLE.read_bytes(), before)

    def test_shortage_stays_partial_and_keeps_capacity(self):
        output = self.generate("shortage", "--capacity", "R1=0")
        report = self.check(output)
        self.assertTrue(report["all_candidates_valid"])
        self.assertEqual(report["oracle"]["objective"], {"assigned_count": 6, "total_cost": 10})
        self.assertFalse(report["oracle"]["complete"])
        for row in report["candidates"]:
            self.assertEqual(row["completeness"], "partial")
            self.assertEqual(row["metrics"]["resource_load"]["R1"], 0)
            self.assertTrue({"J2", "J3"}.issubset(row["metrics"]["unassigned_item_ids"]))

    def test_previous_input_candidate_is_not_a_current_winner(self):
        old = self.generate("old")
        current = self.generate("current", "--capacity", "R1=3")
        report = self.check(current, candidates=[old / "scarcity.json", current / "greedy.json"], expected=1)
        old_row = report["candidates"][0]
        self.assertFalse(old_row["valid"])
        self.assertIsNone(old_row["objective"])
        self.assertIn("input_hash_mismatch", [x["code"] for x in old_row["violations"]])
        self.assertEqual(report["best_candidates"], [str(current / "greedy.json")])

    def test_scarcity_can_be_worse_and_both_candidates_survive(self):
        # Input order and scarcity's ID tie-break differ. A method name is not
        # evidence of improvement; the independent checker must retain greedy.
        raw = {"schema_version": 1,
               "resources": [{"id": "R1", "capacity": 1}, {"id": "R2", "capacity": 1}],
               "items": [{"id": "Z", "costs": {"R1": 0, "R2": 100}},
                         {"id": "A", "costs": {"R1": 1, "R2": 2}}]}
        source = self.directory / "counterexample.json"
        source.write_text(json.dumps(raw), encoding="utf-8")
        output = self.generate("counterexample", source=source)
        report = self.check(output)
        rows = self.results(report)
        self.assertEqual(rows["greedy"]["objective"], {"assigned_count": 2, "total_cost": 2})
        self.assertEqual(rows["scarcity"]["objective"], {"assigned_count": 2, "total_cost": 101})
        self.assertEqual(report["best_candidates"], [str(output / "greedy.json")])
        self.assertTrue(rows["greedy"]["matches_oracle"])
        self.assertFalse(rows["scarcity"]["matches_oracle"])

    def test_existing_run_and_report_are_not_overwritten(self):
        output = self.generate("preserved")
        self.check(output)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        self.command(GENERATOR, "--input", SAMPLE, "--output-dir", output, expected=2)
        self.command(CHECKER, "--input", output / "effective-input.json", "--candidates",
                     output / "greedy.json", "--output", output / "comparison.json", expected=2)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_invalid_override_creates_no_candidate_directory(self):
        output = self.directory / "invalid"
        self.command(GENERATOR, "--input", SAMPLE, "--output-dir", output,
                     "--capacity", "R1=-1", expected=2)
        self.assertFalse(output.exists())

    def test_empty_boundary_matches_both_independent_schemas(self):
        source = self.directory / "empty.json"
        source.write_text(json.dumps({"schema_version": 1, "resources": [], "items": []}), encoding="utf-8")
        report = self.check(self.generate("empty", source=source))
        self.assertEqual(report["oracle"]["objective"], {"assigned_count": 0, "total_cost": 0})
        self.assertTrue(all(row["complete"] for row in report["candidates"]))


if __name__ == "__main__":
    unittest.main()
