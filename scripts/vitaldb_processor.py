from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd


LOGGER = logging.getLogger("vitaldb.processor")
TRACK_CANDIDATES = {
    "heart_rate": {"Solar8000/HR", "HR"},
    "ecg": {"SNUADC/ECG_II", "ECG_II"},
    "spo2": {"Solar8000/PLETH_SPO2", "SpO2"},
    "systolic_bp": {"Solar8000/NIBP_SBP", "Solar8000/ART_SBP"},
    "diastolic_bp": {"Solar8000/NIBP_DBP", "Solar8000/ART_DBP"},
    "respiratory_rate": {"Solar8000/RR", "RR"},
    "temperature": {"Solar8000/BT", "BT"},
}


def prepare_metadata(
    raw_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, int]:
    raw = Path(raw_dir)
    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    cases = pd.read_csv(raw / "cases.csv")
    labs = pd.read_csv(raw / "labs.csv")
    cases.to_parquet(processed / "case_metadata.parquet", index=False)
    labs.to_parquet(processed / "labs.parquet", index=False)
    return {"cases": len(cases), "labs": len(labs)}


def build_track_inventory(
    recordings_dir: str | Path,
    output_csv: str | Path,
    max_cases: int | None = None,
) -> dict[str, int]:
    import vitaldb

    recordings = sorted(Path(recordings_dir).glob("*.vital"), key=lambda path: int(path.stem))
    if max_cases is not None:
        recordings = recordings[:max_cases]
    rows: list[dict[str, Any]] = []
    for path in recordings:
        case_id = path.stem
        try:
            vital_file = vitaldb.VitalFile(str(path))
            for track_name, track in vital_file.trks.items():
                sample_count = sum(
                    len(record.get("val", [])) if isinstance(record.get("val"), list) else 1
                    for record in track.recs
                )
                rows.append(
                    {
                        "case_id": case_id,
                        "track_name": track_name,
                        "track_type": str(track.type),
                        "sampling_frequency": track.srate,
                        "unit": track.unit,
                        "sample_count": sample_count,
                        "recording_duration_seconds": max(0, vital_file.dtend - vital_file.dtstart),
                        "missing_data_percentage": _missing_percentage(track),
                    }
                )
        except Exception as error:
            LOGGER.warning("could not inspect case %s: %s", case_id, error)
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    return {"cases": len(recordings), "tracks": len(rows)}


def extract_measurements(
    recordings_dir: str | Path,
    output_parquet: str | Path,
    interval_seconds: float = 1.0,
    max_cases: int | None = None,
) -> dict[str, int]:
    import vitaldb

    output = Path(output_parquet)
    output.parent.mkdir(parents=True, exist_ok=True)
    import pyarrow as pa
    import pyarrow.parquet as pq

    writer: Any = None
    case_count = 0
    measurement_count = 0
    paths = sorted(Path(recordings_dir).glob("*.vital"), key=lambda item: int(item.stem))
    if max_cases is not None:
        paths = paths[:max_cases]
    for path in paths:
        header = vitaldb.VitalFile(str(path), header_only=True)
        selected = _select_tracks(header.get_track_names())
        if not selected:
            continue
        vital_file = vitaldb.VitalFile(str(path), selected)
        values, names = vital_file.get_samples(
            selected,
            interval=interval_seconds,
            return_timestamp=True,
        )
        timestamps = values[0]
        frame = pd.DataFrame({"recorded_at": pd.to_datetime(timestamps, unit="s", utc=True)})
        for index, track_name in enumerate(names[1:]):
            frame[track_name] = values[index + 1]
        long_frame = frame.melt(
            id_vars=["recorded_at"],
            var_name="metric",
            value_name="value",
        ).dropna(subset=["value"])
        long_frame.insert(0, "case_id", path.stem)
        long_frame["source"] = "VitalDB recorded dataset"
        case_count += 1
        measurement_count += len(long_frame)
        table = pa.Table.from_pandas(long_frame, preserve_index=False)
        if writer is None:
            if output.exists():
                output.unlink()
            writer = pq.ParquetWriter(output, table.schema)
        writer.write_table(table)
    if writer is not None:
        writer.close()
    return {"cases": case_count, "measurements": measurement_count}


def _select_tracks(track_names: list[str]) -> list[str]:
    selected: list[str] = []
    for candidates in TRACK_CANDIDATES.values():
        selected.extend(name for name in track_names if name in candidates)
    return list(dict.fromkeys(selected))


def _missing_percentage(track: Any) -> float | None:
    total = 0
    missing = 0
    for record in track.recs:
        values = record.get("val")
        if values is None:
            continue
        if hasattr(values, "__len__") and not isinstance(values, (str, bytes)):
            values = list(values)
        else:
            values = [values]
        total += len(values)
        missing += sum(value is None for value in values)
    if total == 0:
        return None
    return 100.0 * missing / total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect and process VitalDB recordings")
    parser.add_argument("recordings_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/vitaldb"))
    parser.add_argument("--max-cases", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    metadata = prepare_metadata(args.raw_dir, args.output_dir)
    inventory = build_track_inventory(
        args.recordings_dir,
        args.output_dir / "track_inventory.csv",
        max_cases=args.max_cases,
    )
    extracted = extract_measurements(
        args.recordings_dir,
        args.output_dir / "physiological_measurements.parquet",
        max_cases=args.max_cases,
    )
    (args.output_dir / "dataset_summary.json").write_text(
        json.dumps(
            {"metadata": metadata, "inventory": inventory, "extraction": extracted},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"metadata": metadata, "inventory": inventory, "extraction": extracted}))
