from __future__ import annotations

import argparse
import csv
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


API_URL = "https://api.vitaldb.net"
DATASET_VERSION = "1.0.1"
LOGGER = logging.getLogger("vitaldb.downloader")
MANIFEST_FIELDS = [
    "case_id",
    "download_url",
    "local_filename",
    "status",
    "file_size",
    "downloaded_at",
    "validation_status",
    "error_message",
]


def acquire_dataset(
    output_dir: str | Path = "data/raw/vitaldb",
    case_limit: int | None = None,
    workers: int = 4,
    retries: int = 3,
) -> dict[str, int]:
    root = Path(output_dir)
    recordings_dir = root / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    download_metadata(root)
    case_ids = read_case_ids(root / "cases.csv")
    if case_limit is not None:
        case_ids = case_ids[:case_limit]

    manifest_path = root / "manifest.csv"
    manifest = load_manifest(manifest_path)
    for case_id in case_ids:
        manifest.setdefault(case_id, _manifest_row(case_id, recordings_dir))
    write_manifest(manifest_path, manifest)

    completed = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                download_case,
                case_id,
                recordings_dir,
                manifest[case_id],
                retries,
            ): case_id
            for case_id in case_ids
        }
        for future in as_completed(futures):
            case_id = futures[future]
            row = future.result()
            manifest[case_id] = row
            write_manifest(manifest_path, manifest)
            if row["status"] == "downloaded":
                completed += 1
            else:
                failed += 1
            LOGGER.info(
                "case=%s status=%s validation=%s",
                case_id,
                row["status"],
                row["validation_status"],
            )
    return {"discovered": len(case_ids), "downloaded": completed, "failed": failed}


def download_metadata(root: Path, retries: int = 3) -> None:
    root.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=60.0, follow_redirects=True)
    for endpoint, filename in (("cases", "cases.csv"), ("labs", "labs.csv")):
        destination = root / filename
        if destination.exists() and destination.stat().st_size > 0:
            continue
        _download_file(client, f"{API_URL}/{endpoint}", destination, retries)
    client.close()


def download_case(
    case_id: str,
    recordings_dir: Path,
    existing: dict[str, str],
    retries: int,
) -> dict[str, str]:
    destination = recordings_dir / f"{case_id}.vital"
    url = f"{API_URL}/{DATASET_VERSION}/{case_id}.vital"
    row = _manifest_row(case_id, recordings_dir)
    if destination.exists() and destination.stat().st_size > 0:
        try:
            track_count = validate_recording(destination)
            row.update(
                status="downloaded",
                file_size=str(destination.stat().st_size),
                downloaded_at=existing.get("downloaded_at") or _now(),
                validation_status=f"valid:{track_count}_tracks",
            )
            return row
        except RuntimeError as error:
            row.update(
                status="downloaded",
                file_size=str(destination.stat().st_size),
                downloaded_at=existing.get("downloaded_at") or _now(),
                validation_status=f"pending_parser:{error}",
            )
            return row
        except Exception as error:
            LOGGER.warning("revalidating case %s failed: %s", case_id, error)
            destination.unlink(missing_ok=True)

    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            _download_file(client, url, destination, retries)
        try:
            track_count = validate_recording(destination)
            validation_status = f"valid:{track_count}_tracks"
        except RuntimeError as error:
            validation_status = f"pending_parser:{error}"
        row.update(
            status="downloaded",
            file_size=str(destination.stat().st_size),
            downloaded_at=_now(),
            validation_status=validation_status,
        )
    except Exception as error:
        row.update(status="failed", validation_status="invalid", error_message=str(error))
        destination.unlink(missing_ok=True)
    return row


def validate_recording(path: Path) -> int:
    try:
        import vitaldb
    except ImportError as error:
        raise RuntimeError("Install vitaldb before validating recordings") from error
    vital_file = vitaldb.VitalFile(str(path), header_only=True)
    track_names = vital_file.get_track_names()
    if not track_names:
        raise ValueError("recording contains no tracks")
    return len(track_names)


def _download_file(
    client: httpx.Client,
    url: str,
    destination: Path,
    retries: int,
) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                append = offset > 0 and response.status_code == 206
                with partial.open("ab" if append else "wb") as file:
                    for chunk in response.iter_bytes():
                        file.write(chunk)
            if partial.stat().st_size == 0:
                raise ValueError("downloaded file is empty")
            os.replace(partial, destination)
            return
        except (OSError, httpx.HTTPError, ValueError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"download failed for {url}: {last_error}") from last_error


def read_case_ids(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return [str(row["caseid"]) for row in csv.DictReader(file) if row.get("caseid")]


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        return {row["case_id"]: row for row in csv.DictReader(file) if row.get("case_id")}


def write_manifest(path: Path, rows: dict[str, dict[str, str]]) -> None:
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows[case_id] for case_id in sorted(rows, key=int))
    os.replace(temporary, path)


def _manifest_row(case_id: str, recordings_dir: Path) -> dict[str, str]:
    return {
        "case_id": case_id,
        "download_url": f"{API_URL}/{DATASET_VERSION}/{case_id}.vital",
        "local_filename": str(recordings_dir / f"{case_id}.vital"),
        "status": "pending",
        "file_size": "",
        "downloaded_at": "",
        "validation_status": "pending",
        "error_message": "",
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acquire VitalDB packed recordings")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/vitaldb"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    print(acquire_dataset(args.output_dir, args.limit, args.workers, args.retries))
