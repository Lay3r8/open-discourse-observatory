# Architecture

## Data flow

```text
external sources
      |
      v
 data/raw        immutable downloaded artifacts
      |
      v
 data/bronze     normalized machine-readable Parquet
      |
      v
 data/silver     deduplicated/enriched candidates
      |
      +------> PostgreSQL staging.*
                    |
               human validation
                    |
                    v
              research.*
                    |
                    v
              analytics.*
                    |
                    v
                 Power BI
```

## Why PostgreSQL + Parquet/DuckDB

The validated research corpus is expected to remain small enough for PostgreSQL, while discovery can involve millions of source rows. Large source datasets therefore remain in Parquet and can be queried by DuckDB without loading all raw material into the canonical database.

## Database boundaries

- `staging`: machine-generated candidates and document metadata; not accepted research evidence.
- `research`: human-validated canonical incidents, sources and coding decisions.
- `analytics`: stable read models/views for Power BI and reproducible reporting.

## Raw immutability

Raw downloads are never edited in place. A downloaded artifact is identified by URL/time/path and SHA-256 where practical. Normalization creates a new downstream artifact.

## Scaling path

Do not add Kafka, OpenSearch or ClickHouse until a measured bottleneck requires them. DuckDB + partitioned Parquet should be the first bulk-analysis layer.

## Local execution model

Python tooling runs on the host through `mise` + `uv`. PostgreSQL is containerized through Docker Compose or Podman Compose. This keeps the Python development loop native while preserving a reproducible database service.
