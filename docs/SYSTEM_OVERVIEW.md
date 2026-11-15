# HMS-cr8 System Overview

## 1. Purpose and scope

HMS-cr8 is a prototype for monitoring physiological signals in an astronaut mission scenario. Its intended problem is helping an astronaut and mission health team review changing measurements, notice unusual patterns, and understand what data contributed to an alert when communication, time, and access to ground-based support may be constrained.

The current application demonstrates a data pipeline and dashboard. It is **not an operational spaceflight medical system**, a diagnostic device, or a validated astronaut monitoring model. The data source currently wired into the application is VitalDB, a collection of surgical-patient recordings. Those recordings are useful for exercising the software pipeline, but they are not astronaut telemetry and must not be represented as such.

The product direction should stay mission-specific: support crew health monitoring and review during spaceflight. Avoid presenting generic disease diagnosis, treatment, or hospital workflows as product capabilities. Mission-specific thresholds, baselines, alert rules, and procedures need to come from qualified spaceflight medical and human-factors experts; the codebase does not currently provide them.

## 2. What the system does today

The current prototype can:

- Request short physiological replay windows from the VitalDB replay API.
- Parse supported FHIR Observation/SampledData responses into timestamped measurements.
- Apply clearly named demo transformations for tachycardia, hypoxia, and hypotension scenarios.
- Store measurements in a local SQLite database, keyed by case, metric, timestamp, and source.
- Calculate time-window features and, when a compatible trained model is installed, run an Isolation Forest anomaly detector.
- Return a health summary containing latest readings, data coverage, feature-window count, status, and detected unusual windows.
- Display those results in a React dashboard with a measurement feed, trend chart, case selector, replay controls, model status, and assistant.
- Offer 2D and 3D illustrative anatomy views with callouts for supported measurements.
- Let an LLM assistant inspect the summary through read-only tools and explain the evidence it finds.

The application does not currently connect to a wearable or spacecraft sensor, receive real-time astronaut telemetry, have mission-qualified alert thresholds, calculate a validated health score, diagnose a condition, or provide medically approved treatment recommendations.

## 3. System architecture

```text
VitalDB replay API                 (prototype data source)
        |
        v
FastAPI ingestion endpoint
  - parse and validate samples
  - optionally apply labeled demo scenario
        |
        v
SQLite measurement store
        |
        +------------------------------+
        |                              |
        v                              v
Feature extraction                 Summary API
60-second windows                  latest values, coverage,
        |                           anomaly windows, status
        v                              |
Isolation Forest (optional)            +-----------> React dashboard
        |                                           - cards and trends
        +-------------------> summary              - body illustration
                                                    - signal feed
                                                    - assistant UI
                                                          |
                                                          v
                                             FastAPI assistant endpoint
                                                          |
                                                          v
                                                   OpenAI model
                                             with summary-only tools
```

This is one FastAPI application, not a set of microservices. The `ml/` package contains reusable feature, training, evaluation, and inference code, while the backend imports its inference implementation directly.

## 4. Measurement lifecycle

### 4.1 Acquisition

The dashboard calls `POST /ingest/vitaldb/replay` for each requested track. The current UI requests ten-second windows from VitalDB location `OR1`, with tracks for heart rate, systolic and diastolic non-invasive blood pressure, pulse oximetry SpO₂, body temperature, and respiratory rate. Automatic replay polling defaults to every five seconds and can be changed to ten seconds in the dashboard. Each poll still requests a ten-second recorded window. This is replay of recorded cases, not a live crew connection; faster polling advances the replay more quickly and makes more source requests.

The backend reads FHIR Observation resources and expands SampledData tokens into individual measurements. It preserves the track code, unit, case identity, source label (`VitalDB virtual replay`), and timestamp calculated from the observation start and sample period. Non-numeric tokens are skipped. Missing tracks can fail independently while the other requested tracks succeed.

### 4.2 Demo transformations

The replay scenario selector supports `normal`, `tachycardia`, `hypoxia`, and `hypotension`. The non-normal choices alter selected replayed values to exercise the analysis and display path. Changed values are stored with a scenario-specific source label. These are software demo inputs, not observed patient or astronaut measurements, and should be visibly disclosed whenever used.

