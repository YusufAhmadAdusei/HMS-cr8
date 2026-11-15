from __future__ import annotations

import re

import httpx

from .models import EnvironmentalMeasurement

NASA_EDA_API = "https://visualization.osdr.nasa.gov/eda/api"
NASA_EDA_SOURCE = "NASA OSDR Environmental Data Application"
METRICS = {
    "temperature_iss": ("temperature", "°C"),
    "humidity_iss": ("relative_humidity", "%"),
    "co2_iss": ("co2", "ppm"),
}


class NasaEdaClient:
    """Fetch historical ISS cabin telemetry from NASA's documented EDA API."""

    def __init__(self, timeout_seconds: float = 45.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds)

    def fetch_telemetry(self, mission: str) -> list[EnvironmentalMeasurement]:
        if not re.fullmatch(r"[A-Za-z0-9-]+", mission):
            raise ValueError("Mission identifier may only contain letters, numbers, and hyphens")
        response = httpx.get(
            f"{NASA_EDA_API}/missions/{mission}/telemetry_data/",
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("NASA EDA telemetry response did not contain a value list")

        measurements: list[EnvironmentalMeasurement] = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("time"), str):
                continue
            for field, (metric, unit) in METRICS.items():
                value = row.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    measurements.append(
                        EnvironmentalMeasurement(
                            mission=mission,
                            recorded_at=row["time"],
                            metric=metric,
                            value=float(value),
                            unit=unit,
                            source=NASA_EDA_SOURCE,
                        )
                    )
        return measurements


__all__ = ["METRICS", "NASA_EDA_API", "NASA_EDA_SOURCE", "NasaEdaClient"]
