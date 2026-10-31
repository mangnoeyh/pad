import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.inspect_data import DataToolError, read_local_table
from tools.query_data import main, query_table

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("duckdb"), "optional duckdb unavailable")
class QueryDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="test-query-", dir=ROOT)
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.source = self.directory / "data.csv"
        self.source.write_text("group,value\na,1\na,2\nb,4\n", encoding="utf-8")
        self.table = read_local_table(self.source)

    def test_grouped_query_and_cte(self):
        result, metadata = query_table(self.table, 'WITH grouped AS (SELECT "group", SUM(value) AS total FROM data GROUP BY "group") SELECT * FROM grouped ORDER BY "group";')
        self.assertEqual(result["total"].tolist(), [3.0, 4.0])
        self.assertFalse(metadata["external_access"])
        self.assertFalse(metadata["input_scope"]["sampled"])

    def test_multiple_or_mutating_statements_fail(self):
        before = self.source.read_bytes()
        for sql in ("SELECT * FROM data; DROP TABLE data;", "DELETE FROM data", "CREATE TABLE x AS SELECT * FROM data", "COPY data TO 'forbidden.csv'", "INSTALL httpfs", ""):
            with self.subTest(sql=sql), self.assertRaises(DataToolError):
                query_table(self.table, sql)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse((ROOT / "forbidden.csv").exists())

    def test_file_and_remote_reads_are_disabled(self):
        for sql in ("SELECT * FROM read_csv('https://example.com/data.csv')", f"SELECT * FROM read_csv('{self.source.as_posix()}')", "SELECT * FROM read_text('nonexistent.txt')"):
            with self.subTest(sql=sql), self.assertRaises(DataToolError):
                query_table(self.table, sql)

    def test_result_limit_fails_instead_of_silently_truncating(self):
        with self.assertRaisesRegex(DataToolError, "more than 2"):
            query_table(self.table, "SELECT * FROM data", max_result_rows=2)

    def test_sample_scope_and_trailing_comment(self):
        table = read_local_table(self.source, max_rows=1)
        result, metadata = query_table(table, "SELECT COUNT(*) AS n FROM data -- comment")
        self.assertEqual(result.iloc[0]["n"], 1)
        self.assertTrue(metadata["input_scope"]["sampled"])

    def test_terminal_semicolon_with_line_and_block_comments(self):
        for ending in ("; -- trailing note", "; /* trailing note */", "; /* note */ -- another note"):
            with self.subTest(ending=ending):
                result, _ = query_table(self.table, "SELECT SUM(value) AS total FROM data" + ending)
                self.assertEqual(result.iloc[0]["total"], 7)

    def test_semicolons_inside_quoted_literals_are_preserved(self):
        result, _ = query_table(self.table, "SELECT '; -- still a literal /* yes */' AS text; -- comment")
        self.assertEqual(result.iloc[0]["text"], "; -- still a literal /* yes */")

    def test_unicode_and_dollar_quoted_literal_offsets(self):
        text = "\ud55c\uae00; -- literal /* text */"
        result, _ = query_table(self.table, "SELECT $quoted$" + text + "$quoted$ AS text; /* tail */")
        self.assertEqual(result.iloc[0]["text"], text)

    def test_cli_json_output_and_input_overwrite_guard(self):
        output = self.directory / "result.json"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.source), "--sql", "SELECT SUM(value) AS total FROM data", "--output", str(output)]), 0)
            self.assertEqual(main([str(self.source), "--sql", "SELECT * FROM data", "--output", str(self.source), "--overwrite"]), 2)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))[0]["total"], 7)


if __name__ == "__main__":
    unittest.main()
