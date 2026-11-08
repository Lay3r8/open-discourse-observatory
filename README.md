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
- BigQuery for remote GDELT scans with mandatory dry-runs and per-query byte ceilings.
- Python 3.13 pinned by `mise`; `uv` manages the project environment and dependencies.
- PostgreSQL runs through a Compose-compatible container engine (Docker Compose or Podman Compose).
- Power BI connects to the `analytics` schema.

## Quick start

The project is designed for `mise + uv` locally. PostgreSQL is the only service that needs a container engine.

```bash
make doctor
make bootstrap
```

`make bootstrap` runs `mise install`, `uv sync --extra dev`, creates `.env` from `.env.example` when missing, starts PostgreSQL, applies migrations, imports the pilot, and prints row counts.

If `make doctor` reports no Compose engine, install Docker Compose or Podman with a Compose provider, then rerun `make bootstrap`.

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
make doctor             # check mise, uv, Python and container engine
make setup              # mise install + uv sync + create .env if missing
make bootstrap          # one-shot local bootstrap
make up                 # start PostgreSQL
make down               # stop containers
make adminer            # start optional Adminer profile
make migrate            # apply SQL migrations via uv
make import-pilot       # import pilot CSV files via uv
make gdelt-sample       # parse the bundled GDELT sample into bronze Parquet
make storage            # show ODO/WSL/Windows-host storage guardrails
make discover-dry       # dry-run the calibrated 2025-01-01 GKG discovery query
make discovery-stats    # summarize locally materialized discovery batches
# semantic review commands are exposed through `uv run odo ...`
make test               # run unit tests via uv
make lint               # ruff checks via uv
make format             # ruff format via uv
make db-check           # show canonical row counts via uv
```

## Scientific integrity rules

- Left/right comparisons use the same inclusion criteria and severity definitions.
- Ambiguous ideological attribution stays ambiguous.
- LLM or automated extraction never promotes a record directly into `research`.
- Every validated incident must be traceable to source records.
- Raw source material is immutable and content-addressed where practical.
- Changes to methodology are versioned in Git before results are recomputed.
- Pilot counts must not be interpreted as population prevalence.

See [AGENTS.md](AGENTS.md), [docs/methodology/protocol-v0.1.md](docs/methodology/protocol-v0.1.md), [docs/discovery.md](docs/discovery.md), [docs/semantic-review.md](docs/semantic-review.md), [docs/review-ui.md](docs/review-ui.md) and [docs/ai-analysis.md](docs/ai-analysis.md).

## Power BI

Power BI should connect to PostgreSQL and consume only the `analytics` schema. The main tables/views are:

- `analytics.fact_incidents`
- `analytics.fact_sources`
- `analytics.dim_country`
- `analytics.dim_group`
- `analytics.country_group_bridge`
- `analytics.incident_action_flags`

See [docs/powerbi/model.md](docs/powerbi/model.md).


## Big-data discovery

Authenticate locally with Google Application Default Credentials before querying GDELT:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$(gcloud config get-value project)"
```

The default discovery command is a **dry-run**:

```bash
uv run odo discover --start 2025-01-01 --end 2025-01-02
```

Only `--execute` runs BigQuery and writes Parquet/staging rows:

```bash
make migrate
uv run odo storage status
uv run odo discover --start 2025-01-01 --end 2025-01-02 --execute
uv run odo discovery-stats --start 2025-01-01 --end 2025-01-02
```

The project defaults to a 200 GiB local budget, warning at 150 GiB and blocking new ingestion at 170 GiB. Under WSL it also checks the configured Windows host drive and blocks when host free space reaches the configured stop threshold.

Discovery is intentionally ideology-neutral. It finds action signals first; later semantic/AI stages assess relevance, clustering and structured facts. AI output is stored in staging and cannot promote records into the canonical research schema.


## Semantic review / gold set

After a calibrated discovery window is materialized, create a deterministic human-review sample:

```bash
uv run odo semantic-sample --start 2025-01-01 --end 2025-01-08 --size 500
```

The generated CSV is intentionally outside Git under `data/silver/semantic-review/`. Label it according to `docs/semantic-review.md`, import it with `odo semantic-import`, then use `odo semantic-stats` to track review progress. This gold set is the benchmark for later AI relevance analysis.


### Browser-based annotation

For the initial human gold-set review, use the local Streamlit UI instead of editing the CSV directly:

```bash
uv run odo review \
  --run-id semantic-v1-2025-01-01-2025-01-08-bfe1d5267a05 \
  --reviewer simon \
  --target 150
```

The review server is local-only (`127.0.0.1`). Candidate/control status, discovery token and ideological information are intentionally hidden while coding. Review v2 separates **coercion** from **expressive political/ideological scope**; the final relevance label is derived automatically from those two axes.
