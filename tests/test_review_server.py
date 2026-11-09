from pathlib import Path

from odo.review_server import _streamlit_command


def test_streamlit_review_server_is_local_only():
    command = _streamlit_command(8501)
    assert command[:3] == [command[0], "-m", "streamlit"]
    assert "--server.address" in command
    assert command[command.index("--server.address") + 1] == "127.0.0.1"
    assert command[command.index("--server.port") + 1] == "8501"
    assert Path(command[4]).name == "review_app.py"
