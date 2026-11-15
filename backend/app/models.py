from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Measurement(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    recorded_at: datetime
    metric: str = Field(min_length=1)
    value: float
    unit: str | None = None
    source: str = "VitalDB"


class ReplayRequest(BaseModel):
    location: str = Field(default="OR1", min_length=1)
    track_code: str = Field(default="SNUADC/ECG_II", min_length=1)
    window_seconds: int = Field(default=10, ge=1, le=300)
    at: datetime | None = None
    scenario: Literal["normal", "tachycardia", "hypoxia", "hypotension"] = "normal"


class IngestResponse(BaseModel):
    received: int
    inserted: int
    source: str


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

__all__ = ["AssistantRequest", "IngestResponse", "Measurement", "ReplayRequest"]
