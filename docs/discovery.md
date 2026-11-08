# Discovery pipeline v1

The discovery layer is deliberately high-recall and ideology-neutral.

## Source

GDELT GKG partitioned table:

`gdelt-bq.gdeltv2.gkg_partitioned`

The query reads one day at a time and selects title/URL plus GKG themes, persons, organizations and locations.

## Safety defaults

- dry-run is the default; `--execute` is required to run BigQuery;
- every day is dry-run first;
- each execution sets `maximum_bytes_billed`;
- project storage is checked before every executed day;
- raw query output is immutable and versioned by query/lexicon/date;
- rejected documents are sampled deterministically as a negative control.

## Current benchmark

The manual 2025-01-01 calibration produced 441 candidate rows and 305 unique normalized titles before semantic filtering. These are calibration figures, not research results.

## Commands

```bash
uv run odo storage status

uv run odo discover \
  --start 2025-01-01 \
  --end 2025-01-02

uv run odo discover \
  --start 2025-01-01 \
  --end 2025-01-02 \
  --execute

uv run odo discovery-stats \
  --start 2025-01-01 \
  --end 2025-01-02
```

Dates use an exclusive end bound.

## Data layout

```text
data/raw/gdelt/gkg/query_version=v1/lexicon_version=v1/date=YYYY-MM-DD/
data/bronze/gdelt/gkg/query_version=v1/lexicon_version=v1/date=YYYY-MM-DD/
```

Raw Parquet contains the selected BigQuery rows. Bronze Parquet adds decoded/normalized titles, canonical URLs and stable hashes used for later clustering.

The next analysis stage is semantic relevance and event clustering; it must not introduce left/right labels into discovery.
