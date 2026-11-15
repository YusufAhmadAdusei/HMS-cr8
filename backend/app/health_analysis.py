from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

import pandas as pd

from ml.anomaly_detection import AnomalyDetector, AnomalyResult
from ml.features import extract_window_features

EXPECTED_METRICS = {
    "Solar8000/HR",
    "Solar8000/NIBP_SBP",
    "Solar8000/NIBP_DBP",
    "Solar8000/PLETH_SPO2",
    "Solar8000/BT",
    "Solar8000/RR",
}
logger = logging.getLogger(__name__)


def build_health_summary(
    measurements: list[dict[str, Any]],
    detector: AnomalyDetector | None = None,
) -> dict[str, Any]:
    frame = pd.DataFrame(
        measurements,
        columns=["case_id", "recorded_at", "metric", "value", "unit", "source"],
    )
    windows = _extract_windows_by_case(frame)
    anomalies: list[AnomalyResult] = []
    if detector is not None and not windows.empty:
        anomalies = detector.predict(windows)
    active_anomalies = [result for result in anomalies if result.detected]
    metrics_available = (
        sorted(frame["metric"].dropna().unique().tolist())
        if "metric" in frame
        else []
    )
    if not measurements:
        analysis_status = "insufficient_data"
        status = "insufficient_data"
    elif detector is None:
        analysis_status = "model_unavailable"
        status = "monitoring"
    else:
        analysis_status = "complete"
        status = "attention" if active_anomalies else "monitoring"
    logger.debug(
        "summary_features measurements=%d windows=%d anomalies=%d status=%s",
        len(measurements),
        len(windows),
        len(active_anomalies),
        status,
    )
    return {
        "status": status,
        "analysis_status": analysis_status,
        "data_source": _data_source(frame),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_measurements": _latest_measurements(frame),
        "anomalies": [result.__dict__ for result in active_anomalies],
        "trend_windows": len(windows),
        "data_quality": {
            "measurement_count": len(frame),
            "metrics_available": metrics_available,
            "expected_metrics_missing": sorted(EXPECTED_METRICS.difference(metrics_available)),
            "feature_windows_available": len(windows),
        },
    }


def _latest_measurements(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty or "recorded_at" not in frame:
        return []
    group_columns = ["metric"]
    if "case_id" in frame:
        group_columns.insert(0, "case_id")
    latest = frame.sort_values("recorded_at").groupby(group_columns, as_index=False).tail(1)
    return latest.to_dict(orient="records")


def _extract_windows_by_case(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return extract_window_features(frame)
    windows = [
        extract_window_features(case_frame).assign(case_id=str(case_id))
        for case_id, case_frame in frame.groupby("case_id")
    ]
    return pd.concat(windows, ignore_index=True) if windows else extract_window_features(frame)


def _data_source(frame: pd.DataFrame) -> str:
    if "source" not in frame or frame.empty:
        return "VitalDB"
    sources = frame["source"].dropna().unique().tolist()
    return ", ".join(str(source) for source in sources) or "VitalDB"

__all__ = ["build_health_summary"]
