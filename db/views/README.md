# Analytical views

The executable analytical views are created by `db/migrations/002_analytics_views.sql`.

Power BI should consume the `analytics` schema rather than querying `research` directly. This keeps dashboard-facing contracts stable while the canonical research model evolves.
