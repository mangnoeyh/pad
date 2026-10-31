import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.inspect_data import DataToolError, guard_output, local_path, main, profile_table, read_local_table, render_markdown

ROOT = Path(__file__).resolve().parents[1]


class InspectDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-inspect-", dir=ROOT)
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def source(self, text, name="data.csv"):
        path = self.directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_values_duplicates_and_numeric_statistics(self):
        source = self.source("group,value\na,1\na,1\nb,\n")
        before = source.read_bytes()
        report = profile_table(read_local_table(source))
        self.assertEqual(report["scope"]["total_rows"], 3)
        self.assertEqual(report["duplicate_rows"], 1)
        self.assertEqual(report["missing_cells"], 1)
        self.assertEqual(report["column_profiles"][1]["statistics"]["mean"], 1)
        self.assertFalse(report["scope"]["sampled"])
        self.assertEqual(source.read_bytes(), before)
        json.dumps(report, allow_nan=False)

    def test_prefix_is_not_reported_as_whole_file(self):
        report = profile_table(read_local_table(self.source("x\n1\n2\n3\n4\n"), max_rows=2))
        self.assertEqual(report["scope"]["rows_read"], 2)
        self.assertIsNone(report["scope"]["total_rows"])
        self.assertFalse(report["scope"]["exact_row_count"])
        self.assertTrue(report["scope"]["sampled"])
        self.assertEqual(report["column_profiles"][0]["statistics"]["max"], 2)

    def test_exactly_limit_rows_is_exact(self):
        table = read_local_table(self.source("x\n1\n2\n"), max_rows=2)
        self.assertEqual(table.total_rows, 2)
        self.assertFalse(table.sampled)

    def test_empty_and_header_only_inputs(self):
        for text, columns in (("", 0), ("a,b\n", 2)):
            with self.subTest(text=text):
                report = profile_table(read_local_table(self.source(text)))
                self.assertEqual(report["scope"]["total_rows"], 0)
                self.assertEqual(report["columns"], columns)
                json.dumps(report, allow_nan=False)

    def test_all_null_column_is_valid_json(self):
        report = profile_table(read_local_table(self.source("id,empty\n1,\n2,\n")))
        column = report["column_profiles"][1]
        self.assertEqual(column["missing"], 2)
        self.assertEqual(column["unique_non_null"], 0)
        self.assertIsNone(column["statistics"]["mean"])
        json.dumps(report, allow_nan=False)

    def test_json_objects_nested_values_and_jsonl(self):
        records = [{"id": 1, "nested": {"a": [1]}}, {"id": 1, "nested": {"a": [1]}}]
        report = profile_table(read_local_table(self.source(json.dumps(records), "data.json")))
        self.assertEqual(report["duplicate_rows"], 1)
        self.assertEqual(report["scope"]["total_rows"], 2)
        line_table = read_local_table(self.source('\n{"x":1}\n{"x":2}\n{"x":3}\n', "data.jsonl"), max_rows=1)
        self.assertTrue(line_table.sampled)
        self.assertEqual(line_table.data.iloc[0]["x"], 1)

    def test_json_stream_handles_large_record_across_chunks(self):
        text = json.dumps([{"text": "a" * 100000}, {"text": "b"}])
        table = read_local_table(self.source(text, "data.json"))
        self.assertEqual(table.total_rows, 2)
        self.assertEqual(len(table.data.iloc[0]["text"]), 100000)

    def test_malformed_csv_json_and_jsonl_fail(self):
        cases = [("x\n\"unterminated", "bad.csv"), ('[{"x": 1},]', "bad.json"), ('[{"x":', "bad.json"), ('{"x":1}\nnot json', "bad.jsonl")]
        for text, name in cases:
            with self.subTest(name=name, text=text):
                with self.assertRaises(DataToolError):
                    read_local_table(self.source(text, name))

    def test_duplicate_or_empty_raw_headers_are_rejected(self):
        cases = [
            ("id,id\n1,2\n", "duplicate.csv", "duplicate column names"),
            ("id,\n1,2\n", "empty.csv", "empty column name"),
            ("id\tid\n1\t2\n", "duplicate.tsv", "duplicate column names"),
            ('""\nvalue\n', "quoted-empty.csv", "empty column name"),
        ]
        for text, filename, message in cases:
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(DataToolError, message):
                    read_local_table(self.source(text, filename))

    def test_quoted_header_delimiters_and_initial_blank_lines_are_valid(self):
        table = read_local_table(self.source('\n"sensor,name",value\nalpha,1\n'))
        self.assertEqual(table.data.columns.tolist(), ["sensor,name", "value"])
        self.assertEqual(table.total_rows, 1)

    def test_corrupt_excel_has_clear_reader_error(self):
        with self.assertRaisesRegex(DataToolError, "Cannot read excel input"):
            read_local_table(self.source("not an excel file", "bad.xlsx"))

    def test_urls_network_paths_missing_paths_and_invalid_limit_fail(self):
        for value in ("https://example.com/data.csv", "s3://bucket/data.csv", "file:///tmp/data.csv", "//server/data.csv", "\\\\server\\data.csv"):
            with self.subTest(value=value), self.assertRaises(DataToolError):
                local_path(value)
        with self.assertRaises(DataToolError):
            read_local_table(self.directory / "missing.csv")
        with self.assertRaises(DataToolError):
            read_local_table(self.source("x\n1"), max_rows=0)

    def test_guard_never_overwrites_input_even_with_overwrite(self):
        source = self.source("x\n1\n")
        with self.assertRaises(DataToolError):
            guard_output(source, source, overwrite=True)

    def test_cli_writes_reports_and_refuses_accidental_overwrite(self):
        source = self.source("a|b,value\nx,2\n")
        output = self.directory / "reports"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(source), "--output-dir", str(output)]), 0)
            self.assertEqual(main([str(source), "--output-dir", str(output)]), 2)
        self.assertTrue((output / "profile.json").exists())
        self.assertIn("a\\|b", (output / "profile.md").read_text(encoding="utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("openpyxl"), "optional openpyxl unavailable")
    def test_excel_named_sheet_and_prefix(self):
        import pandas as pd
        path = self.directory / "data.xlsx"
        pd.DataFrame({"x": [1, 2, 3]}).to_excel(path, sheet_name="measurements", index=False)
        table = read_local_table(path, sheet="measurements", max_rows=2)
        self.assertTrue(table.sampled)
        self.assertEqual(len(table.data), 2)

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional pyarrow unavailable")
    def test_parquet_prefix_retains_exact_metadata_count(self):
        import pandas as pd
        path = self.directory / "data.parquet"
        pd.DataFrame({"x": [1, 2, 3, 4]}).to_parquet(path, index=False)
        table = read_local_table(path, max_rows=2)
        self.assertEqual(table.total_rows, 4)
        self.assertTrue(table.sampled)
        self.assertEqual(len(table.data), 2)


if __name__ == "__main__":
    unittest.main()
