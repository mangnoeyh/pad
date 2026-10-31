# Local command evidence v1

Requires Python 3.10 or later and only the standard library. Run from any directory;
`--project` and `--store` resolve from that directory. Store must be a strict child
of the existing project directory. All watched and report paths use forward slashes,
relative to the project. At least one existing regular watched file is required.
Project and store must use local filesystem paths; network prefixes and URI forms
are rejected before filesystem access. Watched/report paths reject absolute paths,
parent components, colons (including alternate streams), and escaping symlinks.
Symlinks to watched files inside the project are allowed; report symlinks are not.

```text
python tools/verify_work.py record --project PROJECT --store PROJECT/evidence --watch src/main.py --timeout 60 --test-report results.xml -- python generate_results.py
python tools/verify_work.py verify --project PROJECT --store PROJECT/evidence --record RUN_ID --minimum-tests 5
```

The report must not exist before the command starts, must differ from every watched
file, and must be generated as a regular file. The command runs with the project as
its working directory, without a shell. Timeout must be finite and greater than
zero. Combined stdout and stderr go directly to `output.log`, with bounded memory
use. A timeout terminates and reaps the direct child. On POSIX a new process group
receives termination and kill signals. On Windows descendants can outlive their
parent; only the direct child is stopped. Commands can intentionally escape a POSIX
process group too. This is evidence recording, not command isolation.

Every call writes one JSON object to stdout containing `record_id` and `status`.
Record statuses are `process_ok` (exit zero without test evidence), `tests_ok`
(successful process with positive, complete test evidence), `review` (changed
inputs, absent/invalid/incomplete report, zero tests, or skipped tests), `failed`
(nonzero process exit or test failures/errors), `timeout`, and `error`. Recording
exits zero only for `process_ok` or `tests_ok`; otherwise it exits one, or two for
invalid arguments and other operational errors. The child's actual return code is
preserved in the record, including negative POSIX signal codes.

Verification exits zero only with `verified_tests`: a successful recorded command,
unchanged watched files before/after/now, matching log and report hashes, complete
test results, and a positive explicit `--minimum-tests` that is satisfied. Missing
test evidence or a missing/unsatisfied minimum yields `review` and exit one.
Recorded unsuccessful commands yield `failed`; invalid or inconsistent records
yield `error`. Successful process exit alone never establishes test success.

Each run gets an exclusively created UUID directory containing `record.json`,
`output.log`, and, when available, a `report.xml` snapshot. Runs are never reused or
overwritten. Files and the directory are marked read-only after recording where
the operating system honors those permissions. These are local, unsigned records;
an owner or administrator can rewrite files and recompute hashes. No human
authorization or external acceptance is represented by a status.

The JSON schema identifier is `local-work-evidence/v1`. Its exact top-level fields
are `schema`, `record_id`, `project`, `cwd`, `argv`, `started_at`, `ended_at`,
`timeout`, `returncode`, `timed_out`, `inputs`, `log_sha256`, `test_report`, `errors`,
and `status`. Times are UTC strings ending in `Z`; hashes are lowercase SHA-256.
`inputs` holds objects with exactly `path`, `before`, `after`. Missing final hashes
are null. `test_report` is null or an object with exactly `path`, `sha256`, `counts`,
and `issue`. Counts are null or an object containing integer `tests`, `failures`,
`errors`, `skipped`; issue is null or a diagnostic string. Errors are strings in an
array. Return code is an integer, or null if launching failed. Verification checks
field sets, types, duplicate JSON keys, identifiers, hashes, timestamps, paths, and
the saved status against its underlying evidence.

JUnit input is bounded to 16 MiB and must be UTF-8 XML with a `testsuite` or
`testsuites` root, without DTDs or entity declarations. Counts come from actual
`testcase` nodes, never sums of nested summary attributes. Declared suite counts
are checked against their descendant cases. Skipped/disabled/notrun cases, unknown
execution statuses, inconsistent counts, zero cases, and malformed reports cannot
establish test success. The original report and its snapshot must both remain regular, nonsymlink files with the recorded hash during verification; the snapshot is parsed again.
The verifier can check evidence consistency, not whether a command truthfully
implemented the work its author intended. Files that change and return to their
original bytes between snapshots are outside this mechanism's visibility.