import numpy as np

from src.data_loader import load_recording

FS = 125


def calculate_agreement(subject_id=1):

    data = load_recording(subject_id)

    ann1 = data["annotation_1"]
    ann2 = data["annotation_2"]

    # Check annotation ranges
    print("Annotation range validation")

    for name, annotations in [
        ("Annotator 1", ann1),
        ("Annotator 2", ann2)
    ]:

        print(
            name,
            "Minimum:", np.min(annotations),
            "Maximum:", np.max(annotations)
        )

    # Compare annotation locations.
    # Match each breath to the nearest breath from
    # the other annotator within a 0.5-second tolerance.

    tolerance = int(0.5 * FS)

    matched_differences = []

    used_indices = set()

    for sample in ann1:

        distances = np.abs(ann2 - sample)

        for index in np.argsort(distances):

            if index in used_indices:
                continue

            if distances[index] <= tolerance:

                matched_differences.append(
                    distances[index] / FS
                )

                used_indices.add(index)

                break

    print("\nANNOTATION AGREEMENT")

    print("Annotator 1 breaths:", len(ann1))

    print("Annotator 2 breaths:", len(ann2))

    print("Matched breaths:", len(matched_differences))

    if matched_differences:

        print(
            "Mean timing difference:",
            round(np.mean(matched_differences), 4),
            "seconds"
        )

        print(
            "Median timing difference:",
            round(np.median(matched_differences), 4),
            "seconds"
        )

    print("\nValidation completed.")


if __name__ == "__main__":

    calculate_agreement()
