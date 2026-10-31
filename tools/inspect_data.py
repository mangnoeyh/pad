#!/usr/bin/env python3
"""Inspect a bounded prefix of a local table without modifying the input."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None

DEFAULT_MAX_ROWS = 100_000
MAX_JSON_RECORD_BYTES = 16 * 1024 * 1024
FORMATS = ("auto", "csv", "tsv", "excel", "json", "jsonl", "parquet")


class DataToolError(ValueError):
    """An input, dependency, or output error suitable for a CLI message."""


@dataclass
class TableRead:
    data: Any
    source: Path
    format: str
    total_rows: int | None
    max_rows: int
    sheet: str | int | None = None

    @property
    def sampled(self) -> bool:
        return self.total_rows is None or len(self.data) < self.total_rows

    def scope(self) -> dict[str, Any]:
        return {
            "max_rows": self.max_rows, "rows_read": len(self.data),
            "total_rows": self.total_rows, "exact_row_count": self.total_rows is not None,
            "sampled": self.sampled, "sampling_method": "first_rows" if self.sampled else "all_rows",
            "note": ("Statistics describe only the first rows, not a random sample. The uninspected suffix has not been validated."
                     if self.sampled else "Statistics describe all parsed data rows."),
        }


def local_path(value: str | Path, *, must_exist: bool = True) -> Path:
    """Reject URLs and network shares before a library can interpret a path."""
    raw = str(value)
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) and not re.match(r"^[A-Za-z]:[\\/]", raw):
        raise DataToolError("Only local filesystem paths are supported; URLs are not allowed.")
    if raw.startswith(("\\\\", "//")) or "://" in raw:
        raise DataToolError("Only local filesystem paths are supported; network paths are not allowed.")
    try:
        path = Path(raw).expanduser().resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise DataToolError(f"Cannot access local path {raw!r}: {exc}") from exc
    if str(path).startswith(("\\\\", "//")):
        raise DataToolError("Resolved network paths are not allowed.")
    if must_exist and not path.is_file():
        raise DataToolError(f"Input is not a regular file: {path}")
    return path


def guard_output(path: str | Path, source: Path, *, overwrite: bool = False) -> Path:
    target = local_path(path, must_exist=False)
    same_file = target == source
    if target.exists():
        try:
            same_file = same_file or target.samefile(source)
        except OSError:
            pass
    if same_file:
        raise DataToolError("Output must not overwrite the input file.")
    if target.exists() and not overwrite:
        raise DataToolError(f"Output already exists: {target}. Use --overwrite to replace it.")
    if target.exists() and not target.is_file():
        raise DataToolError(f"Output is not a regular file: {target}")
    return target


def write_text(path: Path, text: str, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class _JSONStream:
    """Incremental JSON reader with a bounded record buffer."""
    def __init__(self, handle: Any):
        self.handle, self.buffer, self.position, self.eof = handle, "", 0, False
        self.decoder = json.JSONDecoder()

    def _more(self) -> None:
        self.buffer, self.position = self.buffer[self.position:], 0
        block = self.handle.read(65536)
        if not block:
            self.eof = True
        self.buffer += block
        if len(self.buffer.encode("utf-8")) > MAX_JSON_RECORD_BYTES + 65536:
            raise DataToolError("JSON record exceeds the 16 MiB safety limit; use smaller records or JSONL.")

    def peek(self) -> str:
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer):
                return self.buffer[self.position]
            if self.eof:
                return ""
            self._more()

    def consume(self, expected: str) -> None:
        if self.peek() != expected:
            raise DataToolError(f"Malformed JSON: expected {expected!r}.")
        self.position += 1

    def value(self) -> Any:
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                self.position = end
                return value
            except json.JSONDecodeError as exc:
                if self.eof:
                    raise DataToolError(f"Malformed JSON: {exc.msg}.") from exc
                self._more()

    def finish(self) -> None:
        if self.peek():
            raise DataToolError("Malformed JSON: unexpected content after the JSON value.")


def _read_json(path: Path, limit: int, encoding: str) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    with path.open(encoding=encoding) as handle:
        stream = _JSONStream(handle)
        first = stream.peek()
        if not first:
            return records, True
        if first == "{":
            record = stream.value()
            stream.finish()
            return [record], True
        if first != "[":
            raise DataToolError("JSON must be an array of objects or one object; use --format jsonl for JSON Lines.")
        stream.consume("[")
        if stream.peek() == "]":
            stream.consume("]")
            stream.finish()
            return records, True
        while True:
            record = stream.value()
            if not isinstance(record, dict):
                raise DataToolError("Each JSON array item must be an object.")
            records.append(record)
            if len(records) >= limit:
                return records, False
            delimiter = stream.peek()
            if delimiter == "]":
                stream.consume("]")
                stream.finish()
                return records, True
            if delimiter != ",":
                raise DataToolError("Malformed JSON: expected ',' or ']' after an object.")
            stream.consume(",")
            if stream.peek() == "]":
                raise DataToolError("Malformed JSON: trailing commas are not allowed.")


def _read_jsonl(path: Path, limit: int, encoding: str) -> tuple[list[dict[str, Any]], bool]:
    records = []
    with path.open(encoding=encoding) as handle:
        line_number = 0
        while True:
            line = handle.readline(MAX_JSON_RECORD_BYTES + 1)
            if not line:
                break
            line_number += 1
            if len(line) > MAX_JSON_RECORD_BYTES:
                raise DataToolError(f"JSONL line {line_number} exceeds the 16 MiB record limit.")
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > MAX_JSON_RECORD_BYTES:
                raise DataToolError(f"JSONL line {line_number} exceeds the 16 MiB record limit.")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataToolError(f"Malformed JSONL at line {line_number}: {exc.msg}.") from exc
            if not isinstance(record, dict):
                raise DataToolError(f"JSONL line {line_number} must contain one object.")
            records.append(record)
            if len(records) >= limit:
                return records, False
    return records, True


def detect_format(path: Path, requested: str = "auto") -> str:
    if requested not in FORMATS:
        raise DataToolError(f"Unsupported format: {requested}")
    if requested != "auto":
        return requested
    mapping = {".csv": "csv", ".tsv": "tsv", ".tab": "tsv", ".xlsx": "excel", ".xls": "excel",
               ".xlsm": "excel", ".xlsb": "excel", ".ods": "excel", ".json": "json",
               ".jsonl": "jsonl", ".ndjson": "jsonl", ".parquet": "parquet", ".pq": "parquet"}
    try:
        return mapping[path.suffix.lower()]
    except KeyError as exc:
        raise DataToolError("Cannot infer table format from the filename; specify --format.") from exc


def _validate_delimited_header(path: Path, delimiter: str, encoding: str) -> None:
    """Check original names before pandas can silently rename duplicate/empty headers."""
    with path.open(encoding=encoding, newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter, strict=True)
        header = next((row for row in reader if row), None)
    if header is None:
        return
    header[0] = header[0].lstrip("\ufeff")
    if any(not name.strip() for name in header):
        raise DataToolError("CSV/TSV header contains an empty column name; provide explicit non-empty names.")
    seen = set()
    duplicates = []
    for name in header:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        names = ", ".join(repr(name) for name in duplicates)
        raise DataToolError(f"CSV/TSV header contains duplicate column names: {names}. Rename them explicitly before inspection.")


def read_local_table(input_path: str | Path, *, max_rows: int = DEFAULT_MAX_ROWS,
                     format: str = "auto", encoding: str = "utf-8-sig", sheet: str | int = 0) -> TableRead:
    if pd is None:
        raise DataToolError("pandas is required. Install the toolkit's core requirements in the permitted environment.")
    if max_rows < 1:
        raise DataToolError("--max-rows must be a positive integer.")
    path = local_path(input_path)
    kind, limit, total = detect_format(path, format), max_rows + 1, None
    try:
        if kind in ("csv", "tsv"):
            _validate_delimited_header(path, "\t" if kind == "tsv" else ",", encoding)
            try:
                frame = pd.read_csv(path, sep="\t" if kind == "tsv" else ",", encoding=encoding, nrows=limit, on_bad_lines="error")
            except pd.errors.EmptyDataError:
                frame = pd.DataFrame()
            if len(frame) < limit:
                total = len(frame)
        elif kind == "excel":
            frame = pd.read_excel(path, sheet_name=sheet, nrows=limit)
            if len(frame) < limit:
                total = len(frame)
        elif kind in ("json", "jsonl"):
            records, complete = (_read_json if kind == "json" else _read_jsonl)(path, limit, encoding)
            frame = pd.DataFrame.from_records(records)
            if complete:
                total = len(frame)
        else:
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise DataToolError("Bounded Parquet inspection requires optional pyarrow.") from exc
            parquet = pq.ParquetFile(path)
            total, batches, count = parquet.metadata.num_rows, [], 0
            for batch in parquet.iter_batches(batch_size=min(8192, limit)):
                batches.append(batch.slice(0, limit - count))
                count += batches[-1].num_rows
                if count >= limit:
                    break
            frame = pa.Table.from_batches(batches, schema=parquet.schema_arrow).to_pandas()
    except DataToolError:
        raise
    except ImportError as exc:
        raise DataToolError(f"Missing optional reader dependency for {kind}: {exc}") from exc
    except Exception as exc:
        raise DataToolError(f"Cannot read {kind} input {path.name!r}: {exc}") from exc
    return TableRead(frame.iloc[:max_rows].copy(), path, kind, total, max_rows, sheet if kind == "excel" else None)


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            return _json_value(value.item())
        except (ValueError, TypeError):
            pass
    if isinstance(value, (str, int, bool)):
        return value
    try:
        if pd is not None and pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    return str(value)


def _hashable(series: Any) -> Any:
    return series.map(lambda item: json.dumps(_json_value(item), ensure_ascii=False, sort_keys=True))


def profile_table(table: TableRead) -> dict[str, Any]:
    frame, profiles = table.data, []
    row_count = len(frame)
    for position, column in enumerate(frame.columns):
        series = frame.iloc[:, position]
        missing, valid = int(series.isna().sum()), series.dropna()
        try:
            unique, frequencies = int(valid.nunique()), valid.value_counts().head(5)
        except TypeError:
            normalized = _hashable(valid)
            unique, frequencies = int(normalized.nunique()), normalized.value_counts().head(5)
        record = {"name": str(column), "dtype": str(series.dtype), "non_null": row_count - missing,
                  "missing": missing, "missing_percent": round(100 * missing / row_count, 4) if row_count else 0.0,
                  "unique_non_null": unique,
                  "top_values": [{"value": _json_value(value), "count": int(count)} for value, count in frequencies.items()]}
        if pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(series.dtype):
            record["kind"] = "numeric"
            numeric = valid.replace([float("inf"), float("-inf")], float("nan")).dropna()
            record["non_finite"] = len(valid) - len(numeric)
            record["statistics"] = {name: _json_value(getattr(numeric, name)()) if len(numeric) else None for name in ("min", "max", "mean", "median")}
        elif pd.api.types.is_datetime64_any_dtype(series.dtype):
            record["kind"] = "datetime"
            record["statistics"] = {"min": _json_value(valid.min()) if len(valid) else None, "max": _json_value(valid.max()) if len(valid) else None}
        else:
            record["kind"], record["statistics"] = "categorical_or_text", {}
        profiles.append(record)
    try:
        duplicates = int(frame.duplicated().sum()) if len(frame.columns) else 0
    except TypeError:
        duplicates = int(frame.apply(_hashable).duplicated().sum())
    warnings = []
    if table.sampled:
        warnings.append("Prefix only: aggregate statistics and duplicate counts are not whole-file statistics.")
    if row_count == 0:
        warnings.append("The parsed table has no data rows.")
    if not len(frame.columns):
        warnings.append("The parsed table has no columns.")
    warnings.append("The row limit bounds materialized rows, not file bytes, record width, or every reader's internal parsing cost.")
    return {"source": str(table.source), "format": table.format, "sheet": table.sheet,
            "generated_at": datetime.now(timezone.utc).isoformat(), "scope": table.scope(),
            "columns": len(frame.columns), "missing_cells": int(frame.isna().sum().sum()),
            "duplicate_rows": duplicates, "column_profiles": profiles, "warnings": warnings}


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_markdown(profile: dict[str, Any]) -> str:
    scope = profile["scope"]
    total = scope["total_rows"] if scope["exact_row_count"] else "unknown (prefix read only)"
    lines = ["# Local data profile", "", f"Source: `{_md(profile['source'])}`", "",
             f"- Format: {profile['format']}", f"- Rows inspected: {scope['rows_read']}", f"- Total parsed rows: {total}",
             f"- Sampled: {str(scope['sampled']).lower()}", f"- Columns: {profile['columns']}",
             f"- Missing cells in inspected rows: {profile['missing_cells']}", f"- Duplicate rows in inspected rows: {profile['duplicate_rows']}",
             "", scope["note"], "", "| Column | Type | Missing | Missing % | Unique non-null | Numeric / datetime summary |",
             "| --- | --- | ---: | ---: | ---: | --- |"]
    for column in profile["column_profiles"]:
        summary = "; ".join(f"{key}={value}" for key, value in column["statistics"].items())
        lines.append(f"| {_md(column['name'])} | {_md(column['dtype'])} | {column['missing']} | {column['missing_percent']} | {column['unique_non_null']} | {_md(summary)} |")
    lines += ["", "Notes:", ""] + [f"- {warning}" for warning in profile["warnings"]]
    return "\n".join(lines) + "\n"


def add_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", help="Local table; URLs, network shares, and stdin are unsupported.")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS, help="Maximum rows profiled (default: 100000); one extra row detects truncation.")
    parser.add_argument("--format", choices=FORMATS, default="auto")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV/JSON text encoding (default: utf-8-sig).")
    parser.add_argument("--sheet", default="0", help="Excel worksheet name or zero-based index (default: 0).")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output files; never the input.")


def read_from_args(args: Any) -> TableRead:
    sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
    return read_local_table(args.input, max_rows=args.max_rows, format=args.format, encoding=args.encoding, sheet=sheet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_arguments(parser)
    parser.add_argument("--output-dir", required=True, help="Write profile.json and profile.md to this local directory.")
    args = parser.parse_args(argv)
    try:
        source, directory = local_path(args.input), local_path(args.output_dir, must_exist=False)
        targets = [guard_output(directory / name, source, overwrite=args.overwrite) for name in ("profile.json", "profile.md")]
        profile = profile_table(read_from_args(args))
        payloads = [json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False) + "\n", render_markdown(profile)]
        for path, payload in zip(targets, payloads):
            write_text(path, payload, overwrite=args.overwrite)
        print(json.dumps({"scope": profile["scope"], "outputs": [str(path) for path in targets]}, ensure_ascii=False))
        return 0
    except (DataToolError, OSError, LookupError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
