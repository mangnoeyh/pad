# Local delivery review

Python 3.9+ standard library only. No commands, network, models, or project configuration are executed.

```
python tools/review_delivery.py capture --project DIR --plan plan.json --receipt receipt-v1.json
python tools/review_delivery.py check --project DIR --plan plan.json --receipt receipt-v1.json
```

Capture creates a receipt exclusively. Existing receipts are never overwritten; choose a new versioned filename. The parent directory must already exist. Check never writes. Both commands print one JSON object with `state`, `message`, and, on success, `files`. Exit codes: `0` ready; `1` review for missing, stale, unexpected, empty, or malformed output files; `2` error for invalid inputs, schemas, paths, limits, or filesystem failures. Argument syntax errors use argparse's exit code 2.

Plan example:

```json
{"version":1,"sources":["src/main.py","qa.txt"],"outputs":[{"path":"delivery/report.json","format":"json","nonempty":true},{"path":"delivery/results.csv","format":"csv","nonempty":true,"columns":["name","value"],"minimum_rows":1}],"delivery_root":"delivery","allowed_extra_files":["delivery/readme.txt"]}
```

Only these keys are accepted. Sources and outputs are nonempty lists of unique, disjoint files. `nonempty` is required and boolean. Formats are `text` (UTF-8), `json` (UTF-8, no duplicate keys or nonfinite constants), `csv` (UTF-8, strict parsing, unique nonblank header and consistent row width), and `file` (bytes). CSV `columns` specifies exact header order; `minimum_rows` counts data rows and must be an integer at least zero. Empty CSV is permitted only when nonempty is false and no header or row constraint requires content. Boolean integers are rejected. JSON output must always parse, even when nonempty is false.

All internal paths use forward slashes with no empty, dot, parent, absolute, colon, or backslash components. URI and network project prefixes are rejected before filesystem access. Symbolic links in configured paths are rejected. Plan, sources, and outputs must be regular files. Plan and receipt paths cannot overlap configured files or each other. The receipt must stay outside `delivery_root` to avoid recording itself. No implicit path normalization is performed.

The optional existing `delivery_root` is scanned recursively and read only. Every actual file, including hidden files and names mentioned by ignore files, must be a declared output under that folder or an exact `allowed_extra_files` entry. Allowed extra files are optional and are not hashed. Extra directories alone are allowed; symbolic links and special filesystem objects are rejected. Outputs outside the delivery folder are still validated and hashed.

`delivery_root` must name a strict subfolder; `.` is unsupported. Omit this option when only the listed files should be checked. A review of every file in the project root requires separate manual inspection. JSON, text, and CSV accept an optional UTF-8 byte order mark; hashes always cover the original bytes, including that mark. NUL characters are rejected in all paths before those paths reach filesystem operations.

Limits: plan and receipt at most 1 MiB each; each source/output at most 16 MiB; configured bytes including plan at most 64 MiB; at most 128 distinct configured files including optional extra names. Delivery scanning is additionally bounded to 128 directory entries, counting directories. Reads use a maximum-size buffer plus one byte to detect overflow.

Receipt schema is exactly `{"version":1,"project":"absolute local directory","plan":"plan.json","files":{"relative/path":"64 lowercase hex SHA-256 characters"}}`. The files map covers every source, every output, and the plan itself. Capture and check hash these files before and after format and delivery checks and reject observed changes. Check requires both snapshots to match the receipt. Editing any recorded source, report, quality notes, or plan makes that receipt stale. Receipts are editable local records and are not signatures.

Ready means the configured current disk bytes passed these checks. It does not establish approval, factual or semantic correctness, successful tests, unsaved editor buffers, application UI state, or receipt by another person. A file changing and reverting between observations cannot be detected. Additional edits after completion require another check.
