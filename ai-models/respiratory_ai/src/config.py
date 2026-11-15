from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_DIR = BASE_DIR / "bidmc_csv"

MODEL_DIR = BASE_DIR / "models"

OUTPUT_DIR = BASE_DIR / "outputs"

EVALUATION_DIR = OUTPUT_DIR / "evaluation"

PLOT_DIR = OUTPUT_DIR / "plots"


# Dataset sampling frequencies
PPG_SAMPLING_RATE = 125
NUMERICS_SAMPLING_RATE = 1


# Signal processing
WINDOW_SECONDS = 32
STEP_SECONDS = 16

RESPIRATORY_LOW_CUTOFF = 0.08
RESPIRATORY_HIGH_CUTOFF = 0.70


# Model configuration
RANDOM_STATE = 42

# Create directories automatically
for directory in [
    MODEL_DIR,
    EVALUATION_DIR,
    PLOT_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)
