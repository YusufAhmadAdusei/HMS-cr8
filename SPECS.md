# HMS-cr8 — Hackathon MVP Specification

## 1. Project Overview

**HMS-cr8 (Health Monitoring System)** is a health-monitoring and decision-support application designed for astronauts aboard the International Space Station (ISS).

The system monitors physiological measurements, identifies unusual patterns using machine learning, and uses an AI assistant to explain findings and provide relevant guidance.

### Core objectives

1. Collect actual physiological measurements.
2. Analyse measurements and detect unusual patterns using a trained ML model.
3. Visualise health data and detected anomalies.
4. Use an AI assistant to investigate findings and explain them.

The goal is to build a functional demonstration, not a production-grade medical system.

---

## 2. MVP Features

| Feature | Description |
|---|---|
| Data ingestion | Retrieve real physiological data from VitalDB |
| Vital monitoring | Display heart rate, blood pressure, SpO₂, temperature and respiratory rate where available |
| ML anomaly detection | Identify unusual patterns across multiple biomarkers |
| Health dashboard | Display measurements, trends and anomalies |
| AI assistant | Explain detected anomalies using available data |
| Alerts | Highlight measurements or patterns that require attention |

### Data source

Use the VitalDB API and its virtual real-time replay functionality.

VitalDB contains recorded surgical-patient data, not astronaut data. It will serve as our initial real-data source for demonstrating the system.

The dashboard must clearly identify the source. Never present these measurements as actual ISS telemetry.

---

## 3. Simplified Architecture

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

### How it works

1. The backend retrieves physiological measurements from VitalDB.
2. Measurements are cleaned, validated and stored.
3. The ML model analyses measurement windows and identifies unusual patterns.
4. The backend combines measurements and ML results into a health summary.
5. The dashboard displays the data and anomalies.
6. The AI assistant retrieves the health summary and explains relevant findings.

---

## 4. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python + FastAPI |
| Data processing | Pandas + NumPy |
| Machine learning | Scikit-learn |
| Database | SQLite initially |
| AI assistant | OpenAI API |
| Frontend | React + TypeScript |
| Charts | Plotly or Recharts |

Keep everything in one backend application.

Do not introduce microservices, Redis, Kafka, Celery or other infrastructure that does not directly help us demonstrate the project.

---

## 5. Machine Learning

The ML component should be a genuine trained model, not an LLM pretending to perform anomaly detection.

### Initial approach

Use **Isolation Forest** for multivariate anomaly detection.

The model will analyse physiological measurements over time rather than classify individual readings in isolation.

### Input features

Start with features such as:

- Average heart rate
- Heart-rate variability
- Average systolic blood pressure
- Average diastolic blood pressure
- Average SpO₂
- Average body temperature
- Average respiratory rate
- Rate of change of selected measurements

Use time windows to extract these features.

### Model output

The model should return:

- Whether an unusual pattern was detected.
- An anomaly score.
- The measurement window associated with the anomaly.
- Relevant features for further investigation.

The anomaly score is not a probability of illness.

### Training requirements

- Train using actual physiological recordings.
- Do not use randomly generated values as training data.
- Keep training and inference separate.
- Evaluate using held-out subjects or recordings.
- Document the dataset and model limitations.

Remember: surgical-patient data is not representative of healthy astronauts. Our model demonstrates the analytical approach; it is not clinically validated for spaceflight.

---

## 6. Health Analysis and AI Assistant

The backend should produce a simple structured health summary containing:

- Latest measurements.
- Detected anomalies.
- Recent trends.
- Data-quality information.
- Relevant timestamps.

The AI assistant uses this information to investigate health observations.

### Example interaction

**Astronaut:** Why is my health status showing attention?

**Assistant:**
- Retrieves the current health summary.
- Identifies the detected anomaly.
- Examines recent trends.
- Explains which measurements contributed to the alert.
- Provides relevant guidance when an approved source is available.

### Important constraints

The AI assistant must not:

- Diagnose medical conditions.
- Invent medical recommendations.
- Interpret an anomaly score as a probability of illness.
- Make unsupported claims about the astronaut's health.

It should explain evidence, not replace medical professionals.

---

## 7. Dashboard

Keep the interface focused on four main sections.

### A. Overview
- Current vital signs.
- Overall monitoring status.
- Active alerts.
- Last measurement timestamp.

### B. Biomarker Monitoring
- Interactive time-series charts.
- Individual biomarker trends.
- Measurement timestamps and units.

### C. Health Intelligence
- Detected anomalies.
- Anomaly scores.
- Historical trends.
- Relevant measurements associated with each anomaly.

### D. AI Assistant
- Ask questions about health observations.
- Investigate anomalies.
- Explain trends and relationships.

The data source must remain visible throughout the demonstration.

---

## 8. Simple Project Structure

```text
hms-cr8/
│
├── backend/
│   ├── main.py
│   ├── ingestion.py
│   ├── processing.py
│   ├── database.py
│   ├── anomaly_detection.py
│   ├── health_analysis.py
│   └── ai_assistant.py
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── charts/
│       └── services/
│
├── ml/
│   ├── train.py
│   ├── evaluate.py
│   └── model/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── requirements.txt
└── README.md
```

This structure is intentionally small. We can reorganise it if the implementation grows.

---

## 9. Development Priorities

Build in this order.

### Phase 1 — Working data pipeline
- Connect to VitalDB.
- Retrieve actual recorded measurements.
- Process and store measurements.
- Display continuously updating charts.

**Milestone:** Real measurements appear on the dashboard.

### Phase 2 — Machine learning
- Prepare the training dataset.
- Extract physiological features.
- Train Isolation Forest.
- Evaluate the model.
- Connect model inference to incoming measurements.
- Display detected anomalies.

**Milestone:** The system can identify unusual patterns in the data.

### Phase 3 — AI assistant
- Connect the OpenAI API.
- Give the assistant access to structured health summaries and anomaly reports.
- Implement anomaly investigation and explanations.

**Milestone:** The assistant can explain why an anomaly was detected using actual system data.

### Phase 4 — Final integration
- Improve dashboard presentation.
- Add correlation visualisations.
- Improve alerts and data-quality indicators.
- Test the complete workflow.
- Prepare the demonstration.

---

## 10. Rules for the Coding Agent

1. Prioritise a working application over complex architecture.
2. Do not fabricate physiological measurements for the demonstration.
3. Preserve measurement timestamps, units, subject identity and data source.
4. Never mix measurements from different subjects.
5. Never present VitalDB data as actual astronaut telemetry.
6. Train and evaluate a real ML model using actual recordings.
7. Keep ML inference separate from the AI assistant.
8. Do not let the LLM independently diagnose or classify medical conditions.
9. Do not introduce unnecessary infrastructure or dependencies.
10. Implement and test each phase before moving to the next.

## Definition of Success

A working demonstration in which:

- Real recorded physiological measurements are retrieved.
- Measurements appear on an interactive dashboard.
- A trained ML model identifies unusual physiological patterns.
- The system highlights those patterns.
- An AI assistant investigates and explains the findings using actual system data.

**Build the complete working pipeline first. Add sophistication only when the core system works.**