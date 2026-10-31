"""Behavior tests for the local unittest report CLI; no external dependencies."""

import importlib.util
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


CLI = Path(__file__).resolve().parents[1] / "tools" / "run_unit_tests.py"


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.cases = self.project / "cases"
        self.cases.mkdir(parents=True)

    def source(self, text, name="test_sample.py"):
        (self.cases / name).write_text(textwrap.dedent(text), encoding="utf-8")

    def run_cli(self, report="reports/results.xml", extra=()):
        environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, str(CLI), "--tests", "cases", "--report", report, *extra],
            cwd=self.project, env=environment, capture_output=True,
            encoding="utf-8", errors="replace", timeout=30,
        )

    def report(self):
        return ET.parse(self.project / "reports" / "results.xml").getroot()

    def test_success_keeps_real_name_and_human_output(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_addition(self):
                    print("executed")
                    self.assertEqual(1 + 1, 2)
        ''')
        process = self.run_cli()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("executed", process.stdout)
        self.assertIn("OK", process.stderr)
        root = self.report()
        self.assertEqual(root.attrib["tests"], "1")
        self.assertEqual(root.attrib["failures"], "0")
        self.assertEqual(root.attrib["errors"], "0")
        case = root.find("testcase")
        self.assertEqual(case.attrib["classname"], "test_sample.Example")
        self.assertEqual(case.attrib["name"], "test_addition")

    def test_absolute_cli_path_can_import_project_root_module(self):
        (self.project / "local_module.py").write_text("VALUE = 42\n", encoding="utf-8")
        self.source('''
            import unittest
            import local_module
            class Example(unittest.TestCase):
                def test_project_import(self):
                    self.assertEqual(local_module.VALUE, 42)
        ''')
        process = self.run_cli()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(self.report().find("testcase").attrib["name"], "test_project_import")

    def test_assertion_failure_is_failure(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_assertion(self):
                    self.assertEqual("actual", "expected")
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.report().attrib["failures"], "1")
        self.assertIn("AssertionError", self.report().find("testcase/failure").text)

    def test_runtime_error_is_error(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_exception(self):
                    raise RuntimeError("broken execution")
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.report().attrib["errors"], "1")
        self.assertIn("broken execution", self.report().find("testcase/error").text)

    def test_skip_and_unicode_round_trip(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                @unittest.skip("자료가 없음 — λ")
                def test_문자(self):
                    raise AssertionError("must stay skipped")
        ''')
        self.assertEqual(self.run_cli().returncode, 0)
        root = self.report()
        self.assertEqual(root.attrib["skipped"], "1")
        self.assertEqual(root.find("testcase").attrib["name"], "test_문자")
        self.assertEqual(root.find("testcase/skipped").text, "자료가 없음 — λ")

    def test_expected_failure_is_conservatively_skipped(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                @unittest.expectedFailure
                def test_known_problem(self):
                    self.fail("known problem")
        ''')
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.report().attrib["skipped"], "1")
        self.assertIn("Expected failure", self.report().find("testcase/skipped").text)

    def test_unexpected_success_is_failure(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                @unittest.expectedFailure
                def test_surprise(self):
                    pass
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.report().attrib["failures"], "1")
        self.assertIn("Unexpected success", self.report().find("testcase/failure").text)

    def test_subtest_assertion_and_error_are_both_recorded(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_variants(self):
                    with self.subTest(value=2):
                        self.assertEqual(2, 3)
                    with self.subTest(value="exception"):
                        raise RuntimeError("subtest broke")
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        root = self.report()
        self.assertEqual(root.attrib["tests"], "1")
        self.assertEqual(root.attrib["failures"], "1")
        self.assertEqual(root.attrib["errors"], "1")
        self.assertIn("value=2", root.find("testcase/failure").text)
        self.assertIn("subtest broke", root.find("testcase/error").text)

    def test_class_fixture_error_has_an_error_case(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    raise RuntimeError("class setup failed")
                def test_unreachable(self):
                    pass
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.report().attrib["errors"], "1")
        self.assertIn("class setup failed", self.report().find("testcase/error").text)

    def test_xml_invalid_control_characters_are_printable(self):
        self.source(r'''
            import unittest
            class Example(unittest.TestCase):
                def test_control_character(self):
                    self.fail("invalid\x00character")
        ''')
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertIn(r"\u0000", self.report().find("testcase/failure").text)

    def test_malformed_discovery_produces_error_report(self):
        self.source("def invalid(:\n")
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.report().attrib["errors"], "1")
        self.assertIn("SyntaxError", self.report().find("testcase/error").text)

    def test_empty_suite_has_distinct_nonzero_status(self):
        self.assertEqual(self.run_cli().returncode, 3)
        self.assertEqual(self.report().attrib["tests"], "0")
        self.assertIn("No tests", self.report().find("system-err").text)

    def marker_source(self):
        self.source('''
            from pathlib import Path
            Path("executed.txt").write_text("discovered", encoding="utf-8")
            import unittest
            class Example(unittest.TestCase):
                def test_execution(self):
                    pass
        ''')

    def test_existing_report_is_preserved_before_discovery(self):
        self.marker_source()
        destination = self.project / "reports" / "results.xml"
        destination.parent.mkdir()
        destination.write_bytes(b"original report")
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(destination.read_bytes(), b"original report")
        self.assertFalse((self.project / "executed.txt").exists())

    def test_report_paths_cannot_escape_project(self):
        self.marker_source()
        for path in ("../outside.xml", r"..\outside.xml", str(self.base / "absolute.xml"),
                     r"C:\outside.xml", r"\\server\share\report.xml"):
            with self.subTest(path=path):
                self.assertEqual(self.run_cli(report=path).returncode, 2)
                self.assertFalse((self.project / "executed.txt").exists())

    def test_symlink_to_external_directory_is_rejected(self):
        external = self.base / "external"
        external.mkdir()
        try:
            (self.project / "linked").symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest("directory symlinks unavailable: " + str(error))
        self.marker_source()
        self.assertEqual(self.run_cli(report="linked/results.xml").returncode, 2)
        self.assertFalse((external / "results.xml").exists())
        self.assertFalse((self.project / "executed.txt").exists())

    def test_custom_discovery_pattern(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_selected(self):
                    pass
        ''', name="check_example.py")
        self.assertEqual(self.run_cli(extra=("--pattern", "check_*.py")).returncode, 0)
        self.assertEqual(self.report().find("testcase").attrib["name"], "test_selected")

    def test_report_write_failure_is_nonzero(self):
        self.source('''
            import unittest
            class Example(unittest.TestCase):
                def test_success(self):
                    pass
        ''')
        spec = importlib.util.spec_from_file_location("local_exporter", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        previous = Path.cwd()
        try:
            os.chdir(self.project)
            with mock.patch.object(module.ET.ElementTree, "write", side_effect=OSError("disk full")), \
                    mock.patch("sys.stderr", new_callable=io.StringIO):
                status = module.main(["--tests", "cases", "--report", "reports/results.xml"])
        finally:
            os.chdir(previous)
        self.assertEqual(status, 2)
        self.assertEqual((self.project / "reports" / "results.xml").read_bytes(), b"")


    def test_mixed_network_test_paths_rejected_before_filesystem(self):
        spec = importlib.util.spec_from_file_location("exporter_network_guard", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module.Path, "is_dir", side_effect=AssertionError("filesystem touched")):
            for value in (r"/\server\share", r"\/server/share"):
                with self.subTest(value=value), redirect_stderr(io.StringIO()):
                    self.assertEqual(module.main(["--tests", value, "--report", "report.xml"]), 2)


if __name__ == "__main__":
    unittest.main()
