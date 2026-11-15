from __future__ import annotations

from typing import Literal

from .models import Measurement

DemoScenario = Literal["normal", "tachycardia", "hypoxia", "hypotension"]


def apply_demo_scenario(
    measurements: list[Measurement],
    scenario: DemoScenario,
) -> list[Measurement]:
    if scenario == "normal":
        return measurements

    transformed: list[Measurement] = []
    source = f"VitalDB replay simulation: {scenario}"
    for measurement in measurements:
        value = _scenario_value(measurement.metric, measurement.value, scenario)
        if value is None:
            transformed.append(measurement)
            continue
        transformed.append(
            measurement.model_copy(update={"value": value, "source": source})
        )
    return transformed


def _scenario_value(
    metric: str,
    value: float,
    scenario: DemoScenario,
) -> float | None:
    if scenario == "tachycardia" and metric == "Solar8000/HR":
        return max(value * 3, 180)
    if scenario == "hypoxia" and metric == "Solar8000/PLETH_SPO2":
        return min(value, 70)
    if scenario == "hypoxia" and metric == "Solar8000/HR":
        return max(value * 2, 120)
    if scenario == "hypotension" and metric == "Solar8000/NIBP_SBP":
        return min(value * 0.4, 60)
    if scenario == "hypotension" and metric == "Solar8000/NIBP_DBP":
        return min(value * 0.5, 40)
    return None


__all__ = ["DemoScenario", "apply_demo_scenario"]
