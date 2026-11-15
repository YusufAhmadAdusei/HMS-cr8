# HMS-cr8

For the full system description, data flow, current limitations, and astronaut-specific requirements, see [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md).

## Backend

The backend is a single FastAPI application under `backend/app/`. It ingests
VitalDB virtual replay samples, stores validated measurements in SQLite,
extracts time-window features, and exposes the anomaly and AI-agent boundaries.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Backend logs are written to the process output. Set `LOG_LEVEL=DEBUG` for
feature-level diagnostics; the default level is `INFO`:

```powershell
$env:LOG_LEVEL = "DEBUG"
python backend\run.py
```

Request logs include the HTTP method, route, status code, and duration.
VitalDB logs include the requested location and track, response status, and
measurement counts. Secrets and assistant message contents are not logged.

## Dashboard

The React/Vite dashboard is under `frontend/`. Start the backend first, then
run the dashboard in a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

The dashboard uses `http://localhost:8000` by default. To point it at another
FastAPI deployment, copy `frontend/.env.example` to `frontend/.env` and set
`VITE_API_URL`. Configure the backend `CORS_ORIGINS` value with the dashboard
origin when the frontend and API are hosted separately.

The dashboard opens in **1-sec demo stream** mode so displayed values and
graphs update once per second. These synthetic values use the selected case's
latest values as a baseline (or labeled demo seeds if unavailable); they are
not measurements, are never stored, and are not sent to the anomaly model or
assistant. Select **Recorded data** to view stored VitalDB measurements.
Recorded replay polling then runs at a five-second cadence by default; choose
a ten-second cadence or pause it. **Ingest window** manually requests another
ten-second VitalDB source window and stores the returned measurements in
SQLite. Chart metric/range selection, point inspection, anomaly focus, and
review playback are also available.

The replay scenario selector includes labeled demo inputs for `tachycardia`,
`hypoxia`, and `hypotension`. These transform the replayed values only for
testing the anomaly path and store them with a `VitalDB replay simulation: ...`
source. They are not raw VitalDB measurements or clinical diagnoses.

Core endpoints:

- `GET /health`
- `POST /ingest/vitaldb/replay`
- `GET /measurements`
- `GET /health-summary`
- `POST /assistant/explain`

The assistant is a LangChain agent. It uses read-only tools for monitoring
status, latest measurements, and detected anomalies; it does not perform ML
classification or make diagnoses.

Train the Isolation Forest from an actual VitalDB export:

```powershell
python -m ml.train path\to\measurements.csv ml\model\isolation_forest.joblib
```

Training data must contain real measurements with `case_id`, `recorded_at`,
`metric`, and `value` columns. The trainer holds out complete cases for a
leakage-resistant evaluation and can write a report:

```powershell
python -m ml.train path\to\measurements.csv ml\model\isolation_forest.joblib `
  --report ml\model\evaluation.json
```

The data source is surgical-patient data from VitalDB and must not be
presented as astronaut telemetry or treated as clinical validation.

## VitalDB dataset acquisition

The virtual replay endpoint is for live-like monitoring only. For ML
training, acquire the complete recorded dataset with the official VitalDB
packed recordings:

```powershell
python scripts\vitaldb_downloader.py --limit 3 --verbose
python scripts\vitaldb_processor.py `
  data\raw\vitaldb\recordings data\processed\vitaldb `
  --raw-dir data\raw\vitaldb
```

Remove `--limit 3` for the full case inventory. The downloader is resumable,
maintains `data\raw\vitaldb\manifest.csv`, retries failed cases, and validates
recordings with `vitaldb.VitalFile`.

## Training pipeline

After processing recordings into Parquet, prepare case-separated datasets and
train the model:

```powershell
python -m ml.pipeline data\processed\vitaldb\physiological_measurements.parquet `
  --output-dir data\ml `
  --model-path ml\model\isolation_forest.joblib
```

This creates separate train, validation, and test files without splitting
windows from the same case across groups. Incomplete feature windows are
reported and excluded rather than fabricated or silently imputed.
