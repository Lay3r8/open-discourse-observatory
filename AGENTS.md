# Agent and contributor rules

## Scientific integrity

1. Never infer ideology from sentiment, demographic traits or the identity of a target.
2. Prefer explicit affiliation, self-identification, named organizations, voting records or reliable sourcing.
3. Preserve `uncertain` classifications instead of forcing a binary camp.
4. Use identical inclusion criteria for left/progressive and right/conservative incidents.
5. Search deliberately for counterexamples to every substantive hypothesis.
6. Do not collapse criticism, boycott, threats and violence into one score unless the scoring rule is preregistered and sensitivity-tested.
7. Automated extraction can create `staging` candidates only. Human validation is required for `research`.
8. Every coding decision that can affect an ideological comparison must be explainable and sourceable.
9. Never overwrite raw downloaded data. Derive bronze/silver/gold outputs from it.
10. Pilot data is a fixture for pipeline validation, not an estimate of real-world prevalence.

## Development

- Python 3.13, pinned by `mise.toml`.
- `uv` manages the local virtual environment and dependency installation.
- PostgreSQL 18.
- DuckDB and Parquet for bulk analytics.
- Polars for dataframe transformations where useful.
- `psycopg` for PostgreSQL access.
- `pytest` for tests.
- `ruff` for linting/formatting.
- Prefer host-side Python commands through `uv run`; containers are for PostgreSQL and optional tooling.
- Database changes require a numbered SQL migration.
- Keep migrations forward-only and deterministic.
- Use UTC timestamps for ingestion metadata.

## Git

- Do not commit directly to `main` for substantive work.
- Prefer one coherent PR per functional batch; do not fragment work into artificial micro-PRs.
- Update tests and documentation with behavioral changes.
- Do not commit `.env`, credentials, database dumps or bulk raw datasets.
