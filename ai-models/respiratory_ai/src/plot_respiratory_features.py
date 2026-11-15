import numpy as np
import matplotlib.pyplot as plt

from scipy.signal import butter, sosfiltfilt, find_peaks

from src.config import PLOT_DIR
from src.data_loader import load_recording

FS = 125


def bandpass(signal, low, high, fs):
    sos = butter(
        3,
        [low, high],
        btype="bandpass",
        fs=fs,
        output="sos"
    )
    return sosfiltfilt(sos, signal)


def main():

    data = load_recording(1)

    ppg = data["ppg"][:32 * FS]

    time = np.arange(len(ppg)) / FS

    cardiac = bandpass(ppg, 0.5, 8.0, FS)

    peaks, _ = find_peaks(
        cardiac,
        distance=int(0.3 * FS),
        prominence=max(0.05 * np.std(cardiac), 1e-8)
    )

    respiratory_component = bandpass(
        ppg,
        0.08,
        0.70,
        FS
    )

    fig, axes = plt.subplots(3, 1, figsize=(14, 9))

    axes[0].plot(time, ppg)
    axes[0].set_title("Raw PPG waveform")
    axes[0].set_ylabel("Amplitude")

    axes[1].plot(time, cardiac)
    axes[1].scatter(
        peaks / FS,
        cardiac[peaks],
        color="red",
        s=15,
        label="Detected pulses"
    )
    axes[1].set_title("Cardiac PPG signal and detected peaks")
    axes[1].set_ylabel("Amplitude")
    axes[1].legend()

    axes[2].plot(time, respiratory_component)
    axes[2].set_title("Respiratory-frequency component extracted from PPG")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].set_ylabel("Amplitude")

    plt.tight_layout()

    plot_path = PLOT_DIR / "subject01_respiratory_features.png"
    fig.savefig(plot_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print("Plot saved to:", plot_path)
    print("Detected pulses:", len(peaks))
    print("Pulse detection rate:", len(peaks) / 32 * 60, "per minute")


if __name__ == "__main__":
    main()