### 4.3 Persistence and retrieval

`MeasurementStore` writes to SQLite at `data/hms.sqlite3` by default. A measurement carries:

| Field | Meaning |
|---|---|
| `case_id` | Source case identity; used to keep recordings separate |
| `recorded_at` | Time associated with the sample |
| `metric` | Source track/metric code |
| `value` | Numeric measurement |
| `unit` | Unit supplied by the source, when present |
| `source` | Source or labeled demo scenario |

Duplicate records are ignored by the store. `GET /measurements` returns recent records (optionally filtered by case); `GET /cases` returns known case IDs. The dashboard can select a case or request the aggregate view. For a safety-oriented operational system, aggregating crew members or sessions without an explicit identity boundary would not be acceptable; the prototype's case selection is only a basic separation mechanism.

### 4.4 Feature extraction and anomaly detection

`ml/features.py` groups measurements into 60-second windows and computes available features: average heart rate, heart-rate standard deviation, average systolic/diastolic blood pressure, average SpO₂, average temperature, average respiratory rate, and within-window heart-rate and SpO₂ change. Heart-rate standard deviation is not clinical heart-rate variability (HRV).

The Isolation Forest in `ml/anomaly_detection.py` labels unusual feature windows and returns a decision score and the input feature values. Its score is not a probability of illness or a severity scale. A trained model is loaded from `ml/model/isolation_forest.joblib` unless `HMS_MODEL_PATH` points elsewhere. If no model file is available, the service reports that the model is unavailable and cannot produce model-based anomaly results.

There are two training entry points: `ml.train` trains from a CSV with case-separated evaluation, and `ml.pipeline` prepares Parquet data, builds case-separated train/validation/test splits, and trains the selected available features. The available training code does not by itself demonstrate astronaut validation. Any model's training data, version, evaluation, feature coverage, and intended population need to accompany operational use.

### 4.5 Health summary and status

`GET /health-summary` loads the requested case's stored measurements, calculates the latest value per metric, extracts case-separated feature windows, and asks the detector to score them if a model is loaded. It returns:

- Monitoring `status` and `analysis_status`.
- Data source and summary generation timestamp.
- Latest measurement per case and metric.
- Detected anomaly windows, their scores, and feature values.
- Window count and data-quality counts, including missing expected metrics.

The current `monitoring` status means the summary path ran without an active anomaly being returned by a loaded detector; it is not a medically cleared status. `attention` means the model returned an anomalous window. Neither status is a diagnosis or a mission go/no-go decision.

The dashboard's signal coverage display shows the count of configured signal types with a reading for the focused case. It is not output by the trained model and does not represent health or readiness.

### 4.6 Dashboard and anatomy illustration

The React/Vite frontend reads the backend endpoints and renders the data returned by them. The trend chart uses recorded heart-rate measurements and timestamps; it does not interpolate missing samples. The cards and table display source values and their units where available.

The 2D image and local GLB model are illustrative assets. The anatomy panel overlays callouts using explicit screen/model coordinates in `frontend/src/anatomyData.jsx`. Those coordinates indicate approximate body regions for visual orientation only. The callout line does not establish that a sensor measured the illustrated organ or that the value is a localized organ measurement. For example, a heart-rate point may be placed near the chest as a visual cue, not as an anatomical sensor localization. The model is not personalized to a crew member and does not visualize internal physiology.

The 3D model attribution and licenses are recorded under `frontend/public/models/`. Keep those notices with the asset and include required attribution in redistributed product materials.

### 4.7 Assistant

`POST /assistant/explain` builds the current summary and gives it to a LangChain agent. The agent has read-only tools for monitoring status, latest measurements, and detected anomalies. The OpenAI API key is read from `OPENAI_API_KEY`; `OPENAI_MODEL` can override the default model. Without a configured key, the endpoint returns an unavailable response.

The assistant is a language model explanation layer, not the anomaly detector. Its system prompt instructs it to use the supplied evidence, avoid diagnosis, not invent recommendations, and disclose that VitalDB data is not astronaut telemetry. Model output can still be wrong; it should not be used for autonomous medical or mission decisions.

