from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    data_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://discourse:change-me-local-only@localhost:5432/discourse",
            ),
            data_dir=Path(os.getenv("ODO_DATA_DIR", "./data")),
        )
