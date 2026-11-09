# Power BI model

Connect Power BI to PostgreSQL and use the `analytics` schema.

## Tables/views

- `analytics.fact_incidents`
- `analytics.fact_sources`
- `analytics.dim_country`
- `analytics.dim_group`
- `analytics.country_group_bridge`
- `analytics.incident_action_flags`
- `analytics.left_right_incidents`

## Relationships

- `dim_country[country_iso3]` 1:* `fact_incidents[country_iso3]`
- `fact_incidents[incident_id]` 1:* `fact_sources[incident_id]`
- `dim_group[group_id]` 1:* `country_group_bridge[group_id]`
- `dim_country[country_iso3]` 1:* `country_group_bridge[country_iso3]`

For group filtering, use a bidirectional relationship only between `dim_country` and `country_group_bridge`; keep the remainder single-direction unless a concrete visual requires otherwise.

## Required analysis filters

- Direct left/right comparison: `include_left_right = TRUE`.
- Robustness 1: `camp_confidence = High`.
- Robustness 2: `camp_confidence in {High, Medium}`.
- Never present pilot raw counts as prevalence.

## Suggested report pages

1. Overview
2. Left/right matched comparisons
3. Geography and country groups
4. Same-camp dissent / boundary policing
5. Media/institutional response (when coverage data is populated)
6. Public funding (when funding data is populated)
7. Incident drill-through with source URLs and coding confidence
