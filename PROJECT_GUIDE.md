# HMS-cr8 Project Guide for LLMs

## 1. Project in one minute

HMS-cr8 is a prototype for physiological monitoring and decision support, framed
as an astronaut-health scenario. It ingests recorded physiological measurements
from VitalDB, stores them, derives time-window features, runs an Isolation Forest
anomaly detector when a trained model is available, and exposes summaries to a
dashboard and a read-only AI explanation agent.

**VitalDB contains surgical-patient recordings, not astronaut or ISS telemetry.**
This is a technical demonstration, not a medical device, clinical model, or
validated spaceflight-health system. Never describe its data as astronaut data,
its anomaly score as illness probability, or its output as a diagnosis.

## 2. Intended workflow

```text
VitalDB virtual replay or recorded VitalDB files
                    |
          ingestion / preprocessing
                    |
        validated measurements in SQLite
                    |
        60-second physiological features
                    |
        Isolation Forest (if available)
                    |
          health-summary API response
             /                 \
   React/Vite dashboard     LangChain agent
                               (read-only tools)
```

The project also has an offline recorded-data workflow: download `.vital` files
and metadata, inspect tracks, extract measurements to Parquet, then prepare
case-separated training data and a model.

## 3. Repository map

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | FastAPI application, CORS, routes, model startup, request logging |
| `backend/app/models.py` | Pydantic request/response and measurement schemas |
| `backend/app/ingestion.py` | VitalDB FHIR replay client and sampled-data parsing |
| `backend/app/database.py` | SQLite schema, measurement persistence, deduplication and queries |
| `backend/app/health_analysis.py` | Per-case feature extraction, anomaly inference and structured summary |
| `backend/app/agent/` | LangChain/OpenAI agent, system prompt and read-only summary tools |
| `backend/app/logging_config.py` | Process logging configuration |
| `backend/run.py` | Development runner for the backend |
| `ml/features.py` | Canonical metric mapping and 60-second feature extraction |
| `ml/anomaly_detection.py` | Isolation Forest wrapper, result schema and joblib save/load |
| `ml/train.py` | CSV-based training with case-held-out evaluation |
| `ml/pipeline.py` | Parquet-based preparation, case-separated train/validation/test splits and training |
| `ml/model/` | Serialized model artifact |
| `scripts/vitaldb_downloader.py` | Download/resume VitalDB metadata and packed recordings |
| `scripts/vitaldb_processor.py` | Prepare metadata, inventory tracks and extract measurement Parquet |
| `frontend/src/` | React/Vite dashboard source (currently has unresolved merge conflicts; see below) |
| `frontend/AsrotnautDashboard..jsx`, `frontend/astronaut_telemetry.json` | Separate astronaut-themed prototype/sample data; not a verified live feed |
| `tests/` | Backend parsing/store and ML feature/model/pipeline tests |
| `.github/workflows/tests.yml` | Python 3.12 CI test job |
| `README.md` | Current backend/frontend startup and data workflow instructions |
| `SPECS.md`, `REALIGNMENT.md` | Product goals and engineering constraints; not proof that every goal is implemented |

Generated datasets and local runtime data belong under `data/`; ignore rules
exclude downloaded/processed data, Python artifacts, databases and frontend
build/dependency directories.

## 4. Backend behavior and API

The FastAPI application is `backend.app.main:app` and listens on port 8000 in
the documented local setup. It creates a SQLite store at
`data/hms.sqlite3` relative to the process working directory. Measurements are
deduplicated by `(case_id, recorded_at, metric, source)`.

| Route | Behavior |
|---|---|
| `GET /health` | Reports process status, data source, and whether a model loaded |
| `GET /cases` | Lists case IDs already stored |
| `GET /measurements?case_id=...&limit=...` | Returns recent measurements; limit defaults to 100 and is capped at 1000 |
| `GET /health-summary?case_id=...` | Returns status, source, latest measurements, active anomalies, feature-window count and data-quality fields |
| `POST /ingest/vitaldb/replay` | Fetches and stores a VitalDB virtual replay window |
| `POST /assistant/explain?case_id=...` | Builds the selected summary and asks the assistant to explain it |

The replay request accepts `location`, `track_code`, `window_seconds`, and
optional `at`. It parses FHIR `Observation`/`Bundle` `valueSampledData`, extracts
case identity, applies the sampled-data factor/origin, and skips `E` or
non-numeric sample tokens.

