import pandas as pd
import numpy as np

from src.config import DATASET_DIR


def load_recording(subject_id):

    subject = f"{subject_id:02d}"

    signal_file = (
        DATASET_DIR /
        f"bidmc_{subject}_Signals.csv"
    )

    numerics_file = (
        DATASET_DIR /
        f"bidmc_{subject}_Numerics.csv"
    )

    breaths_file = (
        DATASET_DIR /
        f"bidmc_{subject}_Breaths.csv"
    )

    signals = pd.read_csv(signal_file)
    numerics = pd.read_csv(numerics_file)
    breaths = pd.read_csv(breaths_file)

    # Clean column names
    signals.columns = signals.columns.str.strip()
    numerics.columns = numerics.columns.str.strip()
    breaths.columns = breaths.columns.str.strip()

    # Extract physiological waveforms
    ppg = pd.to_numeric(
        signals["PLETH"],
        errors="coerce"
    ).to_numpy()

    respiratory_signal = pd.to_numeric(
        signals["RESP"],
        errors="coerce"
    ).to_numpy()

    # Numerical reference
    respiratory_rate = pd.to_numeric(
        numerics["RESP"],
        errors="coerce"
    ).to_numpy()

    spo2_column = next(
        col for col in numerics.columns
        if col.upper().replace(" ", "").startswith("SPO")
    )

    spo2 = pd.to_numeric(
        numerics[spo2_column],
        errors="coerce"
    ).to_numpy()

    # Manual annotations
    annotation_1 = pd.to_numeric(
        breaths.iloc[:, 0],
        errors="coerce"
    ).dropna().to_numpy()

    annotation_2 = pd.to_numeric(
        breaths.iloc[:, 1],
        errors="coerce"
    ).dropna().to_numpy()

    return {
        "ppg": ppg,
        "resp_signal": respiratory_signal,
        "respiratory_rate": respiratory_rate,
        "spo2": spo2,
        "annotation_1": annotation_1,
        "annotation_2": annotation_2
    }
