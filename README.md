# Open Discourse Observatory

Open Discourse Observatory (ODO) is a reproducible research project for studying political and ideological pressure in Western democracies without assuming the result in advance.

The project separates three layers:

1. **Raw discovery data** - large immutable source datasets and downloaded material.
2. **Candidate data** - automatically extracted or normalized records that still require validation.
3. **Research data** - human-validated incidents with traceable sources and explicit coding decisions.

The initial pilot covers France, Belgium, the United Kingdom, the United States and Canada for 2000-2026. The pilot dataset is a methodology fixture, not a prevalence estimate.

## Stack

- PostgreSQL 18 for the canonical research database and Power BI serving layer.
- DuckDB + Parquet for large local analytical datasets.
- Python 3.13 for ingestion, normalization and validation tooling.
- Docker Compose for local reproducibility.
- Power BI connects to the `analytics` schema.

## Quick start

```bash
cp .env.example .env
make up
make migrate
make import-pilot
make db-check
```

Optional Adminer UI:

```bash
make adminer
```

Open `http://localhost:8080` and connect to host `postgres` using the values from `.env`.

## Repository layout

```text
.
├── data/
│   ├── reference/       # versioned small research fixtures
│   ├── raw/             # immutable bulk downloads, gitignored
│   ├── bronze/          # normalized machine data, gitignored
│   ├── silver/          # deduplicated/enriched candidates, gitignored
│   └── gold/            # analytical outputs, gitignored except small exports
├── db/
│   ├── migrations/      # versioned PostgreSQL DDL
│   └── views/           # analytical SQL notes/views
├── docs/
│   ├── methodology/     # protocol, hypotheses, codebook
│   ├── architecture/    # technical decisions
│   └── powerbi/         # Power BI model guidance
├── src/odo/             # Python package
└── tests/               # unit tests and small fixtures
```

## Core commands

```bash
make up                 # start PostgreSQL + ETL container
make down               # stop containers
make adminer            # start optional Adminer profile
make migrate            # apply SQL migrations
make import-pilot       # import pilot CSV files into research schema
make gdelt-sample       # parse the bundled GDELT sample into bronze Parquet
make test               # run unit tests
make lint               # ruff checks
make format             # ruff format
make db-check           # show canonical row counts
```

## Scientific integrity rules

- Left/right comparisons use the same inclusion criteria and severity definitions.
- Ambiguous ideological attribution stays ambiguous.
- LLM or automated extraction never promotes a record directly into `research`.
- Every validated incident must be traceable to source records.
- Raw source material is immutable and content-addressed where practical.
- Changes to methodology are versioned in Git before results are recomputed.
- Pilot counts must not be interpreted as population prevalence.

See [AGENTS.md](AGENTS.md) and [docs/methodology/protocol-v0.1.md](docs/methodology/protocol-v0.1.md).

## Power BI

Power BI should connect to PostgreSQL and consume only the `analytics` schema. The main tables/views are:

- `analytics.fact_incidents`
- `analytics.fact_sources`
- `analytics.dim_country`
- `analytics.dim_group`
- `analytics.country_group_bridge`
- `analytics.incident_action_flags`

See [docs/powerbi/model.md](docs/powerbi/model.md).
