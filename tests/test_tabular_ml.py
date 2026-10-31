"""Behavior checks for the optional local ML example."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import make_demo_data
import tabular_ml
PANDAS_AVAILABLE = importlib.util.find_spec("pandas") is not None
SKLEARN_AVAILABLE = importlib.util.find_spec("sklearn") is not None



class LocalPathTests(unittest.TestCase):
    def test_url_and_unc_paths_are_rejected_before_filesystem_lookup(self):
        remote_paths = ["https://example.invalid/data.csv", "s3://bucket/data.csv",
                        "file:///tmp/data.csv", r"\\server\share\data.csv", "//server/share/data.csv"]
        with patch.object(Path, "resolve", side_effect=AssertionError("Unexpected filesystem lookup")):
            for value in remote_paths:
                for module in (tabular_ml, make_demo_data):
                    with self.subTest(value=value, module=module.__name__), self.assertRaisesRegex(ValueError, "local filesystem"):
                        module.local_path(value)
                with self.assertRaisesRegex(ValueError, "local filesystem"):
                    make_demo_data.make_demo_data(value)
                with self.assertRaisesRegex(ValueError, "local filesystem"):
                    tabular_ml.run_baseline(value, "target", "classification", Path("output"))

    def test_resolved_network_paths_are_also_rejected(self):
        for module in (tabular_ml, make_demo_data):
            with self.subTest(module=module.__name__):
                with patch.object(Path, "resolve", return_value=Path(r"\\server\share\data.csv")):
                    with self.assertRaisesRegex(ValueError, "local filesystem"):
                        module.local_path("local-alias.csv")


class DemoDataTests(unittest.TestCase):
    def test_generator_reproducibility_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = make_demo_data.make_demo_data(root / "one", 40, 42)
            second = make_demo_data.make_demo_data(root / "two", 40, 42)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with self.assertRaises(ValueError):
                make_demo_data.make_demo_data(root / "one", 40, 42)


@unittest.skipUnless(PANDAS_AVAILABLE, "pandas dependency unavailable")
class SplitTests(unittest.TestCase):
    def setUp(self):
        import pandas as pd
        self.frame = pd.DataFrame({
            "timestamp": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02",
                          "2026-01-03", "2026-01-03", "2026-01-04", "2026-01-04"],
            "equipment": ["A", "B", "C", "D", "A", "B", "C", "D"],
            "value": list(range(8)), "target": [0, 1] * 4,
        })

    def test_time_split_has_strict_boundary_and_excludes_role_features(self):
        result = tabular_ml.make_split(self.frame, "target", "time", "timestamp", "equipment")
        train, test = self.frame.iloc[result.train_indices], self.frame.iloc[result.test_indices]
        self.assertLess(train.timestamp.max(), test.timestamp.min())
        self.assertEqual(result.feature_columns, ["value"])
        self.assertEqual(set(result.train_indices) | set(result.test_indices), set(range(8)))
        self.assertFalse(set(result.train_indices) & set(result.test_indices))

    def test_group_split_has_no_overlap(self):
        result = tabular_ml.make_split(self.frame, "target", "group", "timestamp", "equipment")
        train_groups = set(self.frame.iloc[result.train_indices].equipment)
        test_groups = set(self.frame.iloc[result.test_indices].equipment)
        self.assertFalse(train_groups & test_groups)
        self.assertEqual(result.feature_columns, ["value"])

    def test_random_split_reproducibility(self):
        first = tabular_ml.make_split(self.frame, "target", seed=17)
        second = tabular_ml.make_split(self.frame, "target", seed=17)
        self.assertEqual(first.train_indices, second.train_indices)
        self.assertEqual(first.test_indices, second.test_indices)

    def test_invalid_roles_missing_targets_and_ratios(self):
        import pandas as pd
        for kwargs, message in [({"split": "time", "time_column": "target"}, "different columns"),
                                ({"split": "group"}, "required"), ({"test_size": 1}, "between")]:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, message):
                tabular_ml.make_split(self.frame, "target", **kwargs)
        with self.assertRaisesRegex(ValueError, "missing values"):
            tabular_ml.make_split(self.frame.assign(target=pd.NA), "target")

    def test_identical_timestamps_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct timestamps"):
            tabular_ml.make_split(self.frame.assign(timestamp="2026-01-01"), "target", "time", "timestamp")


@unittest.skipUnless(PANDAS_AVAILABLE and SKLEARN_AVAILABLE, "install requirements-ml.txt for ML checks")
class PipelineTests(unittest.TestCase):
    def test_training_statistics_and_unseen_categories(self):
        import numpy as np
        import pandas as pd
        train = tabular_ml.normalize_features(pd.DataFrame({"value": [1., 3., np.nan, 5.],
                                                            "category": ["a", "b", None, "a"]}))
        test = tabular_ml.normalize_features(pd.DataFrame({"value": [10000., np.nan],
                                                           "category": ["never-seen", None]}))
        model = tabular_ml.build_pipeline(train, "classification")
        model.fit(train, [0, 1, 0, 1])
        imputer = model.named_steps["preprocess"].named_transformers_["numeric"].named_steps["imputer"]
        self.assertEqual(float(imputer.statistics_[0]), 3.)
        self.assertEqual(len(model.predict(test)), 2)
        self.assertEqual(float(imputer.statistics_[0]), 3.)

    def test_classification_outputs_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_demo_data.make_demo_data(root / "data", 80)
            original = source.read_bytes()
            output = root / "output"
            result = tabular_ml.run_baseline(source, "target", "classification", output,
                                               "time", "timestamp", "equipment")
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(result["feature_columns"], ["temperature", "pressure"])
            self.assertEqual(result["split"]["train_rows"] + result["split"]["test_rows"], 80)
            self.assertTrue((output / "predictions.csv").is_file())
            self.assertTrue((output / "report.md").is_file())
            self.assertIn("accuracy", json.loads((output / "metrics.json").read_text())["metrics"])
            with self.assertRaisesRegex(ValueError, "new or empty"):
                tabular_ml.run_baseline(source, "target", "classification", output)

    def test_regression_and_nonfinite_labels(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.csv"
            pd.DataFrame({"x": range(20), "category": ["a", "b"] * 10,
                          "target": [value * 2.5 + 1 for value in range(20)]}).to_csv(source, index=False)
            result = tabular_ml.run_baseline(source, "target", "regression", root / "result")
            self.assertIn("mae", result["metrics"])
            self.assertLess(result["metrics"]["mae"], result["dummy_baseline_metrics"]["mae"])
            frame = pd.read_csv(source)
            frame.loc[0, "target"] = float("inf")
            frame.to_csv(source, index=False)
            with self.assertRaisesRegex(ValueError, "finite"):
                tabular_ml.run_baseline(source, "target", "regression", root / "bad")

    def test_duplicate_headers_and_row_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "duplicate.csv"
            source.write_text("x,x,target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n")
            with self.assertRaisesRegex(ValueError, "unique"):
                tabular_ml.run_baseline(source, "target", "classification", root / "out")
            source = make_demo_data.make_demo_data(root / "demo", 40)
            with self.assertRaisesRegex(ValueError, "exceeds"):
                tabular_ml.run_baseline(source, "target", "classification", root / "out", max_rows=20)


if __name__ == "__main__":
    unittest.main()
