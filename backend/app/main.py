from __future__ import annotations

import httpx
import logging
import os
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent import Agent
from .database import MeasurementStore
from .health_analysis import build_health_summary
from .ingestion import VitalDBClient
from .logging_config import configure_logging
from .models import AssistantRequest, IngestResponse, Measurement, ReplayRequest
from ml.anomaly_detection import AnomalyDetector


configure_logging()
logger = logging.getLogger(__name__)
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
if os.path.exists(model_path):
    detector = AnomalyDetector.load(model_path)
    logger.info("model_loaded path=%s", model_path)
else:
    detector = None
    logger.warning("model_unavailable path=%s", model_path)


@app.middleware("http")
async def log_requests(request, call_next):
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "request_failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/health")
def health() -> dict[str, object]:
    logger.debug("health_check model_loaded=%s", detector is not None)
    return {
        "status": "ok",
        "data_source": "VitalDB",
        "model_loaded": detector is not None,
    }


@app.get("/cases", response_model=list[str])
def get_cases() -> list[str]:
    cases = store.case_ids()
    logger.info("cases_listed count=%d", len(cases))
    return cases


@app.get("/measurements", response_model=list[Measurement])
def get_measurements(
    case_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[Measurement]:
    measurements = store.latest(case_id=case_id, limit=limit)
    logger.info(
        "measurements_listed case_id=%s count=%d limit=%d",
        case_id or "all",
        len(measurements),
        limit,
    )
    return measurements


@app.get("/health-summary")
def get_health_summary(case_id: str | None = Query(default=None)) -> dict:
    measurements = [
        measurement.model_dump(mode="json")
        for measurement in store.all_for_case(case_id)
    ]
    summary = build_health_summary(measurements, detector=detector)
    logger.info(
        "health_summary_built case_id=%s measurements=%d status=%s anomalies=%d",
        case_id or "all",
        len(measurements),
        summary["status"],
        len(summary["anomalies"]),
    )
    return summary

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
        logger.exception(
            "assistant_failed case_id=%s question_length=%d",
            case_id or "all",
            len(request.question),
        )
        raise HTTPException(status_code=503, detail=str(error)) from error
    logger.info(
        "assistant_completed case_id=%s question_length=%d",
        case_id or "all",
        len(request.question),
    )
    return {"answer": answer}


@app.post("/ingest/vitaldb/replay", response_model=IngestResponse)
def ingest_replay(request: ReplayRequest) -> IngestResponse:
    try:
        measurements = vitaldb.fetch_replay(
            request.location, request.track_code, request.window_seconds, request.at
        )
    except (ValueError, httpx.HTTPError) as error:
        logger.exception(
            "vitaldb_ingestion_failed location=%s track=%s",
            request.location,
            request.track_code,
        )
        raise HTTPException(status_code=502, detail=f"VitalDB ingestion failed: {error}") from error
    inserted = store.add_many(measurements)
    logger.info(
        "vitaldb_ingestion_completed location=%s track=%s received=%d inserted=%d",
        request.location,
        request.track_code,
        len(measurements),
        inserted,
    )
    return IngestResponse(
        received=len(measurements), inserted=inserted, source="VitalDB virtual replay"
    )
