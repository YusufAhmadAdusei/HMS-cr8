# HMS-cr8 — Implementation Alignment & Engineering Directive

## 1. Project Objective

HMS-cr8 is a physiological health-monitoring and decision-support prototype designed around an International Space Station (ISS) mission scenario.

The system should demonstrate the ability to:

1. Retrieve actual physiological measurements from an external data source.
2. Process and analyse incoming measurements.
3. Use a trained machine learning model to identify unusual physiological patterns.
4. Store and retrieve measurements and analytical results.
5. Present measurements, trends, and detected anomalies through a dashboard.
6. Provide an AI assistant that explains analytical findings using retrieved evidence.

This is a hackathon MVP. Prioritise functionality, scientific credibility, and integration over architectural complexity.

**Do not introduce unnecessary infrastructure or additional features.**

---

## 2. Non-Negotiable Architecture

The application must follow this simplified architecture:

```text
                VITALDB API
                     |
                     v
              DATA INGESTION
                     |
                     v
             DATA PROCESSING
                     |
                +----+----+
                |         |
                v         v
             DATABASE   ML MODEL
                |         |
                +----+----+
                     |
                     v
              HEALTH ANALYSIS
                     |
                +----+----+
                |         |
                v         v
             DASHBOARD  AI ASSISTANT
```

The backend should remain a single FastAPI application.

The ML model can remain in a separate `ml/` directory for training and evaluation, but model inference must be accessible to the backend.

Do not introduce:
- Microservices.
- Kafka.
- Redis.
- Celery.
- Kubernetes.
- Additional databases.
- Unnecessary agent frameworks or orchestration layers.

Use the existing implementation wherever it is functional.

---

## 3. Data Ingestion

### Data source

VitalDB is the initial physiological data source.

Use its virtual replay functionality to retrieve recorded physiological measurements.

Important: VitalDB recordings represent surgical-patient data, not astronaut telemetry.

The application must preserve this distinction.

### Requirements

The ingestion pipeline must:

- Retrieve measurements from VitalDB.
- Support the required physiological tracks.
- Validate timestamps and numeric values.
- Preserve case identity.
- Preserve measurement names and units.
- Reject malformed samples.
- Handle missing measurements explicitly.
- Prevent duplicate database records.
- Avoid mixing measurements from different cases.

### Validation

Before proceeding, demonstrate that:

1. The actual VitalDB replay request works.
2. The response structure is understood.
3. Measurements are correctly extracted.
4. Timestamps are correctly interpreted.
5. Units are correct.
6. Measurements are successfully persisted.
7. Database records can be retrieved through the API.

Do not assume integration works because the ingestion code exists.

---

## 4. Data Processing and Feature Extraction

The processing pipeline should convert incoming measurements into usable features for anomaly detection.

Use time-based windows.

A starting window of 60 seconds may be used if compatible with the actual sampling frequency and available data.

Potential features include:

- Mean heart rate.
- Heart-rate standard deviation.
- Mean systolic blood pressure.
- Mean diastolic blood pressure.
- Mean SpO₂.
- Mean temperature.
- Mean respiratory rate.
- Rate of change for selected measurements.
- Rolling variability.

Only calculate features for measurements that actually exist in the recording.

Do not silently fabricate missing measurements or treat imputed values as real observations.

Missing-data handling must be explicit.

Do not label ordinary heart-rate standard deviation as clinical HRV.

---

## 5. Machine Learning

### Objective

Implement a genuine anomaly detection pipeline using Scikit-learn Isolation Forest.

The model must identify unusual patterns across physiological measurements.

### Requirements

The ML pipeline must support:

1. Extracting features from actual physiological recordings.
2. Creating a training dataset.
3. Splitting data into training and evaluation sets.
4. Training the Isolation Forest.
5. Evaluating its behaviour.
6. Saving the trained model.
7. Loading the model into the backend.
8. Performing inference on newly received measurements.

### Dataset requirements

Use actual VitalDB recordings.

Do not generate random physiological values to train or demonstrate the model.

Where possible, split training and evaluation data by patient/case rather than randomly splitting overlapping windows.

This helps prevent data leakage.

### Output

The model should return:

- Anomaly classification.
- Anomaly score.
- Relevant feature values.
- Timestamp or time window.
- Case identity.

The anomaly score is not a probability of illness.

Do not claim that the model diagnoses a medical condition.

### Integration requirement

The trained model must be connected to the health-analysis pipeline.

The expected flow is:

```text
Measurements
     |
     v
Feature Extraction
     |
     v
Trained Isolation Forest
     |
     v
Anomaly Results
     |
     v
Health Analysis
     |
     v
API Response
```

A standalone model training script is insufficient.

---

## 6. Health Analysis

The health-analysis component should combine:

- Latest available measurements.
- Measurement trends.
- Detected anomalies.
- Data quality information.
- Monitoring status.

The health summary should provide structured results that can be consumed by both the frontend and AI assistant.

Each anomaly should include enough information to identify the affected measurement window and understand why it was flagged.

Do not invent medical explanations.

Distinguish between:

- Unusual physiological patterns.
- Poor-quality or missing measurements.
- Insufficient data for analysis.

An anomaly is not automatically a medical emergency.

---

## 7. AI Assistant

