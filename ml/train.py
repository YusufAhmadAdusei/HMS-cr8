from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .anomaly_detection import AnomalyDetector
from .features import extract_window_features


def train_model(
    input_csv: str | Path,
    output_model: str | Path,
    report_path: str | Path | None = None,
) -> dict[str, float | int]:
    measurements = pd.read_csv(input_csv)
    if "case_id" not in measurements.columns:
        raise ValueError("Training data must include case_id")
    case_ids = sorted(measurements["case_id"].dropna().astype(str).unique())
    if len(case_ids) < 2:
        raise ValueError("At least two cases are required for held-out evaluation")
    split_index = max(1, int(len(case_ids) * 0.8))
    train_cases = set(case_ids[:split_index])
    train_measurements = measurements[
        measurements["case_id"].astype(str).isin(train_cases)
    ]
    evaluation_measurements = measurements[
        ~measurements["case_id"].astype(str).isin(train_cases)
    ]
    windows = _extract_case_windows(train_measurements)
    detector = AnomalyDetector()
    detector.fit(windows)
    detector.save(output_model)
    evaluation_windows = _extract_case_windows(evaluation_measurements)
    evaluation_results = detector.predict(evaluation_windows) if not evaluation_windows.empty else []
    report = {
        "training_cases": len(train_cases),
        "evaluation_cases": len(case_ids) - len(train_cases),
        "training_windows": len(windows),
        "evaluation_windows": len(evaluation_windows),
        "evaluation_anomalies": sum(result.detected for result in evaluation_results),
    }
    if report_path is not None:
        Path(report_path).write_text(
            pd.Series(report).to_json(indent=2),
            encoding="utf-8",
        )
    return report


def _extract_case_windows(measurements: pd.DataFrame) -> pd.DataFrame:
    windows = [
        extract_window_features(case_measurements).assign(case_id=str(case_id))
        for case_id, case_measurements in measurements.groupby("case_id")
    ]
    return (
        pd.concat(windows, ignore_index=True)
        if windows
        else pd.DataFrame()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the HMS-cr8 anomaly detector")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_model", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    train_model(args.input_csv, args.output_model, args.report)
