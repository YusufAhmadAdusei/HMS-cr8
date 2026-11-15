from datetime import datetime, timezone

from backend.app.database import MeasurementStore
from backend.app.ingestion import parse_replay_payload
from backend.app.simulation import apply_demo_scenario
from backend.app.models import Measurement


def test_parse_replay_payload_accepts_fhir_bundle() -> None:
    payload = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "encounter": {"reference": "Encounter/5871"},
                    "code": {"coding": [{"code": "Solar8000/HR"}]},
                    "effectivePeriod": {
                        "start": "2026-11-14T12:00:00Z",
                    },
                    "valueSampledData": {
                        "origin": {"value": 0, "unit": "/min"},
                        "period": 1000,
                        "factor": 1,
                        "data": "72 E 75",
                    },
                }
            }
        ]
    }

    measurements = parse_replay_payload(payload, "SNUADC/ECG_II")

    assert len(measurements) == 2
    assert measurements[0].value == 72
    assert measurements[0].case_id == "5871"
    assert measurements[0].metric == "Solar8000/HR"
    assert measurements[0].unit == "/min"
    assert measurements[0].recorded_at == datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def test_measurement_store_deduplicates_replay_samples(tmp_path) -> None:
    store = MeasurementStore(tmp_path / "measurements.sqlite3")
    measurement = parse_replay_payload(
        {
            "resourceType": "Observation",
            "encounter": {"reference": "Encounter/5871"},
            "code": {"coding": [{"code": "Solar8000/HR"}]},
            "effectivePeriod": {"start": "2026-11-14T12:00:00Z"},
            "valueSampledData": {
                "origin": {"value": 0, "unit": "/min"},
                "period": 1000,
                "factor": 1,
                "data": "72",
            },
        },
        "SNUADC/ECG_II",
    )[0]

    assert store.add_many([measurement, measurement]) == 1
    assert len(store.latest()) == 1


def test_demo_anomaly_scenario_is_labeled_and_changes_supported_metric() -> None:
    measurement = Measurement(
        case_id="5871",
        recorded_at=datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc),
        metric="Solar8000/HR",
        value=63,
        unit="/min",
    )

    transformed = apply_demo_scenario([measurement], "tachycardia")

    assert transformed[0].value == 189
    assert transformed[0].source == "VitalDB replay simulation: tachycardia"
