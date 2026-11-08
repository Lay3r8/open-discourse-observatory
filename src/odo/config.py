from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    database_url: str
    data_dir: Path
    gcp_project_id: str | None
    bigquery_location: str
    bigquery_max_bytes_gib: float
    negative_sample_modulus: int
    storage_budget_gib: float
    storage_warning_gib: float
    storage_stop_gib: float
    host_drive: str
    host_free_warning_gib: float
    host_free_stop_gib: float

    @classmethod
    def from_env(cls) -> "Settings":
        project = os.getenv("GCP_PROJECT_ID", "").strip() or None
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://discourse:change-me-local-only@localhost:5432/discourse",
            ),
            data_dir=Path(os.getenv("ODO_DATA_DIR", "./data")),
            gcp_project_id=project,
            bigquery_location=os.getenv("GCP_BIGQUERY_LOCATION", "US"),
            bigquery_max_bytes_gib=_env_float("ODO_BIGQUERY_MAX_BYTES_GIB", 2.0),
            negative_sample_modulus=_env_int("ODO_NEGATIVE_SAMPLE_MODULUS", 1000),
            storage_budget_gib=_env_float("ODO_STORAGE_BUDGET_GIB", 200.0),
            storage_warning_gib=_env_float("ODO_STORAGE_WARNING_GIB", 150.0),
            storage_stop_gib=_env_float("ODO_STORAGE_STOP_GIB", 170.0),
            host_drive=os.getenv("ODO_HOST_DRIVE", "E").rstrip(":"),
            host_free_warning_gib=_env_float("ODO_HOST_FREE_WARNING_GIB", 350.0),
            host_free_stop_gib=_env_float("ODO_HOST_FREE_STOP_GIB", 300.0),
        )
