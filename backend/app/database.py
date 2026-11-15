from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Measurement


SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    source TEXT NOT NULL,
    UNIQUE(case_id, recorded_at, metric, source)
);
CREATE INDEX IF NOT EXISTS idx_measurements_case_time
    ON measurements(case_id, recorded_at);
"""


class MeasurementStore:
    def __init__(self, database_path: str | Path = "data/hms.sqlite3") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def add_many(self, measurements: Iterable[Measurement]) -> int:
        rows = [
            (
                measurement.case_id,
                measurement.recorded_at.isoformat(),
                measurement.metric,
                measurement.value,
                measurement.unit,
                measurement.source,
            )
            for measurement in measurements
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            cursor = connection.executemany(
                """
                INSERT OR IGNORE INTO measurements
                    (case_id, recorded_at, metric, value, unit, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return cursor.rowcount

    def latest(self, case_id: str | None = None, limit: int = 100) -> list[Measurement]:
        query = "SELECT case_id, recorded_at, metric, value, unit, source FROM measurements"
        parameters: tuple[object, ...] = ()
        if case_id is not None:
            query += " WHERE case_id = ?"
            parameters = (case_id,)
        query += " ORDER BY recorded_at DESC LIMIT ?"
        parameters += (limit,)
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [Measurement.model_validate(dict(row)) for row in rows]

    def all_for_case(self, case_id: str | None = None) -> list[Measurement]:
        return self.latest(case_id=case_id, limit=100000)

    def case_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT case_id FROM measurements ORDER BY case_id"
            ).fetchall()
        return [str(row["case_id"]) for row in rows]

__all__ = ["MeasurementStore"]
