from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List

from src.predictor import predictor


app = FastAPI(
    title="ASTRA Respiratory AI",
    description="PPG-based respiratory-rate estimation prototype",
    version="1.0.0"
)


class PPGRequest(BaseModel):

    ppg_samples: List[float] = Field(
        ...,
        min_length=4000,
        description="PPG waveform samples"
    )

    sampling_rate: int = Field(
        default=125,
        description="PPG sampling frequency in Hz"
    )


@app.get("/")
def home():

    return {
        "system": "ASTRA Respiratory AI",
        "status": "online",
        "version": "1.0.0"
    }


@app.post("/respiratory/predict")
def predict_respiratory_rate(request: PPGRequest):

    if request.sampling_rate != 125:
        raise HTTPException(
            status_code=400,
            detail="This model currently requires a sampling rate of 125 Hz."
        )

    try:

        result = predictor.predict(request.ppg_samples)

        return {
            "success": True,
            "prediction": result
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )