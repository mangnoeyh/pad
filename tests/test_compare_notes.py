"""Original temporary-fixture checks for the note comparison contract."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "compare_notes.py"
SPEC = importlib.util.spec_from_file_location("compare_notes", MODULE_PATH)
notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notes)


class CompareNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content):
        path = self.root / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def run_cli(self, before="before.txt", after="after.txt", project=None):
        output = io.StringIO()
        with redirect_stdout(output):
            code = notes.main(["--project", str(project or self.root), "--before", before, "--after", after])
        return code, json.loads(output.getvalue())

    def compare_text(self, before, after):
        self.write("before.txt", before)
        self.write("after.txt", after)
        return self.run_cli()

    def test_unchanged_and_preserved(self):
        first = self.write("before.txt", b"\xef\xbb\xbfAmount: 5 kg\n")
        second = self.write("after.txt", "Amount: 5 kg\n")
        snapshots = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (first, second)]
        code, result = self.run_cli()
        self.assertEqual((code, result["status"]), (0, "no_findings"))
        self.assertEqual(result["findings"], [])
        self.assertIn("not semantic proof", result["note"])
        self.assertEqual(snapshots, [(p.read_bytes(), p.stat().st_mtime_ns) for p in (first, second)])
        self.assertEqual({p.name for p in self.root.iterdir()}, {"before.txt", "after.txt"})

    def test_reordering_preserves_multiset(self):
        code, _ = self.compare_text("5kg\n10%\n5kg\n", "5 kg\n5kg\n10 %\n")
        self.assertEqual(code, 0)

    def test_duplicate_removal_has_a_location(self):
        code, result = self.compare_text("5kg\n5kg\n", "5kg\n")
        self.assertEqual(code, 1)
        self.assertEqual(result["counts"]["removed"], 1)
        self.assertEqual(result["findings"], [{"change": "removed", "kind": "quantity", "value": "5kg", "line": 1}])

    def test_quantity_unit_and_comparator_linkage(self):
        for left, right in (("5kg", "5%"), (">=5kg", ">5kg"), ("5명 이상", "5명 초과"), ("3", "4")):
            with self.subTest(left=left):
                code, result = self.compare_text(left, right)
                self.assertEqual(code, 1)
                self.assertEqual(result["counts"]["removed"], 1)
                self.assertEqual(result["counts"]["added"], 1)

    def test_signed_scientific_and_thousands(self):
        _, result = self.compare_text("-1.25e-3kg +2E+4% 1,234.5원", "-1.25e-2kg +2E+4% 1,234.5원")
        self.assertEqual([x["value"] for x in result["findings"]], ["-1.25e-3kg", "-1.25e-2kg"])
        self.assertEqual(result["counts"]["before"], 3)

    def test_korean_and_unicode_operators(self):
        code, result = self.compare_text("인원 ≥ 12명\n길이 1.5미터 이하", "인원 ≥12명\n길이 1.5미터 이상")
        self.assertEqual(code, 1)
        self.assertEqual(result["findings"][0]["line"], 2)
        self.assertEqual(result["findings"][0]["value"], "1.5미터이하")

    def test_korean_adjacent_quantity_and_comparator_candidates(self):
        code, result = self.compare_text("표본은100개\n기준95%이상", "표본은101개\n기준95%초과")
        self.assertEqual(code, 1)
        self.assertEqual([x["value"] for x in result["findings"]],
                         ["100개", "95%이상", "101개", "95%초과"])

    def test_direct_quotes_and_unclosed_quotes(self):
        code, result = self.compare_text('“hello world”\n「안녕」\n"open', '"hello world"\n『다음』\n"open')
        self.assertEqual(code, 1)
        self.assertEqual([(x["kind"], x["value"]) for x in result["findings"]], [("quote", "안녕"), ("quote", "다음")])

    def test_single_quotes_are_bounded_and_contractions_are_ignored(self):
        code, result = self.compare_text("'hello' don't shouldn't", "‘goodbye’ don't shouldn't")
        self.assertEqual(code, 1)
        self.assertEqual([x["value"] for x in result["findings"]], ["hello", "goodbye"])

    def test_long_values_are_reported_as_excerpts(self):
        code, result = self.compare_text('"' + "a" * 1000 + '"', '"' + "b" * 1000 + '"')
        self.assertEqual(code, 1)
        for finding in result["findings"]:
            self.assertEqual(len(finding["value"]), notes.MAX_VALUE_CHARS)
            self.assertTrue(finding["value_truncated"])
            self.assertEqual(finding["value_length"], 1000)

    def test_punctuation_and_whitespace(self):
        code, _ = self.compare_text("Mass: 5 kg.\n", "Mass — 5kg!\n")
        self.assertEqual(code, 0)

    def test_missing_invalid_utf8_and_oversize(self):
        self.write("after.txt", "okay")
        for content in (None, b"\xff", b"x" * (notes.MAX_BYTES + 1)):
            with self.subTest(content_type=type(content).__name__):
                if content is not None:
                    self.write("before.txt", content)
                code, result = self.run_cli()
                self.assertEqual((code, result["status"]), (2, "error"))
                self.assertIn("error", result)

    def test_exact_byte_limit_accepted(self):
        code, _ = self.compare_text(b"x" * notes.MAX_BYTES, b"x" * notes.MAX_BYTES)
        self.assertEqual(code, 0)

    def test_unsafe_arguments_rejected_before_filesystem(self):
        cases = [(p, "a", "b") for p in ("https://host/p", "file:///tmp/p", "//host/p", "\\\\host\\p", "/\\host/p", "\\/host/p")]
        cases += [(str(self.root), p, "b") for p in ("../a", "a/../../b", "/tmp/a", "C:/a", "a\\b", "https://host/a", "//host/a")]
        for project, before, after in cases:
            with self.subTest(project=project, before=before):
                with patch.object(notes.Path, "resolve", side_effect=AssertionError("filesystem reached")):
                    with self.assertRaises(ValueError):
                        notes.compare(project, before, after)

    def test_regular_files_and_existing_project_required(self):
        self.write("after.txt", "okay")
        (self.root / "directory").mkdir()
        self.assertEqual(self.run_cli(before="directory")[0], 2)
        self.assertEqual(self.run_cli(project=self.root / "missing")[0], 2)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "note.txt"
            target.write_text("5kg", encoding="utf-8")
            try:
                (self.root / "link.txt").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable in this environment.")
            self.write("after.txt", "5kg")
            self.assertEqual(self.run_cli(before="link.txt")[0], 2)

    def test_findings_are_bounded_and_totals_retained(self):
        code, result = self.compare_text("\n".join(str(x) for x in range(80)), "")
        self.assertEqual(code, 1)
        self.assertEqual(result["findings_total"], 80)
        self.assertEqual(result["findings_reported"], 50)
        self.assertEqual(result["findings_truncated"], 30)
        self.assertEqual(len(result["findings"]), 50)
        self.assertNotIn("text", result)

    def test_argument_errors_are_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = notes.main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "error")

    def test_help_is_conventional_and_successful(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            notes.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--project", output.getvalue())


    def test_repeated_unclosed_openers_have_no_candidates(self):
        text = "\n".join(char * 15000 for char in ("“", "‘", "「", "『"))
        code, result = self.compare_text(text, text)
        self.assertEqual(code, 0)
        self.assertEqual(result["counts"]["before"], 0)

    def test_resolution_loop_is_a_json_input_error(self):
        self.write("before.txt", "5kg")
        self.write("after.txt", "5kg")
        with patch.object(notes.Path, "resolve", side_effect=RuntimeError("resolution loop")):
            code, result = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