## 5. Backend API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | API status, declared source, model availability |
| `GET /cases` | Stored case IDs |
| `GET /measurements?case_id=…&limit=…` | Recent measurements, up to the configured limit |
| `GET /health-summary?case_id=…` | Latest readings, data quality, and model findings |
| `POST /ingest/vitaldb/replay` | Retrieve and store a replay window |
| `POST /assistant/explain?case_id=…` | Ask the evidence-grounded assistant about a summary |

See request and response schemas in `backend/app/models.py`; the FastAPI interactive API reference is available at `/docs` when the service is running.

## 6. Dashboard navigation and element guide

The dashboard is a single scrollable overview. Start at the top; on smaller screens, the same cards stack into a vertical page. Data refreshes after replay ingestion and when the refresh button is used. If a request fails, an error notice appears near the top of the page.

### Header

- **HMS-cr8 / Health signals** — brand link; returns to the top of the dashboard.
- **Replay running / Replay paused** — indicates whether the browser is scheduling replay requests. It reflects the UI polling switch, not a live astronaut/device telemetry connection.
- **VitalDB replay · not crew telemetry** — identifies the prototype source and makes the data limitation visible in the header.
- **Refresh button (↻)** — reloads health, cases, summary, and recent measurement data from the API. It does not request a new VitalDB window.
- **Ingest window** — requests the next ten-second replay window for each configured metric. While running, the button reads “Collecting…”. A result notice reports sample and track counts, including unavailable tracks.
- **Replay cadence** — set automatic requests to every five or ten seconds. Each request still asks for a ten-second source window, so the shorter cadence advances the recorded replay faster and increases request frequency; it does not make the source live.
- **Pause / Resume** — stops or restarts automatic replay polling. Use **Ingest window** for a one-off request while paused.

### Monitoring workspace controls

- **Mission signals overview** — crew-monitoring presentation over a replay environment. The subheading states that no live crew link is connected.
- **Replay case selector** — choose a stored case ID to filter the selected case's summary, metric cards, body callouts, and trend. “All cases” asks the summary/feed for all cases; the central/left latest-reading cards choose the most recently represented case to avoid mixing different cases into one body diagram. For careful review, select a specific case.
- **Replay scenario** — choose `Recorded values` or a labeled demo transformation (`tachycardia`, `hypoxia`, `hypotension`). The chosen scenario is used on the next ingest request. It does not automatically alter already stored measurements. A demo scenario modifies replayed samples and is not real telemetry.
- **Error / success notices** — API and ingestion errors are displayed here; a successful ingestion notice describes how many samples/tracks were received and names the scenario.

### Main overview cards

The overview is arranged as three visual regions: left-side signal cards, a central anatomy panel, and right-side analysis/assistant cards.

- **Heart rate — Latest reading:** shows the latest heart-rate value and timestamp available for the focused case. The small sparkline uses up to the last 28 recorded heart-rate samples. If there are no readings, it shows an awaiting/empty state.
- **Health metrics — Latest by signal:** lists the latest available value for each metric in the focused case, including source metric codes mapped to readable names. Select a row to jump to that signal's chart. Units are shown where the source provides them. The “available” count counts metrics, not sample quality or clinical normality.
- **Telemetry availability / Signal coverage:** shows how many of six configured signal types have a latest measurement for the focused case. Each row says whether that reading is available and displays its value or “No reading.” The ring is a coverage fraction only; it does not use heart-rate thresholds, model anomaly count, or imply health, normality, or readiness.
- **Signals at a glance — anatomy panel:** switches between **2D** and **3D**. Only callouts for metrics present in the focused case are displayed. Each callout shows the latest corresponding value, source unit when available, and timestamp. Select a callout to jump to that signal's chart. The line endpoints are illustrative coordinates, not a representation of sensor placement or internal physiology.
  - In **2D**, the supplied full-body illustration fills the panel and SVG connector lines point to approximate body regions.
  - In **3D**, the locally hosted model is rendered in the browser. Drag to rotate and use a wheel/pinch gesture to zoom. The view controls disable panning. If WebGL/model loading fails, use the “Show 2D view” fallback. The model preview appears while the 3D asset loads.
