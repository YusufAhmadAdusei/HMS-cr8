from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .anomaly_detection import AnomalyDetector
from .features import FEATURE_COLUMNS, extract_window_features


def prepare_and_train(
    measurements_path: str | Path,
    output_dir: str | Path = "data/ml",
    model_path: str | Path = "ml/model/isolation_forest.joblib",
    seed: int = 42,
) -> dict[str, object]:
    measurements = pd.read_parquet(measurements_path)
    required = {"case_id", "recorded_at", "metric", "value"}
    missing = required.difference(measurements.columns)
    if missing:
        raise ValueError(f"Training data is missing columns: {sorted(missing)}")

    windows = _build_case_windows(measurements)
    if windows.empty:
        raise ValueError("No feature windows were created from the measurements")

    case_feature_coverage = (
        windows.groupby("case_id")[FEATURE_COLUMNS]
        .apply(lambda frame: frame.notna().any())
        .mean()
    )
    available_features = [
        column
        for column in FEATURE_COLUMNS
        if case_feature_coverage[column] >= 0.8
    ]
    if len(available_features) < 2:
        raise ValueError("Fewer than two supported feature columns are available")
    complete_mask = windows[available_features].notna().all(axis=1)
    complete_windows = windows.loc[complete_mask].reset_index(drop=True)
    excluded_windows = int((~complete_mask).sum())
    if complete_windows.empty:
        raise ValueError("No complete feature windows are available for training")

    splits = _split_by_case(complete_windows, seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for split_name, split_frame in splits.items():
        split_frame.to_parquet(output / f"{split_name}.parquet", index=False)
        split_frame.to_csv(output / f"{split_name}.csv", index=False)

    detector = AnomalyDetector(feature_columns=available_features)
    detector.fit(splits["train"])
    detector.save(model_path)
    evaluation = {
        split_name: {
            "cases": int(split_frame["case_id"].nunique()),
            "windows": len(split_frame),
        }
        for split_name, split_frame in splits.items()
    }
    for split_name in ("validation", "test"):
        results = detector.predict(splits[split_name])
        scores = [result.score for result in results]
        evaluation[split_name]["anomalies"] = sum(
            result.detected for result in results
        )
        evaluation[split_name]["mean_score"] = (
            float(sum(scores) / len(scores)) if scores else None
        )
    evaluation["excluded_incomplete_windows"] = excluded_windows
    evaluation["feature_columns"] = available_features
    Path(output / "dataset_summary.json").write_text(
        json.dumps(evaluation, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return evaluation


def _json_default(value: object) -> int | float | str:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Value is not JSON serializable: {type(value).__name__}")


def _build_case_windows(measurements: pd.DataFrame) -> pd.DataFrame:
    windows: list[pd.DataFrame] = []
    for case_id, case_measurements in measurements.groupby("case_id", sort=True):
        case_windows = extract_window_features(case_measurements)
        if not case_windows.empty:
            windows.append(case_windows.assign(case_id=str(case_id)))
    return pd.concat(windows, ignore_index=True) if windows else pd.DataFrame()


def _split_by_case(windows: pd.DataFrame, seed: int) -> dict[str, pd.DataFrame]:
    cases = sorted(windows["case_id"].astype(str).unique())
    if len(cases) < 3:
        raise ValueError("At least three cases are required for train/validation/test splits")
    shuffled = pd.Series(cases).sample(frac=1, random_state=seed).tolist()
    train_end = max(1, int(len(shuffled) * 0.7))
    validation_end = max(train_end + 1, int(len(shuffled) * 0.85))
    validation_end = min(validation_end, len(shuffled) - 1)
    if validation_end <= train_end:
        train_end = len(shuffled) - 2
    case_groups = {
        "train": set(shuffled[:train_end]),
        "validation": set(shuffled[train_end:validation_end]),
        "test": set(shuffled[validation_end:]),
    }
    return {
        split: windows[windows["case_id"].isin(split_cases)].reset_index(drop=True)
        for split, split_cases in case_groups.items()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare VitalDB features and train Isolation Forest")
    parser.add_argument("measurements_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/ml"))
    parser.add_argument("--model-path", type=Path, default=Path("ml/model/isolation_forest.joblib"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_and_train(args.measurements_path, args.output_dir, args.model_path, args.seed),
            indent=2,
            default=_json_default,
        )
    )
