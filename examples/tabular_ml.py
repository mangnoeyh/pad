"""Local CSV baseline with train-only preprocessing and explicit holdout splits.

This is an example, not a task-specific model-selection or validation policy.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys


def local_path(value: str | Path) -> Path:
    """Reject URL and network-share paths before resolving or touching them."""
    def reject_network(raw: str) -> None:
        if raw.startswith(("//", "\\\\")) or "://" in raw or re.match(r"^[A-Za-z][A-Za-z0-9+.-]{1,}:", raw):
            raise ValueError("Only local filesystem paths are supported; URLs and network shares are rejected")
    reject_network(str(value))
    resolved = Path(value).resolve()
    reject_network(str(resolved))
    return resolved


@dataclass
class Split:
    train_indices: list[int]
    test_indices: list[int]
    feature_columns: list[str]
    excluded_columns: list[str]
    details: dict


def make_split(frame, target: str, split: str = "random", time_column: str | None = None,
               group_column: str | None = None, test_size: float = 0.25, seed: int = 42) -> Split:
    import numpy as np
    import pandas as pd
    if target not in frame.columns:
        raise ValueError(f"Target column not found: {target}")
    if frame[target].isna().any():
        raise ValueError("Target contains missing values; resolve labels explicitly before training")
    if len(frame) < 4:
        raise ValueError("At least four labeled rows are required")
    if not 0 < test_size < 1:
        raise ValueError("--test-size must be strictly between 0 and 1")
    if split not in {"random", "time", "group"}:
        raise ValueError("--split must be random, time, or group")
    roles = [name for name in (time_column, group_column) if name is not None]
    if len(roles) != len(set(roles)) or target in roles:
        raise ValueError("Target, time, and group roles must refer to different columns")
    for name in roles:
        if name not in frame.columns:
            raise ValueError(f"Role column not found: {name}")
    excluded = [target] + roles
    features = [column for column in frame.columns if column not in excluded]
    if not features:
        raise ValueError("No predictor columns remain after excluding target/time/group roles")
    rng = np.random.RandomState(seed)
    details = {"strategy": split, "requested_test_size": test_size, "seed": seed}
    if split == "time":
        if time_column is None:
            raise ValueError("--time-column is required for --split time")
        timestamps = pd.to_datetime(frame[time_column], errors="raise", utc=True, format="mixed")
        if timestamps.isna().any():
            raise ValueError("Time column contains missing timestamps")
        order = np.argsort(timestamps.to_numpy(), kind="stable")
        cutoff_position = max(1, min(len(frame) - 1, math.floor(len(frame) * (1 - test_size))))
        cutoff = timestamps.iloc[int(order[cutoff_position])]
        train = [int(index) for index in order if timestamps.iloc[int(index)] < cutoff]
        test = [int(index) for index in order if timestamps.iloc[int(index)] >= cutoff]
        if not train or not test:
            raise ValueError("Time split needs at least two distinct timestamps and a nonempty earlier partition")
        details.update({"train_time_max": timestamps.iloc[train].max().isoformat(),
                        "test_time_min": timestamps.iloc[test].min().isoformat()})
    elif split == "group":
        if group_column is None:
            raise ValueError("--group-column is required for --split group")
        groups = frame[group_column]
        if groups.isna().any():
            raise ValueError("Group column contains missing values")
        unique_groups = list(pd.unique(groups))
        if len(unique_groups) < 2:
            raise ValueError("Group split needs at least two distinct groups")
        order = rng.permutation(len(unique_groups))
        test_count = min(len(unique_groups) - 1, max(1, math.ceil(len(unique_groups) * test_size)))
        test_groups = {unique_groups[int(index)] for index in order[:test_count]}
        test_mask = groups.isin(test_groups).to_numpy()
        train, test = np.flatnonzero(~test_mask).tolist(), np.flatnonzero(test_mask).tolist()
        details.update({"train_groups": int(groups.iloc[train].nunique()),
                        "test_groups": int(groups.iloc[test].nunique()), "group_overlap": 0})
    else:
        order = rng.permutation(len(frame))
        test_count = min(len(frame) - 1, max(1, math.ceil(len(frame) * test_size)))
        test, train = order[:test_count].tolist(), order[test_count:].tolist()
        details["note"] = "Random row holdout is not stratified; inspect class balance and entity/time leakage."
    if len(train) < 2:
        raise ValueError("Split leaves fewer than two training rows; change the split or provide more data")
    details.update({"train_rows": len(train), "test_rows": len(test)})
    return Split(train, test, features, excluded, details)


def normalize_features(frame):
    """Normalize categories/infinities without learning any data statistics."""
    import numpy as np
    import pandas as pd
    result = frame.copy()
    for column in result.columns:
        if pd.api.types.is_numeric_dtype(result[column]):
            result[column] = pd.to_numeric(result[column]).astype(float).replace([np.inf, -np.inf], np.nan)
        else:
            result[column] = result[column].map(lambda value: np.nan if pd.isna(value) else str(value)).astype(object)
    return result


def build_pipeline(features, task: str, seed: int = 42):
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    if task not in {"classification", "regression"}:
        raise ValueError("--task must be classification or regression")
    numeric = [column for column in features if pd.api.types.is_numeric_dtype(features[column])]
    categorical = [column for column in features if column not in numeric]
    transformations = []
    if numeric:
        transformations.append(("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
        ]), numeric))
    if categorical:
        transformations.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("encoder", OneHotEncoder(handle_unknown="ignore", max_categories=50, sparse_output=True)),
        ]), categorical))
    estimator = (LogisticRegression(max_iter=500, random_state=seed)
                 if task == "classification" else Ridge(solver="lsqr"))
    return Pipeline([("preprocess", ColumnTransformer(transformations)), ("model", estimator)])


def _read_csv(input_path: Path, max_rows: int):
    input_path = local_path(input_path)
    import pandas as pd
    if max_rows < 4:
        raise ValueError("--max-rows must be at least four")
    if not input_path.is_file():
        raise ValueError(f"A local input CSV file is required: {input_path}")
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if not header or any(not name.strip() for name in header) or len(header) != len(set(header)):
        raise ValueError("CSV must have nonempty, unique column names")
    frame = pd.read_csv(input_path, encoding="utf-8-sig", nrows=max_rows + 1)
    if len(frame) > max_rows:
        raise ValueError(f"CSV exceeds --max-rows {max_rows}; choose a deliberate local subset or raise the limit")
    return frame


def run_baseline(input_path: Path, target: str, task: str, output_dir: Path, split: str = "random",
                 time_column: str | None = None, group_column: str | None = None,
                 test_size: float = 0.25, seed: int = 42, max_rows: int = 100_000) -> dict:
    input_path, output_dir = local_path(input_path), local_path(output_dir)
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError("Output directory must be new or empty; existing files will not be overwritten")
    frame = _read_csv(input_path, max_rows)
    partition = make_split(frame, target, split, time_column, group_column, test_size, seed)
    x_train = normalize_features(frame.iloc[partition.train_indices][partition.feature_columns])
    x_test = normalize_features(frame.iloc[partition.test_indices][partition.feature_columns])
    labels = frame[target]
    if task == "classification":
        labels = labels.astype(str)
        if labels.iloc[partition.train_indices].nunique() < 2:
            raise ValueError("Training partition has fewer than two classes; revise the split or labels")
        baseline = DummyClassifier(strategy="most_frequent")
    elif task == "regression":
        labels = pd.to_numeric(labels, errors="raise").astype(float)
        if not np.isfinite(labels.to_numpy()).all():
            raise ValueError("Regression labels must be finite numeric values")
        baseline = DummyRegressor(strategy="mean")
    else:
        raise ValueError("--task must be classification or regression")
    y_train, y_test = labels.iloc[partition.train_indices], labels.iloc[partition.test_indices]
    pipeline = build_pipeline(x_train, task, seed)
    pipeline.fit(x_train, y_train)
    prediction = pipeline.predict(x_test)
    baseline.fit(x_train, y_train)
    baseline_prediction = baseline.predict(x_test)
    if task == "classification":
        scores = {"accuracy": float(accuracy_score(y_test, prediction)),
                  "macro_f1": float(f1_score(y_test, prediction, average="macro", zero_division=0))}
        baseline_scores = {"accuracy": float(accuracy_score(y_test, baseline_prediction)),
                           "macro_f1": float(f1_score(y_test, baseline_prediction, average="macro", zero_division=0))}
    else:
        def regression_scores(values):
            return {"mae": float(mean_absolute_error(y_test, values)),
                    "rmse": math.sqrt(float(mean_squared_error(y_test, values))),
                    "r2": float(r2_score(y_test, values)) if len(y_test) >= 2 else None}
        scores, baseline_scores = regression_scores(prediction), regression_scores(baseline_prediction)
    metrics = {"task": task, "target": target, "input_rows": len(frame),
               "feature_columns": partition.feature_columns, "excluded_columns": partition.excluded_columns,
               "split": partition.details, "metrics": scores, "dummy_baseline_metrics": baseline_scores,
               "versions": {"pandas": pd.__version__, "scikit_learn": sklearn.__version__},
               "limitations": ["One holdout only; no hyperparameter search or causal claim.",
                               "Review identifier features, class balance, and domain leakage before use.",
                               "Predictor infinities are treated as missing; training median/mode imputation is used."]}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pd.DataFrame({"source_row": partition.test_indices, "actual": y_test.to_numpy(),
                  "prediction": prediction}).to_csv(output_dir / "predictions.csv", index=False)
    report = ("# Local tabular baseline\n\n"
              f"- Task: {task}\n- Target: `{target}`\n- Holdout: `{split}`\n"
              f"- Training rows: {len(y_train)}; test rows: {len(y_test)}\n"
              f"- Features: {', '.join(f'`{name}`' for name in partition.feature_columns)}\n"
              "- Preprocessing is fitted on training rows only. Target/time/group role columns are excluded.\n"
              "- `predictions.csv` source_row is the zero-based data-row position in the original CSV, excluding its header.\n\n"
              "## Holdout metrics\n\n```json\n" + json.dumps(scores, indent=2) + "\n```\n\n"
              "## Dummy baseline\n\n```json\n" + json.dumps(baseline_scores, indent=2) + "\n```\n\n"
              "## Limits and next checks\n\n"
              + "\n".join(f"- {item}" for item in metrics["limitations"]) + "\n"
              "- The example does not establish that these features, labels, or splits suit the real task.\n")
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog="This example has no --overwrite option; its output directory must be new or empty.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--task", choices=["classification", "regression"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split", choices=["random", "time", "group"], default="random")
    parser.add_argument("--time-column")
    parser.add_argument("--group-column")
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rows", type=int, default=100_000)
    args = parser.parse_args()
    try:
        result = run_baseline(args.input, args.target, args.task, args.output_dir, args.split,
                              args.time_column, args.group_column, args.test_size, args.seed, args.max_rows)
    except ImportError as error:
        parser.exit(2, f"error: missing ML dependency ({error.name}); install requirements-ml.txt\n")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
