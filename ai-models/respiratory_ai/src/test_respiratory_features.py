from src.data_loader import load_recording

from src.respiratory_features import (
    extract_respiratory_features
)


def main():

    data = load_recording(1)

    ppg = data["ppg"]

    # Use first 32 seconds
    window = ppg[:32 * 125]

    features = extract_respiratory_features(
        window
    )

    print("\nASTRA RESPIRATORY FEATURES")

    for name, value in features.items():

        print(f"{name}: {value:.4f}")


if __name__ == "__main__":

    main()