- **Anomaly model output — Pattern analysis:** shows whether the model is available, number of flagged model windows, and feature-window count. Up to three detected windows are listed with case, time, and raw detector score. Select a window to focus its case and move the trend review cursor to the nearest available heart-rate sample. Matching windows appear as shaded intervals on the chart when their measurements are in the visible range. “No anomaly flagged” only means none were returned by the current pipeline; it is not a medical all-clear. “Model unavailable” means model-based anomaly detection is unavailable in this backend process.
- **Ask the monitoring assistant:** enter a question (up to 2,000 characters) and choose **Ask**. The backend gives the assistant the selected summary and read-only tools to inspect its status, latest values, and detected anomaly windows. The answer appears in the card. It requires `OPENAI_API_KEY`; errors appear in the page notice. Do not use the response for diagnosis or mission decisions.

### Trend and measurement history

- **Signal trend:** spans the lower chart row and plots the selected signal's recorded values against timestamps for the focused case. Select a metric, choose a 1-, 5-, or 15-minute window or all loaded data, hover for a value/time tooltip, or click a point to move the review cursor. Use arrow keys when the chart is focused to inspect points. Shaded intervals mark model-flagged windows when they overlap the loaded points.
- **Review playback controls:** use **Play review**, **Pause review**, and the range slider to browse samples already loaded in the selected case; choose 0.5×, 1×, 2×, or 4× review speed. **Latest** returns to the newest loaded point. This is client-side browsing of stored replay samples; it does not control VitalDB's source speed or add new data. The chart can only show the recent rows returned by the API (up to 100 for this dashboard) and does not fill gaps or interpolate values.
- **Latest measurements — Signal feed:** a table of up to twelve latest measurement rows with signal, value, case, recorded time, and source. This feed helps inspect provenance and compare cases; when “All cases” is selected, rows can belong to more than one case. The source column distinguishes VitalDB replay and labeled scenario-modified data.
- **Footer:** repeats the prototype/telemetry limitation and shows the summary generation time when available. “Summary” is a calculation timestamp, not a guarantee that a sensor measurement was taken at that moment.

### Suggested review path

1. Confirm the source label and whether replay is running or paused.
2. Select a specific case before reviewing its anatomy callouts, readings, and trend.
3. Check metric availability and timestamps first; distinguish stale/missing data from a normal value.
4. Review model availability and any listed anomaly windows. Treat a score as a detector output, not a probability or severity.
5. If needed, ask the assistant to explain a specific displayed observation, then verify its answer against the readings and source.
6. Use a demo scenario only when intentionally demonstrating the alert path, and identify its values as simulated transformations of replay data.

## 7. Repository map

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | FastAPI setup, configuration, routes, and dependency wiring |
| `backend/app/ingestion.py` | VitalDB replay client and FHIR SampledData parsing |
| `backend/app/models.py` | Validated request and measurement schemas |
| `backend/app/database.py` | SQLite schema, insertion, and queries |
| `backend/app/simulation.py` | Labeled demo scenario transformations |
| `backend/app/health_analysis.py` | Summary, feature windows, status, and anomaly response |
| `backend/app/agent/` | LLM agent, prompt, and summary inspection tools |
| `ml/features.py` | 60-second physiological feature extraction |
| `ml/anomaly_detection.py` | Isolation Forest wrapper, serialization, inference |
| `ml/train.py`, `ml/pipeline.py` | Model training and dataset preparation |
| `frontend/src/App.jsx` | Dashboard data fetching, UI state, charts, and cards |
| `frontend/src/AnatomyPanel.jsx`, `Anatomy3DViewer.jsx` | 2D/3D anatomy illustration and view toggle |
| `frontend/src/anatomyData.jsx` | Display labels and illustrative callout positions |
| `frontend/src/styles.css` | Dashboard presentation and responsive styling |
| `frontend/public/assets/`, `frontend/public/models/` | Illustrations and attributed 3D model assets |
| `scripts/` | VitalDB bulk acquisition and data processing utilities |
| `docs/` | Product, engineering, and system documentation |

