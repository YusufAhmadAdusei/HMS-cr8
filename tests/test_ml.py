from datetime import datetime, timedelta, timezone
import json

import pandas as pd

from ml.anomaly_detection import AnomalyDetector
from ml.features import FEATURE_COLUMNS, extract_window_features
from ml.pipeline import prepare_and_train


def test_extract_window_features_aggregates_supported_metrics() -> None:
    start = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
    measurements = pd.DataFrame(
        [
            {
                "case_id": "5871",
                "recorded_at": start,
                "metric": "Solar8000/HR",
                "value": 70,
            },
            {
                "case_id": "5871",
                "recorded_at": start + timedelta(seconds=10),
                "metric": "Solar8000/HR",
                "value": 74,
            },
            {
                "case_id": "5871",
                "recorded_at": start + timedelta(seconds=20),
                "metric": "Solar8000/PLETH_SPO2",
                "value": 98,
            },
        ]
    )

    features = extract_window_features(measurements)

    assert len(features) == 1
    assert features.loc[0, "heart_rate_mean"] == 72
    assert features.loc[0, "heart_rate_std"] == 2
    assert features.loc[0, "heart_rate_change"] == 4
    assert features.loc[0, "spo2_mean"] == 98
    assert pd.isna(features.loc[0, "spo2_change"])


def test_anomaly_detector_requires_training_and_round_trips(tmp_path) -> None:
    windows = pd.DataFrame(
        {
            "heart_rate_mean": range(60, 72),
            "spo2_mean": [98] * 12,
            "case_id": ["5871"] * 12,
            "window_start": pd.date_range(
                "2026-11-14T12:00:00Z", periods=12, freq="min"
            ),
            "window_end": pd.date_range(
                "2026-11-14T12:01:00Z", periods=12, freq="min"
            ),
        }
    )
    detector = AnomalyDetector(
        feature_columns=["heart_rate_mean", "spo2_mean"]
    )

    try:
        detector.predict(windows)
    except RuntimeError as error:
        assert "has not been trained" in str(error)
    else:
        raise AssertionError("An untrained detector must reject prediction")

    detector.fit(windows)
    model_path = tmp_path / "model.joblib"
    detector.save(model_path)
    restored = AnomalyDetector.load(model_path)

    results = restored.predict(windows.iloc[:2])
    assert len(results) == 2
    assert all(result.case_id == "5871" for result in results)
    json.dumps([result.__dict__ for result in results])


def test_training_pipeline_keeps_cases_in_one_split(tmp_path) -> None:
    rows = []
    start = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
    for case_number in range(1, 4):
        for minute in range(10):
            recorded_at = start + timedelta(minutes=minute)
            rows.extend(
                [
                    {
                        "case_id": str(case_number),
                        "recorded_at": recorded_at,
                        "metric": "Solar8000/HR",
                        "value": 65 + case_number + minute,
                    },
                    {
                        "case_id": str(case_number),
                        "recorded_at": recorded_at,
                        "metric": "Solar8000/PLETH_SPO2",
                        "value": 97 + (minute % 2),
                    },
                ]
            )
    measurements_path = tmp_path / "measurements.parquet"
    measurements = pd.DataFrame(rows)
    measurements.to_parquet(measurements_path, index=False)

    summary = prepare_and_train(
        measurements_path,
        output_dir=tmp_path / "dataset",
        model_path=tmp_path / "model.joblib",
    )

    assert summary["feature_columns"] == [
        "heart_rate_mean",
        "heart_rate_std",
        "spo2_mean",
    ]
    split_frames = {
        split: pd.read_parquet(tmp_path / "dataset" / f"{split}.parquet")
        for split in ("train", "validation", "test")
    }
    assert all(not frame.empty for frame in split_frames.values())
    split_cases = [set(frame["case_id"]) for frame in split_frames.values()]
    assert not (split_cases[0] & split_cases[1])
    assert not (split_cases[0] & split_cases[2])
    assert not (split_cases[1] & split_cases[2])


def test_feature_columns_include_expected_health_metrics() -> None:
    assert "heart_rate_mean" in FEATURE_COLUMNS
    assert "systolic_bp_mean" in FEATURE_COLUMNS
    assert "spo2_mean" in FEATURE_COLUMNS
