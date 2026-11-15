from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .features import FEATURE_COLUMNS


@dataclass(frozen=True)
class AnomalyResult:
    case_id: str | None
    detected: bool
    score: float
    window_start: str
    window_end: str
    features: dict[str, float | None]


class AnomalyDetector:
    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
        feature_columns: list[str] | None = None,
    ) -> None:
        self.feature_columns = feature_columns or FEATURE_COLUMNS.copy()
        self.pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    IsolationForest(
                        contamination=contamination,
                        random_state=random_state,
                        n_estimators=200,
                    ),
                ),
            ]
        )
        self._trained = False

    def fit(self, windows: pd.DataFrame) -> None:
        self._validate_windows(windows)
        if len(windows) < 10:
            raise ValueError("At least 10 measurement windows are required for training")
        self.pipeline.fit(windows[self.feature_columns])
        self._trained = True

    def predict(self, windows: pd.DataFrame) -> list[AnomalyResult]:
        if not self._trained:
            raise RuntimeError("The anomaly detector has not been trained")
        self._validate_windows(windows)
        predictions = self.pipeline.predict(windows[self.feature_columns])
        scores = self.pipeline.decision_function(windows[self.feature_columns])
        results: list[AnomalyResult] = []
        for index, (prediction, score) in enumerate(zip(predictions, scores)):
            row = windows.iloc[index]
            results.append(
                AnomalyResult(
                    case_id=str(row["case_id"]) if "case_id" in row and pd.notna(row["case_id"]) else None,
                    detected=bool(prediction == -1),
                    score=float(score),
                    window_start=_as_iso(row["window_start"]),
                    window_end=_as_iso(row["window_end"]),
                    features={
                        column: _as_float(row[column]) for column in self.feature_columns
                    },
                )
            )
        return results

    def save(self, path: str | Path) -> None:
        if not self._trained:
            raise RuntimeError("Cannot save an untrained anomaly detector")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: str | Path) -> "AnomalyDetector":
        detector = joblib.load(path)
        if not isinstance(detector, cls):
            raise TypeError("Model file does not contain an AnomalyDetector")
        return detector

    def _validate_windows(self, windows: pd.DataFrame) -> None:
        missing = set(self.feature_columns).difference(windows.columns)
        if missing:
            raise ValueError(f"Feature windows are missing columns: {sorted(missing)}")


def _as_float(value: object) -> float | None:
    return None if pd.isna(value) else float(value)


def _as_iso(value: object) -> str:
    return pd.Timestamp(value).isoformat()
