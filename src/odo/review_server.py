from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def _streamlit_command(port: int) -> list[str]:
    app = Path(__file__).with_name("review_app.py")
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]


def _open_browser(url: str) -> None:
    powershell = shutil.which("powershell.exe")
    if powershell:
        try:
            subprocess.Popen(
                [
                    powershell,
                    "-NoProfile",
                    "-Command",
                    f"Start-Process '{url}'",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except OSError:
            pass

    webbrowser.open(url)


def launch_review_ui(
    *,
    run_id: str,
    reviewer_id: str,
    target: int = 150,
    port: int = 8501,
    open_browser: bool = True,
) -> int:
    if not run_id.strip():
        raise ValueError("run_id is required")
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")
    if target <= 0:
        raise ValueError("target must be positive")
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")

    env = os.environ.copy()
    env["ODO_REVIEW_RUN_ID"] = run_id.strip()
    env["ODO_REVIEWER_ID"] = reviewer_id.strip()
    env["ODO_REVIEW_TARGET"] = str(target)

    url = f"http://localhost:{port}"
    print(f"ODO review UI: {url}")
    print("Ctrl+C stops the local review server.")

    process = subprocess.Popen(
        _streamlit_command(port),
        env=env,
    )
    try:
        if open_browser:
            time.sleep(1.0)
            _open_browser(url)
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130
