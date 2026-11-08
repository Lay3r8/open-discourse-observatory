from __future__ import annotations

import hashlib
from pathlib import Path

from odo.db import connection


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def _checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def migrate(migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    applied: list[str] = []
    with connection() as conn:
        conn.execute(
            """
            create table if not exists public.schema_migrations (
                filename text primary key,
                checksum text not null,
                applied_at timestamptz not null default now()
            )
            """
        )
        conn.commit()

        for path in sorted(migrations_dir.glob("*.sql")):
            content = path.read_bytes()
            checksum = _checksum(content)
            row = conn.execute(
                "select checksum from public.schema_migrations where filename = %s",
                (path.name,),
            ).fetchone()
            if row:
                if row[0] != checksum:
                    raise RuntimeError(f"Applied migration changed on disk: {path.name}")
                continue

            with conn.transaction():
                conn.execute(content.decode("utf-8"))
                conn.execute(
                    "insert into public.schema_migrations(filename, checksum) values (%s, %s)",
                    (path.name, checksum),
                )
            applied.append(path.name)
    return applied
