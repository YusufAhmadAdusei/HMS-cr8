import numpy as np
import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.data_loader import load_recording
from src.respiratory_features import extract_respiratory_features


# Configuration
FS = 125
WINDOW_SECONDS = 32
STEP_SECONDS = 16

FEATURE_COLUMNS = [
    "RIIV_rate",
    "RIIV_power",
    "RIAV_rate",
    "RIAV_power",
    "RIFV_rate",
    "RIFV_power"
]

MODEL_PATH = Path("models/respiratory_rate_model.joblib")
OUTPUT_PATH = Path("outputs/evaluation/respiratory_training_windows.csv")


def calculate_annotation_rate(annotations, start_time, end_time):
    """
    Estimate respiratory rate using manual breath annotations.
    Annotation values are assumed to be signal sample indices.
    """

    times = np.asarray(annotations, dtype=float) / FS

    selected = times[
        (times >= start_time) &
        (times < end_time)
    ]

    if len(selected) < 5:
        return None

    intervals = np.diff(np.sort(selected))

    if len(intervals) == 0:
        return None

    median_interval = np.median(intervals)

    if median_interval <= 0:
        return None

    return 60.0 / median_interval


def build_dataset():

    rows = []

    window_samples = WINDOW_SECONDS * FS
    step_samples = STEP_SECONDS * FS

    for subject_id in range(1, 54):

        print(f"\nProcessing subject {subject_id:02d}...")

        try:
            data = load_recording(subject_id)
        except Exception as error:
            print("Could not load recording:", error)
            continue

        ppg = data["ppg"]

        annotations_1 = data["annotation_1"]
        annotations_2 = data["annotation_2"]

        for start in range(
            0,
            len(ppg) - window_samples + 1,
            step_samples
        ):

            end = start + window_samples

            start_time = start / FS
            end_time = end / FS

            window = ppg[start:end]

            if not np.all(np.isfinite(window)):
                continue

            # Independent manual annotation targets
            target_1 = calculate_annotation_rate(
                annotations_1,
                start_time,
                end_time
            )

            target_2 = calculate_annotation_rate(
                annotations_2,
                start_time,
                end_time
            )

            valid_targets = [
                value for value in [target_1, target_2]
                if value is not None
            ]

            if not valid_targets:
                continue

            # Average available annotator estimates
            target_rate = float(np.mean(valid_targets))

            try:
                features = extract_respiratory_features(window)

                if not all(
                    np.isfinite(features[column])
                    for column in FEATURE_COLUMNS
                ):
                    continue

            except Exception as error:
                print(
                    f"Feature extraction failed for subject "
                    f"{subject_id:02d}: {error}"
                )
                continue

            row = {
                "subject_id": subject_id,
                "respiratory_rate": target_rate,
                **features
            }

            rows.append(row)

        print("Windows collected:", len(rows))

    dataset = pd.DataFrame(rows)

    if dataset.empty:
        raise RuntimeError(
            "No training windows were generated. "
            "Check dataset paths and annotation indexing."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_PATH, index=False)

    print("\nDATASET GENERATION COMPLETE")
    print("Total windows:", len(dataset))
    print("Unique subjects:", dataset["subject_id"].nunique())
    print("Saved:", OUTPUT_PATH)

    return dataset


def train_model(dataset):

    X = dataset[FEATURE_COLUMNS]
    y = dataset["respiratory_rate"]
    groups = dataset["subject_id"]

    # Split by subject to prevent subject-level data leakage
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42
    )

    train_indices, test_indices = next(
        splitter.split(X, y, groups)
    )

    X_train = X.iloc[train_indices]
    X_test = X.iloc[test_indices]

    y_train = y.iloc[train_indices]
    y_test = y.iloc[test_indices]

    model = RandomForestRegressor(
        n_estimators=400,
        max_features=0.8,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    print("\nTraining respiratory model...")

    model.fit(X_train, y_train)

    print("\nFEATURE IMPORTANCE")
    print("----------------------------")

    importance = pd.DataFrame({
        "Feature": FEATURE_COLUMNS,
        "Importance": model.feature_importances_
    })

    importance = importance.sort_values(
        by="Importance",
        ascending=False
    )

    print(importance.to_string(index=False))

    predictions = model.predict(X_test)

    # Baseline: always predict training-set mean
    mean_prediction = np.full(
        len(y_test),
        y_train.mean()
    )

    baseline_mae = mean_absolute_error(
        y_test,
        mean_prediction
    )

    baseline_rmse = np.sqrt(
        mean_squared_error(y_test, mean_prediction)
    )

    baseline_r2 = r2_score(
        y_test,
        mean_prediction
    )

    print("\nMEAN BASELINE")
    print("----------------------------")
    print(f"MAE:  {baseline_mae:.3f}")
    print(f"RMSE: {baseline_rmse:.3f}")
    print(f"R²:   {baseline_r2:.3f}")

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    print("\nASTRA RESPIRATORY MODEL RESULTS")
    print("--------------------------------")
    print(f"Training windows: {len(X_train)}")
    print(f"Testing windows:  {len(X_test)}")
    print(f"Testing subjects: {groups.iloc[test_indices].nunique()}")
    print(f"MAE:  {mae:.3f} breaths/min")
    print(f"RMSE: {rmse:.3f} breaths/min")
    print(f"R²:   {r2:.3f}")

    # Compare against individual PPG-derived estimates
    print("\nINDIVIDUAL FEATURE BASELINES")

    for feature in ["RIIV_rate", "RIAV_rate", "RIFV_rate"]:

        baseline_mae = mean_absolute_error(
            y_test,
            X_test[feature]
        )

        print(f"{feature} MAE: {baseline_mae:.3f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "features": FEATURE_COLUMNS,
            "sampling_rate": FS,
            "window_seconds": WINDOW_SECONDS
        },
        MODEL_PATH
    )

    print("\nModel saved to:", MODEL_PATH)


def main():

    dataset = build_dataset()

    train_model(dataset)


if __name__ == "__main__":
    main()
