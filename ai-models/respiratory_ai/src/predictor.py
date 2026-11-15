import numpy as np
import joblib

from pathlib import Path
from src.respiratory_features import extract_respiratory_features


MODEL_PATH = Path("models/respiratory_rate_model.joblib")


class RespiratoryPredictor:

    def __init__(self):

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found: {MODEL_PATH}"
            )

        saved = joblib.load(MODEL_PATH)

        self.model = saved["model"]
        self.features = saved["features"]
        self.sampling_rate = saved["sampling_rate"]
        self.window_seconds = saved["window_seconds"]

    def predict(self, ppg_samples):

        ppg = np.asarray(ppg_samples, dtype=float)

        expected_samples = (
            self.sampling_rate * self.window_seconds
        )

        if len(ppg) < expected_samples:
            raise ValueError(
                f"At least {expected_samples} PPG samples "
                f"({self.window_seconds} seconds) are required."
            )

        if not np.all(np.isfinite(ppg)):
            raise ValueError(
                "PPG signal contains invalid or missing values."
            )

        # Use the most recent window
        ppg = ppg[-expected_samples:]

        # Extract respiratory modulation features
        features = extract_respiratory_features(ppg)

        feature_vector = np.array([
            features[name] for name in self.features
        ]).reshape(1, -1)

        # Predict respiratory rate
        respiratory_rate = float(
            self.model.predict(feature_vector)[0]
        )

        return {
            "respiratory_rate": round(respiratory_rate, 2),
            "unit": "breaths/min",
            "individual_estimates": {
                "RIIV": round(features["RIIV_rate"], 2),
                "RIAV": round(features["RIAV_rate"], 2),
                "RIFV": round(features["RIFV_rate"], 2)
            },
            "signal_quality": "processable",
            "model": "ASTRA-RandomForest-v1"
        }


predictor = RespiratoryPredictor()