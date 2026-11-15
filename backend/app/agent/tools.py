from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool


def build_health_tools(summary: dict[str, Any]) -> list[StructuredTool]:
    def get_monitoring_status() -> str:
        """Return the monitoring status, source, and generation timestamp."""
        return json.dumps(
            {
                "status": summary.get("status"),
                "data_source": summary.get("data_source"),
                "generated_at": summary.get("generated_at"),
            }
        )

    def get_latest_measurements() -> str:
        """Return the latest available measurements with units and timestamps."""
        return json.dumps(summary.get("latest_measurements", []), default=str)

    def get_detected_anomalies() -> str:
        """Return detected unusual windows and contributing features."""
        return json.dumps(summary.get("anomalies", []), default=str)

    return [
        StructuredTool.from_function(get_monitoring_status),
        StructuredTool.from_function(get_latest_measurements),
        StructuredTool.from_function(get_detected_anomalies),
    ]
