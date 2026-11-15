import numpy as np

from scipy.signal import butter, sosfiltfilt


def clean_ppg_signal(
    signal,
    sampling_rate=125
):

    signal = np.asarray(
        signal,
        dtype=float
    )

    if signal.ndim != 1 or signal.size == 0:
        raise ValueError("PPG signal must be a non-empty one-dimensional array.")
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError("Sampling rate must be a positive number.")

    # Reject excessive missing values
    if not np.all(np.isfinite(signal)):

        valid_fraction = np.mean(
            np.isfinite(signal)
        )

        if valid_fraction < 0.95:
            raise ValueError(
                "Too many missing PPG samples."
            )

        if not np.any(np.isfinite(signal)):
            raise ValueError("PPG signal contains no finite samples.")

        valid = np.isfinite(signal)

        indices = np.arange(len(signal))

        signal = np.interp(
            indices,
            indices[valid],
            signal[valid]
        )

    # Remove DC offset
    signal = signal - np.mean(signal)

    # Butterworth bandpass filter
    sos = butter(
        4,
        [0.08, 0.70],
        btype="bandpass",
        fs=sampling_rate,
        output="sos"
    )

    filtered_signal = sosfiltfilt(
        sos,
        signal
    )

    return filtered_signal
