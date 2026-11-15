from __future__ import annotations

import pandas as pd


FEATURE_COLUMNS = [
    "heart_rate_mean",
    "heart_rate_std",
    "systolic_bp_mean",
    "diastolic_bp_mean",
    "spo2_mean",
    "temperature_mean",
    "respiratory_rate_mean",
    "heart_rate_change",
    "spo2_change",
]

METRIC_ALIASES = {
    "heart_rate": {
        "heart_rate",
        "HR",
        "ECG/HR",
        "SNUADC/HR",
        "Solar8000/HR",
        "Solar8000/PLETH_HR",
    },
    "systolic_bp": {
        "systolic_bp",
        "ART_SBP",
        "Solar8000/ART_SBP",
        "Solar8000/NIBP_SBP",
    },
    "diastolic_bp": {
        "diastolic_bp",
        "ART_DBP",
        "Solar8000/ART_DBP",
        "Solar8000/NIBP_DBP",
    },
    "spo2": {"spo2", "SpO2", "Solar8000/PLETH_SPO2"},
    "temperature": {"temperature", "BT", "Solar8000/BT", "Solar8000/BT2"},
    "respiratory_rate": {"respiratory_rate", "RR", "Solar8000/RR"},
}


def extract_window_features(
    measurements: pd.DataFrame,
    window_seconds: int = 60,
) -> pd.DataFrame:
    required = {"recorded_at", "metric", "value"}
    missing = required.difference(measurements.columns)
    if missing:
        raise ValueError(f"Measurements are missing columns: {sorted(missing)}")
    if measurements.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS + ["window_start", "window_end"])

    frame = measurements.copy()
    frame["recorded_at"] = pd.to_datetime(frame["recorded_at"], utc=True, errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["recorded_at", "value"])
    frame["metric_name"] = frame["metric"].map(_canonical_metric)
    frame = frame.dropna(subset=["metric_name"])
    if frame.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS + ["window_start", "window_end"])

    frame["window_start"] = frame["recorded_at"].dt.floor(f"{window_seconds}s")
    grouped = frame.groupby("window_start", sort=True)
    feature_rows = [
        _aggregate_window(window)
        for _, window in grouped
    ]
    features = pd.DataFrame(feature_rows, index=grouped.groups.keys())
    features.index.name = "window_start"
    features["window_end"] = features.index + pd.to_timedelta(window_seconds, unit="s")
    return features.reset_index()


def _canonical_metric(metric: object) -> str | None:
    text = str(metric)
    for canonical, aliases in METRIC_ALIASES.items():
        if text in aliases:
            return canonical
    return None


def _aggregate_window(window: pd.DataFrame) -> dict[str, float]:
    result = {column: float("nan") for column in FEATURE_COLUMNS}
    for metric, values in window.groupby("metric_name")["value"]:
        result[f"{metric}_mean"] = float(values.mean())
        if metric == "heart_rate":
            result["heart_rate_std"] = float(values.std(ddof=0))
    for metric, feature in (("heart_rate", "heart_rate_change"), ("spo2", "spo2_change")):
        values = window.loc[window["metric_name"] == metric, "value"]
        if len(values) >= 2:
            result[feature] = float(values.iloc[-1] - values.iloc[0])
    return result
