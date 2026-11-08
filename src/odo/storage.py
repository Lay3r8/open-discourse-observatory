from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from odo.config import Settings
from odo.db import connection

GIB = 1024**3


@dataclass(frozen=True)
class StorageStatus:
    data_bytes: int
    postgres_bytes: int | None
    wsl_free_bytes: int
    host_free_bytes: int | None
    project_bytes: int
    state: str
    reasons: tuple[str, ...]


def _directory_size(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["du", "-sb", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return int(result.stdout.split()[0])
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        total = 0
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        return total


def _postgres_size(settings: Settings) -> int | None:
    try:
        with connection(settings) as conn:
            row = conn.execute("select pg_database_size(current_database())").fetchone()
            return int(row[0]) if row else None
    except Exception:
        return None


def _host_drive_free_bytes(drive: str) -> int | None:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        return None

    command = f"[int64](Get-PSDrive {drive}).Free"
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return int(result.stdout.strip().replace("\r", ""))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def collect_storage_status(settings: Settings) -> StorageStatus:
    data_bytes = _directory_size(settings.data_dir)
    postgres_bytes = _postgres_size(settings)
    project_bytes = data_bytes + (postgres_bytes or 0)
    wsl_free_bytes = shutil.disk_usage(settings.data_dir.resolve()).free
    host_free_bytes = _host_drive_free_bytes(settings.host_drive)

    reasons: list[str] = []
    state = "OK"

    project_gib = project_bytes / GIB
    if project_gib >= settings.storage_stop_gib:
        state = "BLOCKED"
        reasons.append(
            f"project usage {project_gib:.2f} GiB >= ingestion stop "
            f"{settings.storage_stop_gib:.2f} GiB"
        )
    elif project_gib >= settings.storage_warning_gib:
        state = "WARNING"
        reasons.append(
            f"project usage {project_gib:.2f} GiB >= warning "
            f"{settings.storage_warning_gib:.2f} GiB"
        )

    if host_free_bytes is not None:
        host_free_gib = host_free_bytes / GIB
        if host_free_gib <= settings.host_free_stop_gib:
            state = "BLOCKED"
            reasons.append(
                f"host {settings.host_drive}: free {host_free_gib:.2f} GiB <= stop "
                f"{settings.host_free_stop_gib:.2f} GiB"
            )
        elif host_free_gib <= settings.host_free_warning_gib and state == "OK":
            state = "WARNING"
            reasons.append(
                f"host {settings.host_drive}: free {host_free_gib:.2f} GiB <= warning "
                f"{settings.host_free_warning_gib:.2f} GiB"
            )

    return StorageStatus(
        data_bytes=data_bytes,
        postgres_bytes=postgres_bytes,
        wsl_free_bytes=wsl_free_bytes,
        host_free_bytes=host_free_bytes,
        project_bytes=project_bytes,
        state=state,
        reasons=tuple(reasons),
    )


def ensure_ingestion_allowed(settings: Settings) -> StorageStatus:
    status = collect_storage_status(settings)
    if status.state == "BLOCKED":
        joined = "; ".join(status.reasons) or "storage policy blocked ingestion"
        raise RuntimeError(joined)
    return status


def format_gib(value: int | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value / GIB:.2f} GiB"


def render_storage_status(settings: Settings, status: StorageStatus) -> str:
    postgres = format_gib(status.postgres_bytes)
    host = format_gib(status.host_free_bytes)
    lines = [
        "ODO storage",
        "",
        f"Data directory        {format_gib(status.data_bytes)}",
        f"PostgreSQL            {postgres}",
        f"ODO tracked total     {format_gib(status.project_bytes)}",
        "",
        f"Warning threshold     {settings.storage_warning_gib:.2f} GiB",
        f"Ingestion stop        {settings.storage_stop_gib:.2f} GiB",
        f"Absolute budget       {settings.storage_budget_gib:.2f} GiB",
        f"WSL free              {format_gib(status.wsl_free_bytes)}",
        f"Host {settings.host_drive}: free          {host}",
        "",
        f"STATUS: {status.state}",
    ]
    lines.extend(f"- {reason}" for reason in status.reasons)
    return "\n".join(lines)
