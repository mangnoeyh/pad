#!/usr/bin/env python3
"""Record local command evidence; independently check its files and test report."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

SCHEMA = "local-work-evidence/v1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[0-9a-f]{32}\Z")
FIELDS = {"schema", "record_id", "project", "cwd", "argv", "started_at", "ended_at",
          "timeout", "returncode", "timed_out", "inputs", "log_sha256", "test_report", "errors", "status"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def contained(root, path):
    try:
        path.resolve().relative_to(root)
    except (ValueError, OSError, RuntimeError):
        raise ValueError("Path leaves the project") from None
    return path


def relative(root, value, must_exist=True):
    require(type(value) is str and value and "\\" not in value and "\0" not in value and ":" not in value,
            "Use a nonempty relative path with forward slashes")
    parts = PurePosixPath(value)
    require(not parts.is_absolute() and not PureWindowsPath(value).drive and ".." not in parts.parts,
            "Absolute, network, and parent paths are forbidden")
    path = contained(root, root.joinpath(*parts.parts))
    require(path != root, "A file path is required")
    if must_exist:
        require(stat.S_ISREG(path.stat().st_mode), "Expected a regular file: " + value)
    return path, parts.as_posix()


def roots(project, store, create=False):
    for raw in (project, store):
        require(not raw.replace("\\", "/").startswith("//") and
                (not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) or
                 re.match(r"^[A-Za-z]:[\\/]", raw)), "Project and store must use local filesystem paths")
    project = Path(project).resolve(strict=True)
    require(project.is_dir(), "Project must be an existing directory")
    store = contained(project, Path(store).resolve())
    require(store != project, "Store must be a directory below the project")
    if create:
        store.mkdir(parents=True, exist_ok=True)
    require(store.is_dir(), "Store must be an existing directory")
    return project, store


def digest(path):
    require(stat.S_ISREG(path.stat().st_mode), "Expected a regular evidence file")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def report_info(path):
    with path.open("rb") as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    require(len(data) <= 16 * 1024 * 1024, "Report exceeds 16 MiB")
    source = data.decode("utf-8-sig")
    require("\0" not in source and not re.search(r"<!\s*(DOCTYPE|ENTITY)\b", source, re.I),
            "Report must be UTF-8 XML without DTDs or entities")
    root = ET.fromstring(source)
    tag = lambda node: node.tag.rsplit("}", 1)[-1]
    require(tag(root) in {"testsuite", "testsuites"}, "Expected a JUnit root")
    cases = [node for node in root.iter() if tag(node) == "testcase"]
    parents = {child: parent for parent in root.iter() for child in parent}
    require(all(tag(parents[node]) == "testsuite" for node in cases), "Misplaced testcase")

    def counts(nodes):
        def marked(node, kind, states):
            return any(tag(c) == kind for c in node) or any(node.get(a, "").lower() in states for a in ("status", "result"))
        return {"tests": len(nodes),
                "failures": sum(marked(n, "failure", {"failed", "failure"}) for n in nodes),
                "errors": sum(marked(n, "error", {"error"}) for n in nodes),
                "skipped": sum(marked(n, "skipped", {"notrun", "disabled", "skipped", "suppressed"}) for n in nodes)}

    result, issues = counts(cases), []
    for node in root.iter():
        if tag(node) not in {"testsuite", "testsuites"}:
            continue
        actual = counts([n for n in node.iter() if tag(n) == "testcase"])
        for key in ("tests", "failures", "errors", "skipped", "disabled", "notrun"):
            if key in node.attrib:
                raw = node.attrib[key]
                require(re.fullmatch(r"[0-9]+", raw) is not None, "Invalid JUnit count")
                if (key in actual and int(raw) != actual[key]) or (key not in actual and int(raw)):
                    issues.append("Declared counts indicate incomplete or inconsistent execution")
    known = {"", "run", "completed", "passed", "success", "failed", "failure", "error", "skipped", "disabled", "notrun", "suppressed"}
    if any(n.get(a, "").lower() not in known for n in cases for a in ("status", "result")):
        issues.append("Unknown testcase execution status")
    return result, "; ".join(sorted(set(issues))) or None


def outcome(record):
    if record["errors"] or record["returncode"] is None or record["log_sha256"] is None:
        return "error"
    if record["timed_out"]:
        return "timeout"
    if record["returncode"] != 0:
        return "failed"
    if any(i["after"] is None or i["before"] != i["after"] for i in record["inputs"]):
        return "review"
    report = record["test_report"]
    if report is None:
        return "process_ok"
    counts = report["counts"]
    if counts and (counts["failures"] or counts["errors"]):
        return "failed"
    if report["issue"] or not report["sha256"] or not counts or counts["tests"] == 0 or counts["skipped"]:
        return "review"
    return "tests_ok"


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def stop(child):
    if os.name == "posix":
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
            if sig == signal.SIGTERM:
                try:
                    child.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
    else:
        try:
            child.kill()
        except ProcessLookupError:
            pass
    child.wait()



def wait_for(child, timeout):
    started = time.monotonic()
    while True:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(child.args, timeout)
        try:
            return child.wait(timeout=min(remaining, 60.0))
        except subprocess.TimeoutExpired:
            if timeout - (time.monotonic() - started) <= 0:
                raise


def record(args):
    require(math.isfinite(args.timeout) and args.timeout > 0, "Timeout must be finite and positive")
    require(args.command and args.command[0] == "--" and len(args.command) > 1,
            "Put command arguments after --")
    project, store = roots(args.project, args.store, True)
    inputs, seen = [], set()
    for raw in args.watch:
        path, name = relative(project, raw)
        require(path.resolve() not in seen, "Duplicate watched file")
        seen.add(path.resolve())
        inputs.append({"path": name, "before": digest(path), "after": None})
    report = None
    if args.test_report:
        path, name = relative(project, args.test_report, False)
        require(path.resolve() not in seen, "Report cannot be a watched file")
        require(not path.exists() and not path.is_symlink(), "Report already exists; choose a new report path")
        report = {"path": name, "sha256": None, "counts": None, "issue": None}
    run_id = uuid.uuid4().hex
    run = store / run_id
    run.mkdir()  # Exclusive allocation: no previous run is reused.
    args.record = run_id
    data = dict(schema=SCHEMA, record_id=run_id, project=str(project), cwd=str(project),
                argv=args.command[1:], started_at=utc(), ended_at=None, timeout=args.timeout,
                returncode=None, timed_out=False, inputs=inputs, log_sha256=None,
                test_report=report, errors=[], status=None)
    try:
        with (run / "output.log").open("xb") as log:
            child = subprocess.Popen(data["argv"], cwd=project, stdout=log, stderr=subprocess.STDOUT,
                                     shell=False, start_new_session=os.name == "posix")
            try:
                data["returncode"] = wait_for(child, args.timeout)
            except subprocess.TimeoutExpired:
                data["timed_out"] = True
                stop(child)
                data["returncode"] = child.returncode
            except BaseException:
                if child.poll() is None:
                    stop(child)
                raise
            log.flush()
            os.fsync(log.fileno())
    except (OSError, ValueError, OverflowError) as exc:
        data["errors"].append("Command or log error: " + str(exc))
    data["ended_at"] = utc()
    try:
        require(not (run / "output.log").is_symlink(), "Log was replaced by a symlink")
        data["log_sha256"] = digest(run / "output.log")
    except (OSError, ValueError) as exc:
        data["errors"].append("Log error: " + str(exc))
    for item in inputs:
        try:
            item["after"] = digest(relative(project, item["path"])[0])
        except (OSError, ValueError, RuntimeError) as exc:
            data["errors"].append("Input error: " + str(exc))
    if report is not None:
        try:
            path = relative(project, report["path"])[0]
            require(not path.is_symlink(), "Report cannot be a symlink")
            with path.open("rb") as src, (run / "report.xml").open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            report["sha256"] = digest(run / "report.xml")
            report["counts"], report["issue"] = report_info(run / "report.xml")
        except (OSError, ValueError, RuntimeError, ET.ParseError) as exc:
            report["issue"] = "Report error: " + str(exc)
    data["status"] = outcome(data)
    with (run / "record.json").open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")
    for path in run.iterdir():
        path.chmod(0o444)
    run.chmod(0o555)
    return {"record_id": run_id, "status": data["status"]}, 0 if data["status"] in {"process_ok", "tests_ok"} else 1


def schema(data, run_id, project):
    require(type(data) is dict and set(data) == FIELDS, "Unknown or missing record fields")
    require(data["schema"] == SCHEMA and data["record_id"] == run_id, "Wrong schema or record identifier")
    require(data["project"] == str(project) and data["cwd"] == str(project), "Project mismatch")
    require(type(data["argv"]) is list and data["argv"] and
            all(type(a) is str and "\0" not in a for a in data["argv"]) and data["argv"][0], "Invalid argv")
    require(type(data["timeout"]) in {int, float} and math.isfinite(data["timeout"]) and data["timeout"] > 0,
            "Invalid timeout")
    require(data["returncode"] is None or type(data["returncode"]) is int, "Invalid return code")
    require(type(data["timed_out"]) is bool and type(data["errors"]) is list and
            all(type(e) is str for e in data["errors"]), "Invalid result fields")
    times = [dt.datetime.strptime(data[k], "%Y-%m-%dT%H:%M:%S.%fZ") for k in ("started_at", "ended_at")]
    require(times[1] >= times[0], "Invalid timestamp order")
    hash_ok = lambda h: type(h) is str and HEX.fullmatch(h) is not None
    require(data["log_sha256"] is None or hash_ok(data["log_sha256"]), "Invalid log hash")
    require(type(data["inputs"]) is list and data["inputs"], "Missing watched inputs")
    seen = set()
    for item in data["inputs"]:
        require(type(item) is dict and set(item) == {"path", "before", "after"}, "Invalid input fields")
        path, name = relative(project, item["path"])
        require(name == item["path"] and path.resolve() not in seen, "Duplicate or noncanonical input")
        seen.add(path.resolve())
        require(hash_ok(item["before"]) and (item["after"] is None or hash_ok(item["after"])), "Invalid input hashes")
    report = data["test_report"]
    if report is not None:
        require(type(report) is dict and set(report) == {"path", "sha256", "counts", "issue"}, "Invalid report fields")
        path, name = relative(project, report["path"], False)
        require(name == report["path"] and path.resolve() not in seen, "Invalid report path")
        require(report["sha256"] is None or hash_ok(report["sha256"]), "Invalid report hash")
        require(report["issue"] is None or type(report["issue"]) is str, "Invalid report issue")
        counts = report["counts"]
        require(counts is None or (type(counts) is dict and set(counts) == {"tests", "failures", "errors", "skipped"}
                and all(type(n) is int and n >= 0 for n in counts.values())), "Invalid test counts")
        require(report["sha256"] is not None or (counts is None and report["issue"]), "Missing report evidence")
    require(type(data["status"]) is str and data["status"] == outcome(data), "Inconsistent saved status")


def verify(args):
    require(ID.fullmatch(args.record) is not None, "Invalid record identifier")
    require(args.minimum_tests is None or args.minimum_tests > 0, "Minimum tests must be positive")
    project, store = roots(args.project, args.store)
    run = contained(project, store / args.record)
    require(not run.is_symlink() and run.is_dir(), "Invalid run directory")
    record_path = run / "record.json"
    require(not record_path.is_symlink() and stat.S_ISREG(record_path.stat().st_mode), "Invalid record file")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON field")
            result[key] = value
        return result
    with record_path.open(encoding="utf-8") as stream:
        source = stream.read(1024 * 1024 + 1)
    require(len(source) <= 1024 * 1024, "Record exceeds 1 MiB")
    data = json.loads(source, object_pairs_hook=pairs, parse_constant=lambda _: require(False, "Nonfinite JSON"))
    schema(data, args.record, project)
    watched = {relative(project, item["path"])[0].resolve() for item in data["inputs"]}
    required = set()
    for raw in args.require_watch:
        path, name = relative(project, raw)
        resolved = path.resolve()
        require(resolved not in required, "Duplicate required watched file")
        required.add(resolved)
        require(resolved in watched,
                "Required file was not watched in recorded run: " + name + "; record a new run with --watch")
    log = run / "output.log"
    require(not log.is_symlink() and digest(log) == data["log_sha256"], "Log hash mismatch")
    for item in data["inputs"]:
        require(item["before"] == item["after"] == digest(relative(project, item["path"])[0]),
                "Watched input changed: " + item["path"])
    report = data["test_report"]
    if report and report["sha256"] is not None:
        original = relative(project, report["path"])[0]
        require(not original.is_symlink() and digest(original) == report["sha256"], "Original report hash mismatch")
        saved = run / "report.xml"
        require(not saved.is_symlink() and digest(saved) == report["sha256"], "Report hash mismatch")
        try:
            counts, issue = report_info(saved)
        except (ValueError, ET.ParseError):
            require(data["status"] != "tests_ok" and report["counts"] is None and report["issue"], "Invalid report evidence")
        else:
            require(counts == report["counts"] and issue == report["issue"], "Report summary mismatch")
    status = "review"
    reason = "Test verification requires a valid report and --minimum-tests"
    if data["status"] in {"error", "timeout", "failed"}:
        status, reason = "failed", "Recorded command did not succeed"
    elif data["status"] == "tests_ok" and args.minimum_tests is not None:
        if report["counts"]["tests"] >= args.minimum_tests:
            status, reason = "verified_tests", "Current files, log, and executed test evidence match"
        else:
            reason = "Fewer tests executed than the required minimum"
    return {"record_id": args.record, "status": status, "reason": reason}, 0 if status == "verified_tests" else 1


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("record", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("--project", required=True)
        sub.add_argument("--store", required=True)
        if name == "record":
            sub.add_argument("--watch", action="append", required=True)
            sub.add_argument("--test-report")
            sub.add_argument("--timeout", type=float, required=True)
            sub.add_argument("command", nargs=argparse.REMAINDER)
        else:
            sub.add_argument("--record", required=True)
            sub.add_argument("--minimum-tests", type=int)
            sub.add_argument("--require-watch", action="append", default=[],
                             help="Require this current dependency to have been watched in the recorded run (repeatable)")
    args = None
    try:
        args = parser.parse_args()
        output, code = record(args) if args.operation == "record" else verify(args)
    except (OSError, ValueError, TypeError, RuntimeError, OverflowError, ET.ParseError) as exc:
        output, code = {"record_id": getattr(args, "record", None), "status": "error", "reason": str(exc)}, 2
    print(json.dumps(output, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
