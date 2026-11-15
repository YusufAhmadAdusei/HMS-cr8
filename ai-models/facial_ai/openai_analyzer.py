
import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from schemas import FACE_HEALTH_SCHEMA

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-6.1-terra"
)

SYSTEM_INSTRUCTIONS = """
You are the visual observation engine of ASTRA,
an experimental astronaut health-monitoring system.

Your task is to assess visible skin and facial
characteristics in submitted photographs.

IMPORTANT RULES:

1. Do not diagnose diseases or medical conditions.
2. Do not infer immune dysfunction, anemia,
   infection, cancer, or cardiovascular disease
   from facial appearance.
3. Only describe features visibly supported
   by the submitted photographs.
4. Distinguish visible observations from
   uncertain interpretations.
5. Never invent findings when the image
   does not provide sufficient evidence.
6. Do not infer identity, ethnicity, emotion,
   personality, or mental health from appearance.
7. Do not interpret normal skin pigmentation
   as an abnormality.
8. Account for lighting, shadows, camera quality,
   skin tone, and image limitations.
9. If image quality is inadequate, state that
   assessment is limited.
10. If an observation warrants clinical attention,
    recommend review by qualified medical personnel.

For longitudinal comparisons:
- Compare the same anatomical regions.
- Account for differences in lighting, pose,
  camera distance and image quality.
- Do not claim a new abnormality unless there
  is sufficient visual evidence.
- Use inconclusive when comparison is unreliable.

Return only the requested structured output.
"""

def analyze_facial_health(
    current_image,
    baseline_image=None,
    quality_warnings=None
):

    content = [
        {
            "type": "input_text",
            "text": SYSTEM_INSTRUCTIONS
        },
        {
            "type": "input_text",
            "text": """
            Analyze the CURRENT astronaut facial image.

            Identify visible skin observations only.

            Do not make medical diagnoses.
            """
        },
        {
            "type": "input_image",
            "image_url": (
                "data:image/jpeg;base64,"
                + current_image
            ),
            "detail": "high"
        }
    ]

    if baseline_image:

        content.append({
            "type": "input_text",
            "text": """
            The next image is a PREVIOUS facial image
            of the same consenting astronaut.

            Compare it with the current image.
            Describe only clearly visible changes.
            Account for differences in lighting and pose.
            """
        })

        content.append({
            "type": "input_image",
            "image_url": (
                "data:image/jpeg;base64,"
                + baseline_image
            ),
            "detail": "high"
        })

    if quality_warnings:

        content.append({
            "type": "input_text",
            "text": (
                "Image quality warnings: "
                + ", ".join(quality_warnings)
            )
        })

    response = client.responses.create(
        model=MODEL,

        input=[
            {
                "role": "user",
                "content": content
            }
        ],

        text={
            "format": {
                "type": "json_schema",
                "name": "face_health_screening",
                "strict": True,
                "schema": FACE_HEALTH_SCHEMA
            }
        }
    )

    if not response.output_text:
        raise RuntimeError(
            "The model returned no structured output."
        )

    result = json.loads(response.output_text)

    return result