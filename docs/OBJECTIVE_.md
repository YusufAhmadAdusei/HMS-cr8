# Objective

Improve the existing HMS-cr8 implementation so that it more convincingly addresses the NASA Space Apps Challenge problem: Health Monitoring Software for Astronauts on Space Missions.

Do not rebuild the application or introduce unnecessary architectural complexity.

Preserve the existing FastAPI backend, React frontend, SQLite persistence, VitalDB integration, Isolation Forest model, and AI assistant.

## 1. NASA ISS Environmental Data Integration

Investigate NASA's Environmental Data Application (EDA):

https://visualization.osdr.nasa.gov/eda/

Official NASA resources:
- https://github.com/nasa/OSDR_Tutorials/blob/main/source/pages/guides/environmental_data_application.md
- https://science.nasa.gov/biological-physical/data/osdr/

Determine the simplest reliable way to obtain actual ISS environmental telemetry.

Prioritize:
- CO2 concentration.
- Temperature.
- Relative humidity.
- Radiation measurements, if readily accessible.

First inspect the available data formats, API capabilities, and download mechanisms. Do not invent endpoints.

Implement a small environmental data ingestion module.

Requirements:
- Preserve original timestamps, units, mission identifiers, and source attribution.
- Store environmental measurements separately from physiological measurements.
- Expose an API endpoint to retrieve environmental measurements.
- Display environmental trends in the dashboard.
- Label these as historical NASA ISS environmental measurements.
- Do not imply that they are live measurements or belong to the same mission/time period as VitalDB recordings.

If direct API integration proves impractical, use a NASA-provided downloadable data table and build a reliable local data ingestion pipeline instead.

## 2. ML Model Evaluation

The Isolation Forest model has already been trained using six VitalDB cases, and inference works.

Do not unnecessarily retrain or replace it.

Inspect:
- ml/features.py
- ml/anomaly_detection.py
- ml/pipeline.py
- ml/train.py
- Existing model artifact and training metadata.

Produce an evaluation report that includes:
- Cases used.
- Number of windows per split.
- Feature columns.
- Training and evaluation methodology.
- Anomaly-score distributions.
- Anomaly detection examples from held-out cases.
- Known limitations.

Verify that the actual dataset is split by case, not by individual time windows.

Do not report accuracy, precision, recall, or F1 unless appropriate ground-truth labels exist.

Do not claim astronaut-specific validation.

## 3. Temporal Demonstration Scenarios

Improve the existing scenarios:
- Normal.
- Tachycardia.
- Hypoxia.
- Hypotension.

The current scenario system should be inspected before modification.

Implement temporal progression rather than simply changing individual values.

Demonstrations should support:
- Normal baseline.
- Gradual deterioration.
- Sudden physiological changes.
- Persistent anomalies.
- Recovery.

Scenarios must:
- Generate clearly labelled demonstration data.
- Preserve timestamps.
- Be reproducible.
- Remain separate from actual VitalDB measurements.
- Display a clear DEMONSTRATION DATA indicator.

Do not invent medical diagnoses or present illustrative values as validated astronaut thresholds.

## 4. Replace the Existing Health Score

Do not remove the dashboard indicator without replacing its functionality.

Inspect how the current score is calculated.

Replace it with a Monitoring Readiness Score.

It should represent the reliability and completeness of the monitoring system, not the astronaut's medical condition.

Calculate it from actual system measurements, including:
- Signal coverage.
- Data freshness.
- Signal continuity.
- Data quality.
- Monitoring model availability.

Display the individual components so users can understand the score.

Do not automatically penalize the score simply because an anomaly was detected.

Clearly explain that Monitoring Readiness is a system-quality indicator, not a health assessment.

## 5. AI Assistant

Keep the existing read-only architecture.

Improve explanations so the assistant can distinguish:
- Physiological observations.
- Model-detected anomalies.
- Data-quality issues.
- Monitoring readiness.
- NASA environmental context.
- Simulated demonstration events.

The assistant must never claim that an environmental measurement caused a physiological anomaly without evidence.

It must identify the source and timestamp of relevant observations.

## 6. Integration and Verification

Verify the complete pipeline:

VitalDB replay
    → Physiological ingestion
    → SQLite
    → Feature extraction
    → Trained Isolation Forest
    → Anomaly results
    → Health summary
    → Dashboard and assistant

NASA EDA
    → Environmental ingestion
    → Environmental storage
    → Environmental API
    → Dashboard and contextual analysis

Demo scenarios
    → Controlled temporal signal generation
    → Physiological ingestion
    → Model inference
    → Anomaly presentation

Run the existing tests and add targeted tests for new functionality.

Do not claim functionality is complete unless it has been implemented and tested.

## Constraints

- Do not introduce microservices.
- Do not add Kafka, Redis, Celery, Kubernetes, or other unnecessary infrastructure.
- Do not replace the existing ML model without a demonstrated reason.
- Do not redesign the entire frontend.
- Do not fabricate NASA data.
- Do not present VitalDB measurements as astronaut telemetry.
- Do not present Isolation Forest anomaly scores as medical probabilities.
- Do not claim the system is medically or operationally validated.

Before changing files, inspect the existing implementation and report the proposed changes. Then implement only what is necessary.