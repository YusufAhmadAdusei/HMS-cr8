# HMS-cr8

## Backend

The backend is a single FastAPI application under `backend/app/`. It ingests
VitalDB virtual replay samples, stores validated measurements in SQLite,
extracts time-window features, and exposes the anomaly and AI-agent boundaries.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

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