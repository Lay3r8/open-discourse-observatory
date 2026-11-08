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


def test_discovery_migration_defines_ai_staging_boundary():
    migration = (
        Path(__file__).parents[1] / "db" / "migrations" / "003_discovery.sql"
    ).read_text()
    assert "staging.discovery_batch" in migration
    assert "staging.candidate_document" in migration
    assert "staging.ai_analysis" in migration
    assert "analytics.discovery_batches" in migration



def test_discovery_membership_migration_preserves_batch_history():
    migration = (
        Path(__file__).parents[1] / "db" / "migrations" / "004_discovery_membership.sql"
    ).read_text()
    assert "staging.discovery_batch_document" in migration
    assert "first_batch_id" in migration
    assert "first_sample_kind" in migration
    assert "first_matched_token" in migration



def test_semantic_review_migration_defines_gold_set():
    migration = (
        Path(__file__).parents[1] / "db" / "migrations" / "005_semantic_review.sql"
    ).read_text()
    assert "staging.semantic_review_run" in migration
    assert "staging.semantic_gold_label" in migration
    assert "analytics.semantic_gold_labels" in migration



def test_review_ui_audit_migration_tracks_label_changes():
    migration = (
        Path(__file__).parents[1] / "db" / "migrations" / "006_review_ui_audit.sql"
    ).read_text()
    assert "staging.semantic_gold_label_audit" in migration
    assert "previous_relevance" in migration
    assert "new_relevance" in migration
    assert "undone_at" in migration
