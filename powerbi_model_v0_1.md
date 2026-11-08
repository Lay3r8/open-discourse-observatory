# Power BI model — pilot v0.1

## Import
Import the sheets `Incidents`, `Sources`, `DimDate`, `DimCountry`, `DimGroup`, and `CountryGroupBridge` from the XLSX, or use the matching CSV files.

## Relationships
- `DimDate[date]` 1:* `FactIncidents[event_date]`
- `DimCountry[country_iso3]` 1:* `FactIncidents[country_iso3]`
- `FactIncidents[incident_id]` 1:* `FactSources[incident_id]`
- `DimGroup[group_id]` 1:* `CountryGroupBridge[group_id]`
- `DimCountry[country_iso3]` 1:* `CountryGroupBridge[country_iso3]`; use **Both** cross-filter only here so a group selection propagates to countries and incidents.

## Critical analysis filters
- Use `include_left_right = 1` for left/right comparison.
- Run robustness views with `camp_confidence = High` only, then High+Medium.
- Do not interpret raw pilot counts as prevalence.

## Measures
The `DAX` sheet in the workbook contains ready-to-copy measures.