The AI assistant is an explanation interface.

It should retrieve structured information from the backend and explain the findings in understandable language.

Existing LangChain implementation may be retained if it works reliably.

Keep the assistant read-only.

Its tools should cover:

1. Monitoring status.
2. Latest physiological measurements.
3. Detected anomalies.

The assistant must:

- Use retrieved measurements and analytical results.
- Mention relevant timestamps.
- Identify the data source.
- Acknowledge missing or unreliable data.
- Avoid inventing measurements.
- Avoid unsupported diagnoses or treatment recommendations.

Do not allow the assistant to independently analyse raw physiological streams.

Do not expand the agent's capabilities until the core analytical pipeline is working.

---

## 8. Dashboard

The dashboard is a required part of the MVP.

Use React and TypeScript.

Use Plotly or Recharts for visualisations.

Organise the dashboard into four main sections.

### A. Overview

Display:

- Overall monitoring status.
- Latest measurements.
- Number of available measurements.
- Number of detected anomalies.
- Data source.
- Data quality status.

### B. Biomarker Monitoring

Display:

- Heart-rate trends.
- Blood-pressure trends.
- SpO₂ trends.
- Temperature trends.
- Respiratory-rate trends where available.

Only display measurements that exist in the selected recording.

### C. Health Intelligence

Display:

- Detected anomalies.
- Affected measurements.
- Relevant timestamps.
- Anomaly scores.
- Feature values associated with flagged windows.
- Data quality warnings.

### D. AI Assistant

Provide a simple conversational interface that allows users to ask questions about the current monitoring session and its analytical findings.

---

## 9. Technical Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Data processing | Pandas, NumPy |
| Machine learning | Scikit-learn |
| Database | SQLite |
| AI assistant | OpenAI API, existing LangChain implementation |
| Frontend | React, TypeScript |
| Visualisation | Plotly or Recharts |

Do not change the stack without a concrete technical reason.

---

## 10. Development Priorities

Work in this order.

### Phase 1 — Audit and Data Integration

- Inspect the existing repository.
- Identify duplicated or unnecessary modules.
- Verify VitalDB replay integration.
- Verify measurement extraction.
- Verify timestamps, units, and case identity.
- Verify database persistence.
- Test the measurement and health-summary endpoints.

**Completion condition:** Actual VitalDB measurements can be retrieved, stored, and returned through the backend API.

### Phase 2 — Complete the ML Pipeline

- Build the actual training-data export pipeline.
- Extract features from real recordings.
- Train Isolation Forest.
- Evaluate using held-out cases.
- Save and load the trained model.
- Integrate inference into health analysis.

**Completion condition:** Incoming measurements can pass through the trained model and produce structured anomaly results.

### Phase 3 — Complete Health Analysis

- Combine measurements, trends, anomalies, and data quality.
- Return structured health-analysis results.
- Ensure the API exposes these results correctly.

**Completion condition:** The backend returns a complete monitoring summary containing actual measurements and ML-generated findings.

### Phase 4 — Complete the Dashboard

- Implement the four dashboard sections.
- Connect frontend components to backend endpoints.
- Visualise actual measurements and anomalies.
- Handle loading, empty, and error states.

**Completion condition:** A user can view the monitoring session and understand its findings through the dashboard.

### Phase 5 — Integrate the AI Assistant

- Connect the existing assistant to the completed health-analysis endpoints.
- Verify its tools.
- Test explanations against actual analytical results.
- Ensure it does not fabricate findings.

**Completion condition:** The assistant can accurately explain the current monitoring session using retrieved data.

### Phase 6 — Final Integration and Testing

Test the complete workflow:

```text
VitalDB
   |
   v
Ingestion
   |
   v
Processing
   |
   v
SQLite
   |
   v
ML Inference
   |
   v
Health Analysis
   |
   +----------+
   |          |
   v          v
Dashboard   AI Assistant
```

Verify that all components work together.

---

## 11. Instructions to Copilot

Before making further changes:

1. Inspect the entire existing repository.
2. Read the existing implementation rather than assuming how it works.
3. Compare the code against this specification.
4. Identify completed, incomplete, broken, and missing components.
5. Identify any implementation that deviates from the intended architecture.
6. Report the findings before making major structural changes.

Do not rewrite working code simply to match the suggested file structure.

Do not introduce new features.

Do not create placeholder data to make the application appear functional.

Do not claim that an integration, model, or endpoint works without testing it.

When implementing a component, test it before moving to the next phase.

Preserve existing working functionality.

If a requirement cannot be implemented with the available data, document the limitation instead of inventing a solution.

**The immediate priority is to establish a working end-to-end data and ML pipeline. Do not start expanding the AI assistant or adding dashboard features until this foundation is verified.**

---

## 12. Definition of Success

The MVP is successful when:

- Actual physiological recordings can be retrieved.
- Measurements are correctly processed and stored.
- A model trained on real recordings can perform inference.
- Unusual patterns are identified and returned through the backend.
- Health analysis combines measurements and ML findings.
- The dashboard visualises the results.
- The AI assistant explains findings using actual analytical evidence.
- The system clearly identifies VitalDB data as surgical-patient recordings, not astronaut telemetry.

The priority is a working, demonstrable system—not a large codebase.