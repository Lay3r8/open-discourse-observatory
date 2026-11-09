from pathlib import Path


def test_discovery_query_is_partition_bounded_and_ideology_neutral():
    sql = (
        Path(__file__).parents[1]
        / "research"
        / "discovery"
        / "v2"
        / "gkg_candidates.sql"
    ).read_text(encoding="utf-8")

    assert "_PARTITIONTIME >= @start_ts" in sql
    assert "_PARTITIONTIME < @end_ts" in sql
    assert "@negative_sample_modulus" in sql
    assert "@target_country_pattern" in sql
    assert "V2Locations" in sql

    lowered = sql.lower()
    for ideological_term in (
        "far-right",
        "far right",
        "antifa",
        "leftist",
        "conservative",
        "pro-palestinian",
        "pro-israel",
    ):
        assert ideological_term not in lowered
