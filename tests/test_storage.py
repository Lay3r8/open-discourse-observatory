from odo.config import Settings
from odo.storage import GIB, StorageStatus, render_storage_status


def test_render_storage_status_contains_budget_and_host():
    settings = Settings(
        database_url="postgresql://example",
        data_dir=None,  # type: ignore[arg-type]
        gcp_project_id=None,
        bigquery_location="US",
        bigquery_max_bytes_gib=2,
        negative_sample_modulus=1000,
        storage_budget_gib=200,
        storage_warning_gib=150,
        storage_stop_gib=170,
        host_drive="E",
        host_free_warning_gib=350,
        host_free_stop_gib=300,
    )
    status = StorageStatus(
        data_bytes=1 * GIB,
        postgres_bytes=2 * GIB,
        wsl_free_bytes=900 * GIB,
        host_free_bytes=591 * GIB,
        project_bytes=3 * GIB,
        state="OK",
        reasons=(),
    )
    rendered = render_storage_status(settings, status)
    assert "ODO tracked total     3.00 GiB" in rendered
    assert "Absolute budget       200.00 GiB" in rendered
    assert "Host E: free          591.00 GiB" in rendered
    assert "STATUS: OK" in rendered
