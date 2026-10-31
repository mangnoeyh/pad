"""Run local unittest discovery and create an exclusive JUnit XML report."""

import argparse
import os
from pathlib import Path, PureWindowsPath
import sys
import time
import unittest
import xml.etree.ElementTree as ET


class ExportResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases, self.current = [], None

    def startTest(self, test):
        super().startTest(test)
        self.current = {"id": test.id(), "time": time.perf_counter(), "outcomes": []}
        self.cases.append(self.current)

    def stopTest(self, test):
        self.current["time"] = time.perf_counter() - self.current["time"]
        self.current = None
        super().stopTest(test)

    def outcome(self, test, kind, detail):
        record = self.current
        if record is None:
            record = {"id": test.id(), "time": 0, "outcomes": []}
            self.cases.append(record)
        record["outcomes"].append((kind, detail))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcome(test, "failure", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.outcome(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcome(test, "skipped", str(reason))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcome(test, "skipped", "Expected failure:\n" + self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcome(test, "failure", "Unexpected success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            kind = "failure" if issubclass(err[0], test.failureException) else "error"
            self.outcome(test, kind, subtest.id() + "\n" + self._exc_info_to_string(err, test))


def report_path(value):
    relative, windows = Path(value), PureWindowsPath(value)
    if (not value or relative.is_absolute() or windows.drive or windows.root or ":" in value
            or ".." in relative.parts or ".." in windows.parts):
        raise ValueError("report must be a relative path without parent traversal")
    root = Path.cwd().resolve()
    candidate = root / relative
    candidate.resolve().relative_to(root)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.parent.resolve().relative_to(root)
    return candidate


def xml_safe(text):
    return "".join(c if c in "\t\n\r" or 32 <= ord(c) <= 0xD7FF
                   or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
                   else "\\u%04x" % ord(c) for c in text)


def xml_report(result):
    counts = {kind: sum(any(k == kind for k, _ in c["outcomes"]) for c in result.cases)
              for kind in ("failure", "error", "skipped")}
    suite = ET.Element("testsuite", name="unittest", tests=str(len(result.cases)),
                       failures=str(counts["failure"]), errors=str(counts["error"]),
                       skipped=str(counts["skipped"]))
    for record in result.cases:
        classname, _, name = xml_safe(record["id"]).rpartition(".")
        case = ET.SubElement(suite, "testcase", classname=classname, name=name,
                             time="%.6f" % record["time"])
        for kind, detail in record["outcomes"]:
            detail = xml_safe(detail)
            ET.SubElement(case, kind, message=detail.splitlines()[0] if detail else kind).text = detail
    if not result.cases:
        ET.SubElement(suite, "system-err").text = "No tests were discovered."
    return ET.ElementTree(suite)


class DiscoveryError(unittest.TestCase):
    def __init__(self, error):
        super().__init__("runTest")
        self.error = error

    def runTest(self):
        raise self.error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args(argv)
    try:
        if args.tests.replace("\\", "/").startswith("//") or not Path(args.tests).is_dir():
            raise ValueError("tests must name an existing local directory")
        destination = report_path(args.report)
        with destination.open("xb") as output:
            sys.path.insert(0, str(Path.cwd().resolve()))
            try:
                suite = unittest.TestLoader().discover(args.tests, pattern=args.pattern)
            except Exception as error:
                suite = unittest.TestSuite([DiscoveryError(error)])
            result = unittest.TextTestRunner(verbosity=2, resultclass=ExportResult).run(suite)
            xml_report(result).write(output, encoding="utf-8", xml_declaration=True)
            output.flush()
            os.fsync(output.fileno())
        return 1 if not result.wasSuccessful() else (0 if result.testsRun else 3)
    except (OSError, ValueError, RuntimeError) as error:
        print("Report or discovery error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
