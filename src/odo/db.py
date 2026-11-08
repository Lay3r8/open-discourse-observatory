from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from odo.config import Settings


@contextmanager
def connection(settings: Settings | None = None) -> Iterator[Any]:
    import psycopg

    settings = settings or Settings.from_env()
    with psycopg.connect(settings.database_url) as conn:
        yield conn