Feature extraction maps supported VitalDB signal names to heart rate, blood
pressure, SpO2, temperature, and respiratory-rate fields. The model uses
60-second windows. Health summaries group windows by case, but an omitted
`case_id` still requests an aggregate summary across the stored set; be
deliberate about case selection and never imply that different cases are one
person.

The replay endpoint's default track is `SNUADC/ECG_II`; the ML feature extractor
expects recognized vital-sign metric names, not an arbitrary ECG waveform.
Choose and verify replay tracks appropriate to the desired feature and preserve
the actual metric name and unit.

## 5. Machine learning and interpretation

The detector is an unsupervised Scikit-learn `IsolationForest` in a pipeline
with median imputation. It returns a flag, decision score, case, time window
and feature values. The score is a model decision score, **not** a probability
or clinical risk estimate.

There are two training entry points:

- `python -m ml.train <measurements.csv> <model.joblib>` uses a CSV, holds out
  cases for an evaluation report, and writes the model.
- `python -m ml.pipeline <measurements.parquet> --output-dir data/ml
  --model-path ml/model/isolation_forest.joblib` builds windows, chooses
  sufficiently covered features, excludes incomplete windows, splits by case
  into train/validation/test, trains and writes split files and a summary.

The model artifact currently present in `ml/model/` is loadable by the backend
if it is compatible, but the repository does not establish its training-data
provenance or clinical validity. Do not claim validation based only on the
artifact's presence. The tests use small constructed datasets to test code
behavior; those are not medical or model-quality evaluations.

## 6. Assistant and safety boundaries

The assistant is created per request using `OPENAI_API_KEY`; `OPENAI_MODEL`
defaults to `gpt-4o-mini`. It receives a health summary and has read-only tools
for monitoring status, latest measurements, and detected anomalies. Missing
API credentials produce an unavailable response from the API rather than a
working assistant.

The system prompt requires evidence-based explanations, explicit mention that
VitalDB is surgical-patient data, and no diagnosis, fabricated recommendations,
or interpretation of anomaly scores as illness probabilities. Keep ML
classification in the detector; do not ask the LLM to infer anomalies from raw
streams or replace missing evidence.

## 7. Frontend: current audit findings

The intended React/Vite dashboard variant reads `VITE_API_URL` (default
`http://localhost:8000`) and requests `/health`, `/cases`, `/health-summary`,
`/measurements`, and `/assistant/explain`. Its visible sections include
operational/model status, analysis status, measurement count, latest
measurements, anomalies, signal coverage, and an assistant form. It offers a
manual refresh; it does not itself constitute proof of continuous ingestion.

**The frontend is currently not a clean, buildable source tree.** Unresolved
Git conflict markers occur in `frontend/index.html`, `frontend/package.json`,
`frontend/package-lock.json`, `frontend/vite.config.js`,
`frontend/src/App.jsx`, `frontend/src/main.jsx`, and
`frontend/src/styles.css`. The alternatives mix a synthetic astronaut mission
dashboard with an API-backed HMS-cr8 dashboard, and include different React
and Vite versions. The current index also contains unresolved merge entries.
Do not run package installation or choose a side implicitly; determine the
intended UI/dependency versions with the user before resolving these conflicts.

The separate astronaut prototype and its JSON contain illustrative/synthetic
telemetry and astronaut identity. They are not wired into the verified VitalDB
backend path. Never present that content as real patient or astronaut readings.

The written specs mention TypeScript and charting libraries, while the actual
frontend files are JSX and do not establish that charting is implemented.
Treat specs and `REALIGNMENT.md` as requirements/intent; describe actual
behavior from the code and tests.

## 8. Local development and validation

Backend setup from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Frontend setup is documented as:

```powershell
Set-Location frontend
npm install
npm run dev
```

That frontend setup is blocked until the merge conflicts are resolved. Use
`frontend/.env.example` as the template for `VITE_API_URL`; configure backend
`CORS_ORIGINS` if the UI and API have different origins. The assistant also
requires `OPENAI_API_KEY`. `HMS_MODEL_PATH` overrides the default model path.
`LOG_LEVEL=DEBUG` enables debug logging.

Tests and CI:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

In the audit that produced this guide, `python -m pytest -q` could not start
because `pytest` is not installed in the active Python environment. No test
result should be inferred from that attempt. Once the frontend conflicts are
resolved, validate its dependency lockfile and run `npm run build`.

