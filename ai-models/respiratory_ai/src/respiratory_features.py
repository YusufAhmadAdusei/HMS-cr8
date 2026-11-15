import numpy as np

from scipy.signal import (
    butter,
    sosfiltfilt,
    find_peaks,
    welch
)

from scipy.interpolate import interp1d

from scipy.signal import detrend


FS = 125

RESP_LOW = 0.08
RESP_HIGH = 0.70


def bandpass_filter(signal, low, high, fs):

    sos = butter(
        3,
        [low, high],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    return sosfiltfilt(sos, signal)


def resample_irregular_signal(times, values, fs=4):

    if len(times) < 5:
        raise ValueError("Insufficient pulse measurements.")

    uniform_times = np.arange(
        times[0],
        times[-1],
        1 / fs
    )

    interpolator = interp1d(
        times,
        values,
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate"
    )

    return uniform_times, interpolator(uniform_times)


def calculate_spectral_features(signal, fs=4):

    signal = np.asarray(signal, dtype=float)

    signal = detrend(signal)

    filtered = bandpass_filter(
        signal,
        RESP_LOW,
        RESP_HIGH,
        fs
    )

    frequencies, power = welch(
        filtered,
        fs=fs,
        nperseg=min(len(filtered), fs * 32)
    )

    valid = (
        (frequencies >= RESP_LOW) &
        (frequencies <= RESP_HIGH)
    )

    frequencies = frequencies[valid]
    power = power[valid]

    if len(power) == 0 or np.sum(power) == 0:
        raise ValueError("Insufficient respiratory spectral power.")

    dominant_frequency = frequencies[
        np.argmax(power)
    ]

    return {
        "dominant_frequency": float(dominant_frequency),
        "estimated_rate": float(dominant_frequency * 60),
        "spectral_power": float(np.sum(power))
    }


def extract_respiratory_features(ppg):

    ppg = np.asarray(ppg, dtype=float)

    if not np.all(np.isfinite(ppg)):
        raise ValueError("PPG contains missing or invalid samples.")

    if len(ppg) < FS * 32:
        raise ValueError("At least 32 seconds of PPG is required.")

    # Remove slow DC component
    ppg_centered = ppg - np.median(ppg)

    # Cardiac-frequency filtering for pulse detection
    cardiac_signal = bandpass_filter(
        ppg_centered,
        0.5,
        8.0,
        FS
    )

    # Detect pulse peaks
    peaks, _ = find_peaks(
        cardiac_signal,
        distance=int(0.3 * FS),
        prominence=max(
            0.05 * np.std(cardiac_signal),
            1e-8
        )
    )

    if len(peaks) < 15:
        raise ValueError("Insufficient PPG pulses detected.")

    # Estimate local pulse troughs
    troughs = []

    amplitudes = []

    for i, peak in enumerate(peaks):

        left = (
            peaks[i - 1]
            if i > 0
            else max(0, peak - FS)
        )

        trough = left + np.argmin(
            cardiac_signal[left:peak]
        )

        troughs.append(trough)

        amplitudes.append(
            cardiac_signal[peak] -
            cardiac_signal[trough]
        )

    troughs = np.array(troughs)

    amplitudes = np.array(amplitudes)

    peak_times = peaks / FS

    # RIIV: respiratory-induced baseline variation
    baseline_signal = bandpass_filter(
        ppg_centered,
        RESP_LOW,
        RESP_HIGH,
        FS
    )

    riiv = np.interp(
        peak_times,
        np.arange(len(ppg)) / FS,
        baseline_signal
    )

    # RIAV: respiratory-induced pulse amplitude variation
    riav = amplitudes

    # RIFV: respiratory-induced pulse frequency variation
    pulse_intervals = np.diff(peak_times)

    interval_times = (
        peak_times[:-1] + peak_times[1:]
    ) / 2

    if np.any(pulse_intervals <= 0):
        raise ValueError("Invalid pulse intervals.")

    pulse_frequency = 1.0 / pulse_intervals

    # Resample all respiratory modulation signals
    _, riiv_uniform = resample_irregular_signal(
        peak_times,
        riiv
    )

    _, riav_uniform = resample_irregular_signal(
        peak_times,
        riav
    )

    _, rifv_uniform = resample_irregular_signal(
        interval_times,
        pulse_frequency
    )

    # Extract spectral features
    features = {}

    for name, signal in [
        ("RIIV", riiv_uniform),
        ("RIAV", riav_uniform),
        ("RIFV", rifv_uniform)
    ]:

        result = calculate_spectral_features(
            signal,
            fs=4
        )

        features[f"{name}_rate"] = result[
            "estimated_rate"
        ]

        features[f"{name}_power"] = result[
            "spectral_power"
        ]

    return features
