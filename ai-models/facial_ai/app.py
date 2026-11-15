
import os
import tempfile

from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional

from facedetector import preprocess_face
from openai_analyzer import analyze_facial_health

app = FastAPI(
    title="ASTRA FaceHealth API",
    description="Astronaut facial and skin health screening",
    version="1.0.0"
)

def process_upload(image_bytes):

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".jpg",
            delete=False
        ) as temp:

            temp.write(image_bytes)
            temp_path = temp.name

        return preprocess_face(temp_path)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/")
def home():

    return {
        "system": "ASTRA FaceHealth AI",
        "status": "online",
        "module": "Facial Health Screening"
    }

@app.post("/facial/analyze")
def facial_analysis(
    current_image: UploadFile = File(...),
    baseline_image: Optional[UploadFile] = File(None)
):

    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]

    if current_image.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format."
        )

    try:

        current_bytes = current_image.file.read()

        if len(current_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Image exceeds 10 MB limit."
            )

        current = process_upload(current_bytes)

        baseline = None

        if baseline_image:

            if baseline_image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=415,
                    detail="Unsupported baseline image format."
                )

            baseline_bytes = baseline_image.file.read()

            if len(baseline_bytes) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="Baseline image exceeds 10 MB limit."
                )

            baseline = process_upload(baseline_bytes)

        result = analyze_facial_health(
            current_image=current["image_base64"],
            baseline_image=(
                baseline["image_base64"]
                if baseline else None
            ),
            quality_warnings=current["quality_warnings"]
        )

        return {
            "module": "facial_health",
            "analysis": result,
            "technical_metadata": {
                "face_detection": "successful",
                "image_blur_score": current["blur_score"],
                "image_brightness": current["brightness"],
                "baseline_provided": baseline is not None
            }
        }

    except HTTPException:
        raise

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail="Facial analysis failed. Check server logs."
        )