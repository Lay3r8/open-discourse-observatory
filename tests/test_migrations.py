from pathlib import Path


def test_migrations_define_required_schemas():
    migration = (Path(__file__).parents[1] / "db" / "migrations" / "001_init.sql").read_text()
    for schema in ("staging", "research", "analytics"):
        assert f"create schema if not exists {schema}" in migration.lower()


def test_analytics_exposes_powerbi_views():
    migration = (
        Path(__file__).parents[1] / "db" / "migrations" / "002_analytics_views.sql"
    ).read_text()
    assert "analytics.fact_incidents" in migration
    assert "analytics.country_group_bridge" in migration
    assert "analytics.incident_action_flags" in migration
