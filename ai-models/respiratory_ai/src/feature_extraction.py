import numpy as np

from scipy.signal import welch, find_peaks

from src.processing import clean_ppg_signal


def extract_features(
    ppg_window,
    sampling_rate=125
):

    ppg_window = np.asarray(ppg_window, dtype=float)
    if ppg_window.ndim != 1 or ppg_window.size == 0:
        raise ValueError("PPG window must be a non-empty one-dimensional signal.")
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError("Sampling rate must be a positive number.")

    signal = clean_ppg_signal(
        ppg_window,
        sampling_rate
    )

    features = {}

    # Time-domain features
    features["mean"] = np.mean(signal)

    features["std"] = np.std(signal)

    features["rms"] = np.sqrt(
        np.mean(signal ** 2)
    )

    features["min"] = np.min(signal)

    features["max"] = np.max(signal)

    features["range"] = (
        np.max(signal) - np.min(signal)
    )

    features["zero_crossings"] = np.sum(
        np.diff(np.sign(signal)) != 0
    )

    # Frequency-domain analysis
    frequencies, power = welch(
        signal,
        fs=sampling_rate,
        nperseg=min(
            len(signal),
            sampling_rate * 16
        )
    )

    valid_band = (
        (frequencies >= 0.08) &
        (frequencies <= 0.70)
    )

    band_frequencies = frequencies[valid_band]

    band_power = power[valid_band]

    if len(band_power) == 0:
        raise ValueError(
            "Insufficient frequency information."
        )

    dominant_frequency = band_frequencies[
        np.argmax(band_power)
    ]

    features["dominant_frequency"] = (
        dominant_frequency
    )

    features["estimated_rr_frequency"] = (
        dominant_frequency * 60
    )

    features["band_power"] = np.sum(
        band_power
    )

    features["peak_power"] = np.max(
        band_power
    )

    return features