## 8. Running the prototype locally

From the repository root, install and start the backend:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for the API. Set `VITE_API_URL` in `frontend/.env` to use another backend. Configure backend `CORS_ORIGINS` to include the frontend origin if they are hosted separately. To enable assistant responses, configure `OPENAI_API_KEY` for the backend. To enable anomaly inference, provide a trained model at the default path or set `HMS_MODEL_PATH`.

The dashboard starts replaying automatically by default with a five-second polling cadence. Change it to ten seconds or pause replay; use **Ingest window** to request a window manually. The review playback control only scrubs data already loaded in the browser. Choose a named demo scenario only when intentionally demonstrating the alert pathway.

## 9. Astronaut-specific changes needed before operational use

The prototype should evolve around crew, mission phase, and data provenance. These are requirements to investigate, not capabilities already implemented:

1. **Astronaut data sources:** Replace or supplement VitalDB replay with approved wearable/vehicle telemetry interfaces. Define authentication, device identity, time synchronization, sampling, buffering, disconnection behavior, and data ownership.
2. **Mission context:** Define crew-member and mission/session identity, mission elapsed time, EVA/exercise/sleep context, and how context changes interpretation. Keep each crew member's measurements strictly separated.
3. **Spaceflight baselines and validation:** Establish appropriate per-person baselines, signal-quality rules, approved thresholds, and validation with representative spaceflight data and qualified medical review. Do not carry over surgical-patient model assumptions as astronaut norms.
4. **Alert design and response:** Specify urgency levels, confirmation/acknowledgment, persistence, escalation, offline behavior, crew privacy, and approved response procedures. The present binary anomaly label is not an alert policy.
5. **Data quality and uncertainty:** Surface stale or missing telemetry, sensor disconnects, unit conversions, artifact/noise flags, clock quality, and model/data limitations. A missing measurement must not look normal.
6. **Human factors:** Evaluate readability, color/shape redundancy, glove/touch interaction, workload, accessibility, localization, and use in the actual spacecraft display environment.
7. **Security and resilience:** Define access controls, encryption, auditability, retention, update strategy, fault recovery, offline operation, and handling of sensitive crew health data.
8. **Assistant constraints:** Decide whether an external LLM service is acceptable for sensitive health data and mission connectivity. If retained, enforce approved data boundaries, source citations, reliable refusal behavior, and human review; otherwise use a local or rules-based explanation component.
9. **Anatomy visualization:** Keep the body view explicitly illustrative until a medically reviewed, correctly licensed visualization and validated mapping are available. Do not imply that a displayed metric was sensed at the callout location.
10. **Deployment and persistence:** Confirm the production host's disk persistence and backup behavior. SQLite on an ephemeral deployment filesystem may lose records on restart or redeploy; choose and validate a persistence strategy before relying on stored history.

Any operational or clinical/flight decision use requires a separate safety, security, human-factors, and medical validation process beyond this software prototype.

## 10. Known limitations and interpretation rules

- VitalDB replay is the source currently integrated; it is not ISS or astronaut telemetry.
- Demo scenarios transform replay values and are not observations.
- A successful API response or “monitoring” status does not mean a person is medically healthy or fit for duty.
- An Isolation Forest anomaly is an unusual pattern relative to its training data, not an illness probability, diagnosis, or severity estimate.
- A model being present on disk does not demonstrate that it is trained, evaluated, or appropriate for astronauts.
- The assistant summarizes a supplied data snapshot; it does not perform independent clinical validation.
- Anatomy callouts are decorative orientation aids, not sensor location or organ-function measurements.
- The signal coverage fraction describes only the presence of configured measurement types; it must not be treated as a health score.
- No real crew identity, spacecraft telemetry, mission response workflow, or flight qualification is implemented.

## 11. Related documents

- `README.md` — setup, data-source details, and training commands.
- `SPECS.md` and `docs/SPECS.md` — initial product and hackathon requirements.
- `REALIGNMENT.md` — engineering alignment and implementation constraints.
- `frontend/public/models/ATTRIBUTION.md` and `LICENSE-MODELS.md` — 3D asset attribution and license details.
