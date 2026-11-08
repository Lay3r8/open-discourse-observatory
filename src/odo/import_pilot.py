from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from odo.db import connection


BOOL_FIELDS = {
    "include_left_right",
    "organized_pressure",
    "deplatforming_attempt",
    "deplatforming_success",
    "content_removal_or_suppression",
    "employment_sanction",
    "career_exit",
    "mandatory_training",
    "professional_sanction",
    "formal_investigation_or_discipline",
    "doxxing",
    "targeted_harassment",
    "threats",
    "physical_obstruction",
    "violence",
    "legal_restriction",
    "state_power",
    "judicially_unlawful",
    "same_camp_dissent",
}

INCIDENT_COLUMNS = [
    "incident_id",
    "event_date",
    "date_precision",
    "year",
    "country",
    "country_iso3",
    "city",
    "sector",
    "target_type",
    "target_name",
    "initiator_name",
    "initiator_specific_ideology",
    "analysis_camp",
    "camp_confidence",
    "attribution_basis",
    "include_left_right",
    "issue",
    "action_primary",
    "organized_pressure",
    "deplatforming_attempt",
    "deplatforming_success",
    "content_removal_or_suppression",
    "employment_sanction",
    "career_exit",
    "mandatory_training",
    "professional_sanction",
    "formal_investigation_or_discipline",
    "doxxing",
    "targeted_harassment",
    "threats",
    "physical_obstruction",
    "violence",
    "legal_restriction",
    "state_power",
    "judicially_unlawful",
    "same_camp_dissent",
    "outcome",
    "evidence_grade",
    "notes",
    "verified_on",
]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lstrip("\ufeff")
    return value or None


def normalize_incident_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in INCIDENT_COLUMNS:
        value = _clean(row.get(key))
        if key in BOOL_FIELDS:
            normalized[key] = value in {"1", "true", "True", "yes", "Yes"}
        elif key == "year":
            normalized[key] = int(value) if value else None
        else:
            normalized[key] = value
    return normalized


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def import_pilot(reference_dir: Path) -> dict[str, int]:
    incidents = [
        normalize_incident_row(row) for row in _read_csv(reference_dir / "fact_incidents_v0_1.csv")
    ]
    sources = _read_csv(reference_dir / "fact_sources_v0_1.csv")
    countries = _read_csv(reference_dir / "dim_country_v0_1.csv")
    groups = _read_csv(reference_dir / "dim_group_v0_1.csv")
    bridge = _read_csv(reference_dir / "bridge_country_group_v0_1.csv")

    with connection() as conn, conn.transaction():
        for row in countries:
            conn.execute(
                """
                insert into research.country(
                    country_iso3, country, region, subregion, predominant_language_group, eu_2026
                ) values (%s,%s,%s,%s,%s,%s)
                on conflict (country_iso3) do update set
                    country=excluded.country,
                    region=excluded.region,
                    subregion=excluded.subregion,
                    predominant_language_group=excluded.predominant_language_group,
                    eu_2026=excluded.eu_2026
                """,
                (
                    _clean(row["country_iso3"]),
                    _clean(row["country"]),
                    _clean(row["region"]),
                    _clean(row["subregion"]),
                    _clean(row["predominant_language_group"]),
                    _clean(row["eu_2026"]) == "1",
                ),
            )

        for row in groups:
            conn.execute(
                """
                insert into research.country_group(group_id, group_name, description)
                values (%s,%s,%s)
                on conflict (group_id) do update set
                    group_name=excluded.group_name,
                    description=excluded.description
                """,
                (_clean(row["group_id"]), _clean(row["group_name"]), _clean(row["description"])),
            )

        for row in bridge:
            conn.execute(
                """
                insert into research.country_group_membership(
                    country_iso3, group_id, membership_type, filter_weight
                ) values (%s,%s,%s,%s)
                on conflict (country_iso3, group_id) do update set
                    membership_type=excluded.membership_type,
                    filter_weight=excluded.filter_weight
                """,
                (
                    _clean(row["country_iso3"]),
                    _clean(row["group_id"]),
                    _clean(row["membership_type"]),
                    float(_clean(row["filter_weight"]) or "1"),
                ),
            )

        placeholders = ",".join(["%s"] * len(INCIDENT_COLUMNS))
        update_columns = [c for c in INCIDENT_COLUMNS if c != "incident_id"]
        assignments = ",".join(f"{c}=excluded.{c}" for c in update_columns)
        sql = (
            f"insert into research.incident ({','.join(INCIDENT_COLUMNS)}) "
            f"values ({placeholders}) on conflict (incident_id) do update set {assignments}"
        )
        for row in incidents:
            conn.execute(sql, tuple(row[col] for col in INCIDENT_COLUMNS))
            conn.execute(
                """
                insert into research.coding_decision(
                    incident_id, field_name, value_text, confidence, basis_type,
                    basis_description, coder_id, source_dataset
                ) values (%s,'analysis_camp',%s,%s,'pilot_import',%s,'pilot-v0.1','pilot-v0.1')
                on conflict (incident_id, field_name, coder_id, source_dataset) do update set
                    value_text=excluded.value_text,
                    confidence=excluded.confidence,
                    basis_description=excluded.basis_description,
                    updated_at=now()
                """,
                (
                    row["incident_id"],
                    row["analysis_camp"],
                    row["camp_confidence"],
                    row["attribution_basis"],
                ),
            )

        for row in sources:
            conn.execute(
                """
                insert into research.source(
                    source_id, incident_id, publisher, source_date, source_type, url, supports
                ) values (%s,%s,%s,%s,%s,%s,%s)
                on conflict (source_id) do update set
                    incident_id=excluded.incident_id,
                    publisher=excluded.publisher,
                    source_date=excluded.source_date,
                    source_type=excluded.source_type,
                    url=excluded.url,
                    supports=excluded.supports
                """,
                (
                    _clean(row["source_id"]),
                    _clean(row["incident_id"]),
                    _clean(row["publisher"]),
                    _clean(row["source_date"]),
                    _clean(row["source_type"]),
                    _clean(row["url"]),
                    _clean(row["supports"]),
                ),
            )

    return {
        "incidents": len(incidents),
        "sources": len(sources),
        "countries": len(countries),
        "groups": len(groups),
        "memberships": len(bridge),
    }
