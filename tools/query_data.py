#!/usr/bin/env python3
"""Run one read-only SELECT over a bounded local table registered as data."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

if __package__:
    from .inspect_data import DataToolError, add_input_arguments, guard_output, local_path, read_from_args, write_text
else:
    from inspect_data import DataToolError, add_input_arguments, guard_output, local_path, read_from_args, write_text


def _select_body(sql: str, duckdb: Any) -> str:
    """Trim only terminal delimiter tokens; tokenizer offsets are UTF-8 bytes."""
    encoded = sql.encode("utf-8")
    end = len(encoded)
    for position, kind in reversed(duckdb.tokenize(sql)):
        if kind == duckdb.token_type.comment:
            continue
        if kind == duckdb.token_type.operator and encoded[position:position + 1] == b";":
            end = position
            continue
        break
    return encoded[:end].decode("utf-8")


def query_table(table: Any, sql: str, *, max_result_rows: int = 10_000) -> tuple[Any, dict[str, Any]]:
    try:
        import duckdb
    except ImportError as exc:
        raise DataToolError("Optional duckdb is required for SQL queries; install requirements-core.txt in the permitted environment.") from exc
    if max_result_rows < 1:
        raise DataToolError("--max-result-rows must be a positive integer.")
    connection = duckdb.connect(":memory:", config={"enable_external_access": "false", "allow_unsigned_extensions": "false"})
    try:
        statements = connection.extract_statements(sql)
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
            raise DataToolError("Provide exactly one SELECT (or WITH ... SELECT) statement over data.")
        connection.register("data", table.data)
        query = _select_body(sql, duckdb)
        # A newline also keeps a final line comment from swallowing the wrapper.
        result = connection.execute(f"SELECT * FROM (\n{query}\n) AS analysis_query LIMIT {max_result_rows + 1}").fetchdf()
        if len(result) > max_result_rows:
            raise DataToolError(f"Query returned more than {max_result_rows} rows. Add SQL LIMIT or raise --max-result-rows; no output was written.")
        metadata = {"input_scope": table.scope(), "result_rows": len(result), "result_columns": len(result.columns), "external_access": False}
        return result, metadata
    except DataToolError:
        raise
    except Exception as exc:
        raise DataToolError(f"SQL query failed: {exc}") from exc
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_arguments(parser)
    parser.add_argument("--sql", required=True, help="Exactly one SELECT or WITH ... SELECT; the input table is named data.")
    parser.add_argument("--output", required=True, help="Local .csv, .json, or .jsonl output file.")
    parser.add_argument("--max-result-rows", type=int, default=10_000)
    args = parser.parse_args(argv)
    try:
        source = local_path(args.input)
        output = guard_output(args.output, source, overwrite=args.overwrite)
        suffix = output.suffix.lower()
        if suffix not in (".csv", ".json", ".jsonl", ".ndjson"):
            raise DataToolError("Query output must end in .csv, .json, .jsonl, or .ndjson.")
        table = read_from_args(args)
        result, metadata = query_table(table, args.sql, max_result_rows=args.max_result_rows)
        if suffix == ".csv":
            payload = result.to_csv(index=False)
        else:
            payload = result.to_json(orient="records", date_format="iso", force_ascii=False, lines=suffix in (".jsonl", ".ndjson"), indent=2 if suffix == ".json" else None)
            if not payload.endswith("\n"):
                payload += "\n"
        write_text(output, payload, overwrite=args.overwrite)
        metadata["output"] = str(output)
        print(json.dumps(metadata, ensure_ascii=False))
        if table.sampled:
            print("Warning: the query ran on the input prefix only; its aggregates are not whole-file aggregates.", file=sys.stderr)
        return 0
    except (DataToolError, OSError, LookupError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
