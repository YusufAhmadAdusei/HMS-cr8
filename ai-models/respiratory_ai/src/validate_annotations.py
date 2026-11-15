import numpy as np
import matplotlib.pyplot as plt

from src.data_loader import load_recording
from src.config import PPG_SAMPLING_RATE


def validate_annotations(subject_id=1):

    data = load_recording(subject_id)

    resp = data["resp_signal"]

    ann1 = data["annotation_1"]
    ann2 = data["annotation_2"]

    fs = PPG_SAMPLING_RATE

    print("\n========== ANNOTATION VALIDATION ==========")

    for name, annotations in [
        ("Annotator 1", ann1),
        ("Annotator 2", ann2)
    ]:

        print(f"\n{name}")

        print("Number of annotations:", len(annotations))

        print("First 10:", annotations[:10])

        print("Minimum:", np.min(annotations))

        print("Maximum:", np.max(annotations))

        print(
            "Estimated recording duration:",
            np.max(annotations) / fs,
            "seconds"
        )

        # Convert annotation sample numbers to seconds
        times = annotations / fs

        intervals = np.diff(times)

        if len(intervals):

            print(
                "Mean interval between breaths:",
                np.mean(intervals),
                "seconds"
            )

            print(
                "Estimated mean respiratory rate:",
                60 / np.mean(intervals),
                "breaths/min"
            )

    # Plot first 30 seconds of respiratory waveform
    duration = 30

    samples = duration * fs

    time = np.arange(samples) / fs

    plt.figure(figsize=(14, 5))

    plt.plot(
        time,
        resp[:samples],
        label="Respiratory waveform"
    )

    for annotation in ann1:

        annotation_time = annotation / fs

        if annotation_time <= duration:

            plt.axvline(
                annotation_time,
                linestyle="--",
                alpha=0.5
            )

    plt.title("BIDMC Respiratory Signal and Breath Annotations")

    plt.xlabel("Time (seconds)")

    plt.ylabel("Respiratory amplitude")

    plt.legend()

    plt.grid()

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":

    validate_annotations()