VitalDB recorded-data acquisition and preparation are documented in `README.md`.
Those commands access external datasets and can download substantial data;
use a small case limit for a first check and do not commit raw recordings.

## 9. Priority issues and implementation caveats

1. **Resolve frontend merge conflicts deliberately.** Confirm which design and
   dependency versions are intended, then reconcile the package manifest and
   lockfile together. Avoid losing either the mock design intent or API-backed
   features without user direction.
2. **Verify the live VitalDB integration.** Code presence is not integration
   evidence. Check requested tracks, timestamps, units, case identity, API
   persistence, and read-back against a real response.
3. **Make the demo data boundary unmistakable.** Label VitalDB as surgical
   patient data and keep mock astronaut telemetry separate or remove it only
   when explicitly in scope.
4. **Validate model provenance and performance.** Record dataset/version,
   selected features, case split, evaluation method, and limitations; do not
   imply clinical or astronaut validation.
5. **Run targeted tests and builds after environment setup.** The current
   Python test attempt was blocked by missing pytest; the frontend build is
   blocked by unresolved conflict markers.

## 10. Instructions for an LLM working in this repository

Use the following prompt as project-specific working context:

> You are contributing to HMS-cr8, a prototype that monitors recorded
> VitalDB surgical-patient measurements in an astronaut-mission scenario.
> VitalDB is not astronaut telemetry, and this software is not clinically or
> spaceflight validated. Read `PROJECT_GUIDE.md`, `README.md`, and the relevant
> implementation/tests before changing code. Treat source and tests as evidence
> of current behavior; treat `SPECS.md` and `REALIGNMENT.md` as desired
> requirements when they differ. Make the smallest complete change, preserve
> case identity, timestamps, units, and source, do not fabricate measurements,
> and do not turn anomaly scores into diagnoses or illness probabilities.
> The frontend currently has unresolved Git merge conflicts and staged
> unmerged entries: do not install dependencies, choose a conflict side, stage,
> unstage, or otherwise alter the merge state unless the user explicitly asks.
> Add focused tests for changed behavior and report commands run and their
> actual results.

### Reusable task prompt

Copy and fill in for a focused implementation request:

```text
Task:
<one specific outcome>

Context:
<user-visible problem and why it matters>

Scope:
<files/components allowed to change; explicitly list exclusions>

Requirements:
- Preserve source, case identity, timestamps, units, and missing-data meaning.
- Follow existing Python/FastAPI, SQLite, React/Vite, and ML patterns.
- Keep anomaly detection separate from LLM explanations.
- Do not claim clinical or astronaut validation.

Before editing:
- Inspect the relevant implementation, callers, tests, and current Git status.
- Report any unresolved merge conflict or staged change that blocks safe work.
- Ask before making a material product/dependency decision.

Validation:
- Add only focused tests for introduced/fixed behavior.
- Run the smallest relevant test/build command.
- If blocked by missing tools or conflicts, report the exact blocker; do not
  claim success or silently work around it.

Completion response:
- Summarize changed files and behavior.
- List validation commands and pass/fail/block status.
- Call out remaining risks or follow-up decisions.
```

### Useful task-specific prompts

**Backend or ingestion**

> Trace this request from the FastAPI route through VitalDB parsing, validation,
> SQLite, and the response. Identify the exact expected payload and metric
> names before changing it. Preserve timestamps, units, case IDs, source, and
> duplicate handling. Add focused tests for valid, malformed, and missing data.

**ML**

> Trace the feature columns from VitalDB track names through window extraction,
> training, model serialization, backend loading, and summary output. Keep
> windows from one case in one split. Report dataset provenance and evaluation
> limitations; a successful fit is not clinical validation. Do not use the LLM
> as a classifier.

**Frontend**

> First inspect Git status and all frontend conflict markers. Do not resolve
> them or install dependencies without explicit direction. Once the merge
> choice is authorized, align the manifest and lockfile, connect UI state to
> the documented API contract, preserve loading/error/empty states, and clearly
> label the source as VitalDB surgical-patient data.

**Audit or review**

> Audit the requested scope against implementation, tests, and documented
> requirements. Separate confirmed behavior, gaps, and assumptions. Prioritize
> actionable findings with file paths and evidence. Do not edit files unless
> asked, and do not call mock data or an artifact a validated system.
