import argparse
from pathlib import Path

from stress_ai.predictor import get_stress_predictor


def main():
    parser = argparse.ArgumentParser(
        description="Run a stress prediction for a WAV audio file."
    )
    parser.add_argument(
        "audio_path",
        type=Path,
        help="Path to an audio file containing at least one second of speech.",
    )
    args = parser.parse_args()

    if not args.audio_path.is_file():
        parser.error(f"audio file not found: {args.audio_path}")

    result = get_stress_predictor().predict(args.audio_path)


    print("Prediction:", result["prediction"])

    print(
        "Stress probability:",
        f'{result["stress_probability"]}%'
    )

    print(
        "Not stressed probability:",
        f'{result["not_stressed_probability"]}%'
    )

    print("Model:", result["model"])

    print("Status:", result["status"])



if __name__ == "__main__":
    main()
