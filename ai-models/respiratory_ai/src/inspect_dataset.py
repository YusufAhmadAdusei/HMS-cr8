import numpy as np

from src.data_loader import load_recording

from src.config import PPG_SAMPLING_RATE


data = load_recording(1)

print("\n========== ASTRA DATASET INSPECTION ==========\n")

for name, values in data.items():

    print(f"{name}:")
    print("Samples:", len(values))
    print("First 10 values:", values[:10])
    print("Missing values:", np.isnan(values).sum())
    print()

print("PPG duration:",
      len(data["ppg"]) / PPG_SAMPLING_RATE,
      "seconds")

print("RESP duration:",
      len(data["resp_signal"]) / PPG_SAMPLING_RATE,
      "seconds")

print("\n========== INSPECTION COMPLETE ==========")
