from __future__ import annotations

import httpx
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent import Agent
from .database import MeasurementStore
from .health_analysis import build_health_summary
from .ingestion import VitalDBClient
from .models import AssistantRequest, IngestResponse, Measurement, ReplayRequest
from ml.anomaly_detection import AnomalyDetector


app = FastAPI(title="HMS-cr8 Backend", version="0.2.0")
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = MeasurementStore()
vitaldb = VitalDBClient()
model_path = os.getenv("HMS_MODEL_PATH", "ml/model/isolation_forest.joblib")
detector = AnomalyDetector.load(model_path) if os.path.exists(model_path) else None


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "data_source": "VitalDB",
        "model_loaded": detector is not None,
    }


@app.get("/cases", response_model=list[str])
def get_cases() -> list[str]:
    return store.case_ids()


@app.get("/measurements", response_model=list[Measurement])
def get_measurements(
    case_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[Measurement]:
    return store.latest(case_id=case_id, limit=limit)


@app.get("/health-summary")
def get_health_summary(case_id: str | None = Query(default=None)) -> dict:
    measurements = [
        measurement.model_dump(mode="json")
        for measurement in store.all_for_case(case_id)
    ]
    return build_health_summary(measurements, detector=detector)

@app.post("/assistant/explain")
def assistant_explain(
    request: AssistantRequest,
    case_id: str | None = Query(default=None),
) -> dict[str, str]:
    measurements = [
        measurement.model_dump(mode="json")
        for measurement in store.all_for_case(case_id)
    ]
    summary = build_health_summary(measurements, detector=detector)
    try:
        answer = Agent(summary).chat(request.question)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"answer": answer}


@app.post("/ingest/vitaldb/replay", response_model=IngestResponse)
def ingest_replay(request: ReplayRequest) -> IngestResponse:
    try:
        measurements = vitaldb.fetch_replay(
            request.location, request.track_code, request.window_seconds, request.at
        )
    except (ValueError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502, detail=f"VitalDB ingestion failed: {error}") from error
    inserted = store.add_many(measurements)
    return IngestResponse(
        received=len(measurements), inserted=inserted, source="VitalDB virtual replay"
    )
