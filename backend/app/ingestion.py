from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .models import Measurement

VITALDB_REPLAY_URL = "https://api.vitaldb.net/fhir/Location/{location}/$sample"
SOURCE_NAME = "VitalDB virtual replay"
logger = logging.getLogger(__name__)


class VitalDBClient:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds)

    def fetch_replay(
        self,
        location: str,
        track_code: str,
        window_seconds: int,
        at: datetime | None = None,
    ) -> list[Measurement]:
        logger.info(
            "vitaldb_request location=%s track=%s window_seconds=%d at=%s",
            location,
            track_code,
            window_seconds,
            at.isoformat() if at else "latest",
        )
        params: dict[str, Any] = {
            "code": track_code,
            "window": window_seconds,
        }
        if at is not None:
            params["at"] = at.isoformat()
        response = httpx.get(
            VITALDB_REPLAY_URL.format(location=location),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        measurements = parse_replay_payload(response.json(), track_code)
        logger.info(
            "vitaldb_response location=%s track=%s status=%d measurements=%d",
            location,
            track_code,
            response.status_code,
            len(measurements),
        )
        return measurements


def parse_replay_payload(payload: Any, track_code: str) -> list[Measurement]:
    if isinstance(payload, dict) and payload.get("resourceType") == "Bundle":
        records = [
            item.get("resource", {})
            for item in payload.get("entry", [])
            if isinstance(item, dict)
        ]
    elif isinstance(payload, dict) and payload.get("resourceType") == "Observation":
        records = [payload]
    else:
        raise ValueError("VitalDB replay response was not a FHIR Observation or Bundle")

    measurements: list[Measurement] = []
    for record in records:
        measurements.extend(_observation_measurements(record, track_code))
    return measurements


def _observation_measurements(
    observation: dict[str, Any],
    requested_track_code: str,
) -> list[Measurement]:
    sampled_data = observation.get("valueSampledData")
    if not isinstance(sampled_data, dict):
        raise ValueError("VitalDB Observation did not contain valueSampledData")

    start = _observation_start(observation)
    period_ms = _as_float(sampled_data.get("period"))
    factor = _as_float(sampled_data.get("factor"), default=1.0)
    origin = sampled_data.get("origin", {})
    origin_value = _as_float(origin.get("value"), default=0.0)
    unit = origin.get("unit") or None
    data = sampled_data.get("data", "")
    if not start or period_ms is None or not isinstance(data, str):
        raise ValueError("VitalDB SampledData is missing timestamp, period, or data")

    case_id = _case_id(observation)
    metric = _track_code(observation) or requested_track_code
    measurements: list[Measurement] = []
    for index, token in enumerate(data.split()):
        if token == "E":
            continue
        try:
            raw_value = float(token)
        except ValueError:
            continue
        measurements.append(
            Measurement(
                case_id=case_id,
                recorded_at=start + timedelta(milliseconds=period_ms * index),
                metric=metric,
                value=raw_value * factor + origin_value,
                unit=unit,
                source=SOURCE_NAME,
            )
        )
    return measurements


def _observation_start(observation: dict[str, Any]) -> datetime | None:
    period = observation.get("effectivePeriod", {})
    value = period.get("start") if isinstance(period, dict) else None
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _case_id(observation: dict[str, Any]) -> str:
    encounter = observation.get("encounter", {})
    reference = encounter.get("reference") if isinstance(encounter, dict) else None
    if isinstance(reference, str) and reference:
        return reference.rsplit("/", 1)[-1]
    for extension in observation.get("extension", []):
        if extension.get("url", "").endswith("replay-source"):
            for nested in extension.get("extension", []):
                if nested.get("url") == "caseid" and nested.get("valueInteger") is not None:
                    return str(nested["valueInteger"])
    raise ValueError("VitalDB Observation did not contain a case identity")


def _track_code(observation: dict[str, Any]) -> str | None:
    code = observation.get("code", {})
    if isinstance(code, dict):
        for coding in code.get("coding", []):
            if coding.get("code"):
                return str(coding["code"])
        if code.get("text"):
            return str(code["text"])
    return None


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

__all__ = ["SOURCE_NAME", "VITALDB_REPLAY_URL", "VitalDBClient", "parse_replay_payload"]
