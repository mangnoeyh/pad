"""Independent, subprocess-based checks for the work-evidence CLI contract.

Run after placing this module in the project's tests directory:
    python -m unittest discover -s tests -p test_verify_work.py

Only Python's standard library is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid


CLI = Path(__file__).resolve().parents[1] / "tools" / "verify_work.py"


def junit(case_names: tuple[str, ...] = ("first", "second")) -> str:
    cases = "".join(f'<testcase name="{name}" />' for name in case_names)
    count = len(case_names)
    return (
        f'<testsuites tests="{count}" failures="0" errors="0" skipped="0">'
        f'<testsuite name="checks" tests="{count}" failures="0" '
        f'errors="0" skipped="0">{cases}</testsuite></testsuites>'
    )


@dataclass
class RecordedRun:
    process: subprocess.CompletedProcess[str]
    data: dict
    stdout_marker: str
    stderr_marker: str
    report_path: Path | None

    @property
    def record_id(self) -> str | None:
        value = self.data.get("record_id")
        return value if isinstance(value, str) and value else None


class VerifyWorkContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="work-evidence-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.store = self.project / "store"
        self.project.mkdir()
        self.store.mkdir()
        self.source = self.project / "input.txt"
        self.source.write_text("original input\n", encoding="utf-8")
        self.other_source = self.project / "other.txt"
        self.other_source.write_text("second input\n", encoding="utf-8")
        (self.root / "outside.txt").write_text("outside input\n", encoding="utf-8")

    def invoke(self, arguments: list[str], *, require_json: bool = True):
        process = subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
            check=False,
        )
        data = {}
        if require_json or process.stdout.strip():
            try:
                data = json.loads(process.stdout)
            except json.JSONDecodeError as error:
                self.fail(
                    f"CLI stdout must contain one JSON object: {error}; "
                    f"stdout={process.stdout!r}; stderr={process.stderr!r}"
                )
            self.assertIsInstance(data, dict)
            self.assertIsInstance(data.get("status"), str)
        return process, data

    def record_arguments(
        self,
        code: str,
        *,
        watch: list[str] | None = None,
        timeout: str = "5",
        store: Path | None = None,
        report: str | None = None,
    ) -> list[str]:
        arguments = [
            "record", "--project", str(self.project),
            "--store", str(self.store if store is None else store),
        ]
        for relative_path in ["input.txt"] if watch is None else watch:
            arguments += ["--watch", relative_path]
        arguments += ["--timeout", timeout]
        if report is not None:
            arguments += ["--test-report", report]
        return [*arguments, "--", sys.executable, "-c", code]

    def record(
        self,
        *,
        xml: str | None = None,
        with_report: bool = True,
        watch: list[str] | None = None,
        extra_code: str = "",
        exit_code: int = 0,
        timeout: str = "5",
    ) -> RecordedRun:
        stdout_marker = "child-stdout-" + uuid.uuid4().hex
        stderr_marker = "child-stderr-" + uuid.uuid4().hex
        report_name = "report-" + uuid.uuid4().hex + ".xml"
        report_path = self.project / report_name if with_report else None
        code = (
            "from pathlib import Path\nimport sys\nimport time\n"
            f"print({stdout_marker!r}, flush=True)\n"
            f"print({stderr_marker!r}, file=sys.stderr, flush=True)\n"
        )
        if with_report and xml is not None:
            code += f"Path({str(report_path)!r}).write_text({xml!r}, encoding='utf-8')\n"
        if extra_code:
            code += extra_code + "\n"
        code += f"sys.exit({exit_code})\n"
        process, data = self.invoke(self.record_arguments(
            code, watch=watch, timeout=timeout,
            report=report_name if with_report else None,
        ))
        if process.returncode == 0:
            self.assertIsInstance(data.get("record_id"), str)
            self.assertTrue(data["record_id"])
        return RecordedRun(process, data, stdout_marker, stderr_marker, report_path)

    def successful_record(self, **kwargs) -> RecordedRun:
        run = self.record(**kwargs)
        self.assertEqual(run.process.returncode, 0, run.process.stderr)
        self.assertIsNotNone(run.record_id)
        return run

    def verify(self, run: RecordedRun, minimum: int = 1, *, require_watch: list[str] | None = None):
        self.assertIsNotNone(run.record_id)
        arguments = [
            "verify", "--project", str(self.project), "--store", str(self.store),
            "--record", run.record_id, "--minimum-tests", str(minimum),
        ]
        for relative_path in require_watch or []:
            arguments += ["--require-watch", relative_path]
        return self.invoke(arguments)

    def assert_verified(self, run: RecordedRun, minimum: int = 1, *, require_watch: list[str] | None = None) -> None:
        process, data = self.verify(run, minimum, require_watch=require_watch)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(data.get("status"), "verified_tests")
        self.assertIsNot(data.get("whole_task_done"), True)
        self.assertIsNot(data.get("approved"), True)

    def assert_not_verified(self, run: RecordedRun, minimum: int = 1, *, require_watch: list[str] | None = None) -> None:
        if run.record_id is None:
            self.assertNotEqual(run.process.returncode, 0)
            self.assertNotEqual(run.data.get("status"), "verified_tests")
            return
        process, data = self.verify(run, minimum, require_watch=require_watch)
        self.assertNotEqual(process.returncode, 0, process.stdout)
        self.assertNotEqual(data.get("status"), "verified_tests")

    def record_directory(self, run: RecordedRun) -> Path:
        self.assertIsNotNone(run.record_id)
        directories = [
            path for path in self.store.rglob("*")
            if path.is_dir() and path.name == run.record_id
        ]
        if len(directories) == 1:
            return directories[0]

        # A record ID need not be the directory's literal name. Its JSON
        # metadata can also identify the public directory for this run.
        def includes_id(value) -> bool:
            if isinstance(value, dict):
                return any(includes_id(item) for item in value.values())
            if isinstance(value, list):
                return any(includes_id(item) for item in value)
            return value == run.record_id

        candidates = set()
        for path in self.store.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if includes_id(data):
                candidates.add(path.parent)
        self.assertEqual(
            len(candidates), 1,
            "Each record must expose a distinct directory identifiable by its ID.",
        )
        return candidates.pop()

    def log_for_marker(self, run: RecordedRun, marker: str) -> Path:
        directory = self.record_directory(run)
        marker_bytes = marker.encode("utf-8")
        candidates = []
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            content = path.read_bytes()
            if marker_bytes in content and (
                path.suffix.lower() == ".log" or marker_bytes in content.splitlines()
            ):
                candidates.append(path)
        self.assertTrue(candidates, "The child's output must be retained in a file log.")
        return sorted(candidates)[0]

    def test_process_only_record_requires_review_and_captures_logs(self) -> None:
        run = self.successful_record(with_report=False)
        self.assertEqual(run.data.get("status"), "process_ok")
        self.log_for_marker(run, run.stdout_marker)
        self.log_for_marker(run, run.stderr_marker)
        process, data = self.verify(run)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(data.get("status"), "review")
        self.assertIsNot(data.get("whole_task_done"), True)
        self.assertIsNot(data.get("approved"), True)

    def test_fresh_success_report_verifies_multiple_watched_files(self) -> None:
        run = self.successful_record(xml=junit(), watch=["input.txt", "other.txt"])
        self.assert_verified(run, minimum=2)

    def test_required_dependencies_match_canonical_record_paths(self) -> None:
        (self.project / "requirements.md").write_text("Maximum: 10\n", encoding="utf-8")
        (self.project / "decisions.md").write_text("Accepted: 8\n", encoding="utf-8")
        run = self.successful_record(
            xml=junit(), watch=["input.txt", "./requirements.md", "decisions.md"],
            extra_code=(
                "limit = int(Path('requirements.md').read_text().split(':')[1])\n"
                "accepted = int(Path('decisions.md').read_text().split(':')[1])\n"
                "assert accepted <= limit"
            ),
        )
        self.assert_verified(run, minimum=2, require_watch=["./requirements.md", "decisions.md"])

    def test_requirement_or_decision_change_invalidates_record(self) -> None:
        dependencies = ["requirements.md", "decisions.md"]
        for changed in dependencies:
            with self.subTest(changed=changed):
                for name in dependencies:
                    (self.project / name).write_text("Original decision\n", encoding="utf-8")
                run = self.successful_record(xml=junit(), watch=["input.txt", *dependencies])
                self.assert_verified(run, require_watch=dependencies)
                (self.project / changed).write_text("Revised decision\n", encoding="utf-8")
                self.assert_not_verified(run, require_watch=dependencies)

    def test_new_required_dependency_needs_fresh_execution_without_rewriting_old_record(self) -> None:
        for name, existed in (("other.txt", True), ("new-answer.md", False)):
            with self.subTest(dependency_existed_at_recording=existed):
                original = self.successful_record(xml=junit())
                directory = self.record_directory(original)
                preserved = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
                if not existed:
                    (self.project / name).write_text("New stakeholder answer\n", encoding="utf-8")
                self.assert_verified(original, require_watch=["input.txt"])
                process, data = self.verify(original, require_watch=["input.txt", name])
                self.assertEqual(process.returncode, 2)
                self.assertEqual(data.get("status"), "error")
                refreshed = self.successful_record(xml=junit(), watch=["input.txt", name])
                self.assertNotEqual(original.record_id, refreshed.record_id)
                self.assert_verified(refreshed, require_watch=["input.txt", name])
                self.assert_not_verified(original, require_watch=["input.txt", name])
                self.assertEqual(
                    preserved, {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()},
                )

    def test_unrelated_unrequired_file_change_does_not_invalidate_record(self) -> None:
        run = self.successful_record(xml=junit())
        self.assert_verified(run, require_watch=["input.txt"])
        self.other_source.write_text("Unrelated edit\n", encoding="utf-8")
        self.assert_verified(run, require_watch=["input.txt"])

    def test_invalid_required_paths_and_duplicate_aliases_are_rejected(self) -> None:
        run = self.successful_record(xml=junit())
        cases = [
            [""], ["missing.txt"], ["."], ["store"], [str(self.source)],
            ["../outside.txt"], ["https://example.invalid/input.txt"], [".\\input.txt"],
            ["input.txt", "./input.txt"],
        ]
        for required in cases:
            with self.subTest(require_watch=required):
                process, data = self.verify(run, require_watch=required)
                self.assertEqual(process.returncode, 2)
                self.assertEqual(data.get("status"), "error")

    def test_records_use_distinct_directories_and_keep_earlier_logs(self) -> None:
        first = self.successful_record(with_report=False)
        first_directory = self.record_directory(first)
        first_log = self.log_for_marker(first, first.stdout_marker)
        original_log = first_log.read_bytes()
        second = self.successful_record(with_report=False)
        self.assertNotEqual(first.record_id, second.record_id)
        self.assertNotEqual(first_directory, self.record_directory(second))
        self.assertEqual(first_log.read_bytes(), original_log)
        self.log_for_marker(second, second.stdout_marker)

    def test_preexisting_report_is_rejected_before_child_runs(self) -> None:
        report = self.project / "existing.xml"
        report.write_text(junit(), encoding="utf-8")
        sentinel = self.project / "child-ran.txt"
        code = f"from pathlib import Path; Path({str(sentinel)!r}).write_text('ran')"
        process, data = self.invoke(
            self.record_arguments(code, report=report.name), require_json=False,
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(sentinel.exists())
        self.assertEqual(report.read_text(encoding="utf-8"), junit())
        self.assertNotEqual(data.get("status"), "verified_tests")

    def test_invalid_record_arguments_do_not_start_child(self) -> None:
        cases = [
            ("zero timeout", {"timeout": "0"}),
            ("negative timeout", {"timeout": "-1"}),
            ("NaN timeout", {"timeout": "NaN"}),
            ("infinite timeout", {"timeout": "Infinity"}),
            ("negative infinite timeout", {"timeout": "-Infinity"}),
            ("no watched files", {"watch": []}),
            ("empty watched path", {"watch": [""]}),
            ("missing watched file", {"watch": ["missing.txt"]}),
            ("watched directory", {"watch": ["."]}),
            ("absolute watched path", {"watch": [str(self.source)]}),
            ("escaping watched path", {"watch": ["../outside.txt"]}),
            ("store outside project", {"store": self.root / "outside-store"}),
            ("absolute report path", {"report": str(self.root / "external.xml")}),
            ("escaping report path", {"report": "../external.xml"}),
        ]
        for label, options in cases:
            with self.subTest(label=label):
                sentinel = self.project / ("started-" + uuid.uuid4().hex)
                code = f"from pathlib import Path; Path({str(sentinel)!r}).write_text('ran')"
                process, data = self.invoke(
                    self.record_arguments(code, **options), require_json=False,
                )
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(sentinel.exists())
                self.assertNotEqual(data.get("status"), "verified_tests")

    def test_failed_or_timed_out_child_cannot_verify(self) -> None:
        with self.subTest(reason="nonzero child exit"):
            failed = self.record(xml=junit(), exit_code=7)
            self.assertNotEqual(failed.process.returncode, 0)
            self.assert_not_verified(failed)
        with self.subTest(reason="child timeout"):
            timed_out = self.record(xml=junit(), timeout="0.15", extra_code="time.sleep(2)")
            self.assertNotEqual(timed_out.process.returncode, 0)
            self.assert_not_verified(timed_out)

    def test_verify_requires_positive_minimum_and_safe_record_id(self) -> None:
        run = self.successful_record(xml=junit())
        self.assert_verified(run)
        cases = [(run.record_id, value) for value in ("0", "-1", "1.5", "NaN")]
        cases += [("../project", "1"), (str(self.project), "1"), ("", "1")]
        for record_id, minimum in cases:
            with self.subTest(record_id=record_id, minimum=minimum):
                process, data = self.invoke([
                    "verify", "--project", str(self.project), "--store", str(self.store),
                    "--record", record_id, "--minimum-tests", minimum,
                ], require_json=False)
                self.assertNotEqual(process.returncode, 0)
                self.assertNotEqual(data.get("status"), "verified_tests")

    @staticmethod
    def make_writable(path: Path) -> None:
        path.parent.chmod(0o755)
        path.chmod(0o644)

    def test_modifying_watched_file_invalidates_verification(self) -> None:
        run = self.successful_record(xml=junit(), watch=["input.txt", "other.txt"])
        self.assert_verified(run)
        self.other_source.write_text("modified after recording\n", encoding="utf-8")
        self.assert_not_verified(run)

    def test_modifying_stdout_log_invalidates_verification(self) -> None:
        run = self.successful_record(xml=junit())
        self.assert_verified(run)
        log = self.log_for_marker(run, run.stdout_marker)
        self.make_writable(log)
        log.write_bytes(log.read_bytes() + b"changed stdout\n")
        self.assert_not_verified(run)

    def test_modifying_stderr_log_invalidates_verification(self) -> None:
        run = self.successful_record(xml=junit())
        self.assert_verified(run)
        log = self.log_for_marker(run, run.stderr_marker)
        self.make_writable(log)
        log.write_bytes(log.read_bytes() + b"changed stderr\n")
        self.assert_not_verified(run)

    def test_modifying_report_invalidates_verification(self) -> None:
        for location in ("original", "snapshot"):
            with self.subTest(location=location):
                run = self.successful_record(xml=junit())
                self.assert_verified(run)
                if location == "original":
                    self.assertIsNotNone(run.report_path)
                    report = run.report_path
                else:
                    reports = list(self.record_directory(run).rglob("*.xml"))
                    self.assertEqual(len(reports), 1, "The recorded report must be retained.")
                    report = reports[0]
                self.make_writable(report)
                report.write_bytes(report.read_bytes() + b"\n ")
                self.assert_not_verified(run)

    def test_modifying_metadata_invalidates_verification(self) -> None:
        run = self.successful_record(xml=junit())
        self.assert_verified(run)
        metadata = list(self.record_directory(run).rglob("*.json"))
        self.assertTrue(metadata, "A record must retain its JSON metadata.")
        for path in metadata:
            self.make_writable(path)
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value["independent_test_mutation"] = True
                path.write_text(json.dumps(value), encoding="utf-8")
            else:
                path.write_text("{}", encoding="utf-8")
        self.assert_not_verified(run)

    def test_invalid_and_incomplete_junit_reports_never_verify(self) -> None:
        cases = {
            "missing report": None,
            "malformed XML": '<testsuite tests="1"><testcase></testsuite>',
            "DTD": '<!DOCTYPE testsuite><testsuite tests="1"><testcase name="one" /></testsuite>',
            "entity": (
                '<!DOCTYPE testsuite [<!ENTITY label "expanded">]>'
                '<testsuite tests="1"><testcase name="&label;" /></testsuite>'
            ),
            "zero cases": '<testsuite tests="0" failures="0" errors="0" skipped="0" />',
            "skipped case": (
                '<testsuite tests="1" failures="0" errors="0" skipped="1">'
                '<testcase name="one"><skipped /></testcase></testsuite>'
            ),
            "failed case": (
                '<testsuite tests="1" failures="1" errors="0" skipped="0">'
                '<testcase name="one"><failure message="failed" /></testcase></testsuite>'
            ),
            "error case": (
                '<testsuite tests="1" failures="0" errors="1" skipped="0">'
                '<testcase name="one"><error message="error" /></testcase></testsuite>'
            ),
        }
        for label, xml in cases.items():
            with self.subTest(label=label):
                self.assert_not_verified(self.record(xml=xml))

    def test_actual_testcase_nodes_control_counts_and_declared_counts_must_match(self) -> None:
        one_case = self.successful_record(xml=junit(("only",)))
        self.assert_verified(one_case, minimum=1)
        self.assert_not_verified(one_case, minimum=2)
        cases = [
            '<testsuite tests="2" failures="0" errors="0" skipped="0">'
            '<testcase name="only" /></testsuite>',
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase name="one" /><testcase name="two" /></testsuite>',
            '<testsuite tests="1" failures="1" errors="0" skipped="0">'
            '<testcase name="only" /></testsuite>',
            '<testsuites tests="2" failures="0" errors="0" skipped="0">'
            '<testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase name="only" /></testsuite></testsuites>',
        ]
        for xml in cases:
            with self.subTest(xml=xml):
                self.assert_not_verified(self.record(xml=xml), minimum=1)

    def test_mixed_separator_network_roots_are_rejected_before_filesystem_access(self) -> None:
        specification = importlib.util.spec_from_file_location("reviewed_work_cli", CLI)
        self.assertIsNotNone(specification)
        self.assertIsNotNone(specification.loader)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        for remote in ("/\\server/share", "\\/server/share"):
            for field in ("project", "store"):
                with self.subTest(remote=remote, field=field):
                    project = remote if field == "project" else str(self.project)
                    store = remote if field == "store" else str(self.store)
                    with mock.patch.object(
                        module.Path, "resolve",
                        side_effect=AssertionError("Filesystem access occurred before validation"),
                    ):
                        with self.assertRaises(ValueError):
                            module.roots(project, store)
    def test_child_changes_to_watched_files_cannot_verify(self) -> None:
        mutation = f"Path({str(self.source)!r}).write_text('changed during child', encoding='utf-8')"
        run = self.record(xml=junit(), extra_code=mutation)
        self.assert_not_verified(run)


    def test_huge_finite_timeout_uses_safe_operating_system_waits(self) -> None:
        run = self.successful_record(with_report=False, timeout="1e308")
        self.assertEqual(run.data["status"], "process_ok")

    def test_wait_errors_stop_and_reap_started_child(self) -> None:
        import argparse
        import importlib.util
        from unittest import mock

        spec = importlib.util.spec_from_file_location("verify_cleanup_check", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        child = mock.Mock()
        child.wait.side_effect = [OverflowError("simulated wait failure"), 0]
        child.poll.return_value = None
        arguments = argparse.Namespace(
            project=str(self.project), store=str(self.store), watch=["input.txt"],
            test_report=None, timeout=5.0, command=["--", "mock-command"],
        )
        def reap(process):
            process.kill()
            process.wait()
        with mock.patch.object(module.subprocess, "Popen", return_value=child):
            with mock.patch.object(module, "stop", side_effect=reap) as cleanup:
                result, code = module.record(arguments)
        cleanup.assert_called_once_with(child)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "error")
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
