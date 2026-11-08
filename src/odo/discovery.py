from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import tomllib
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import polars as pl
from google.cloud import bigquery

from odo.config import Settings
from odo.db import connection
from odo.storage import GIB, ensure_ingestion_allowed

QUERY_VERSION = "v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = PROJECT_ROOT / "research" / "discovery" / QUERY_VERSION
SQL_PATH = DISCOVERY_ROOT / "gkg_candidates.sql"
LEXICON_PATH = DISCOVERY_ROOT / "lexicon.toml"

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "mkt_tok",
}

RAW_COLUMNS = [
    "gdelt_date",
    "source_common_name",
    "source_language",
    "title_raw",
    "url",
    "themes",
    "persons",
    "organizations",
    "locations",
    "sample_kind",
    "matched_token",
]


@dataclass(frozen=True)
class BatchPaths:
    raw_parquet: Path
    bronze_parquet: Path
    manifest: Path


@dataclass(frozen=True)
class QueryEstimate:
    batch_date: date
    total_bytes_processed: int
    max_bytes_billed: int
    safe: bool


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_title(value: str | None) -> tuple[str, str]:
    decoded = html.unescape(value or "")
    decoded = unicodedata.normalize("NFKC", decoded)
    decoded = re.sub(r"\s+", " ", decoded).strip()
    return decoded, decoded.casefold()


def canonicalize_url(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    try:
        parts = urlsplit(raw)
    except ValueError:
        return raw

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if not hostname:
        return raw

    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    filtered_query = []
    for key, val in parse_qsl(parts.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_QUERY_KEYS:
            continue
        filtered_query.append((key, val))

    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            urlencode(sorted(filtered_query)),
            "",
        )
    )


def _load_lexicon() -> dict[str, str]:
    with LEXICON_PATH.open("rb") as handle:
        payload = tomllib.load(handle)
    return {
        "version": payload["metadata"]["version"],
        "english": payload["english"]["pattern"],
        "french": payload["french"]["pattern"],
        "dutch": payload["dutch"]["pattern"],
    }


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def _iter_days(start: date, end: date):
    if end <= start:
        raise ValueError("end must be later than start")
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def _paths(settings: Settings, batch_date: date, lexicon_version: str) -> BatchPaths:
    partition = (
        Path(f"query_version={QUERY_VERSION}")
        / f"lexicon_version={lexicon_version}"
        / f"date={batch_date.isoformat()}"
    )
    raw_dir = settings.data_dir / "raw" / "gdelt" / "gkg" / partition
    bronze_dir = settings.data_dir / "bronze" / "gdelt" / "gkg" / partition
    return BatchPaths(
        raw_parquet=raw_dir / "candidates.parquet",
        bronze_parquet=bronze_dir / "candidates.parquet",
        manifest=bronze_dir / "manifest.json",
    )


def _query_parameters(
    batch_date: date,
    lexicon: dict[str, str],
    negative_sample_modulus: int,
) -> list[bigquery.ScalarQueryParameter]:
    start_ts = datetime.combine(batch_date, time.min, tzinfo=UTC)
    end_ts = start_ts + timedelta(days=1)
    return [
        bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_ts),
        bigquery.ScalarQueryParameter("end_ts", "TIMESTAMP", end_ts),
        bigquery.ScalarQueryParameter("english_pattern", "STRING", lexicon["english"]),
        bigquery.ScalarQueryParameter("french_pattern", "STRING", lexicon["french"]),
        bigquery.ScalarQueryParameter("dutch_pattern", "STRING", lexicon["dutch"]),
        bigquery.ScalarQueryParameter(
            "negative_sample_modulus",
            "INT64",
            negative_sample_modulus,
        ),
    ]


def _configured_project(settings: Settings) -> str:
    if settings.gcp_project_id:
        return settings.gcp_project_id

    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        project = result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        project = ""

    if not project or project == "(unset)":
        raise RuntimeError(
            "No GCP project configured. Set GCP_PROJECT_ID or run "
            "'gcloud config set project <project-id>'."
        )
    return project


def _client(settings: Settings) -> bigquery.Client:
    return bigquery.Client(
        project=_configured_project(settings),
        location=settings.bigquery_location,
    )


def estimate_day(
    settings: Settings,
    batch_date: date,
    *,
    client: bigquery.Client | None = None,
) -> QueryEstimate:
    lexicon = _load_lexicon()
    bq_client = client or _client(settings)
    config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        query_parameters=_query_parameters(
            batch_date,
            lexicon,
            settings.negative_sample_modulus,
        ),
        labels={"odo_stage": "discovery", "odo_query": QUERY_VERSION},
    )
    job = bq_client.query(
        _sql(),
        job_config=config,
        location=settings.bigquery_location,
    )
    processed = int(job.total_bytes_processed or 0)
    max_bytes = int(settings.bigquery_max_bytes_gib * GIB)
    return QueryEstimate(
        batch_date=batch_date,
        total_bytes_processed=processed,
        max_bytes_billed=max_bytes,
        safe=processed <= max_bytes,
    )


def _raw_rows(query_rows) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in query_rows:
        payload = {column: row[column] for column in RAW_COLUMNS}
        rows.append(payload)
    return rows


def _bronze_rows(raw_rows: list[dict[str, object]], batch_date: date) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for row in raw_rows:
        title, title_norm = normalize_title(
            str(row.get("title_raw") or "")
        )
        canonical_url = canonicalize_url(str(row.get("url") or ""))
        source_name = str(row.get("source_common_name") or "")
        identity_source = canonical_url or f"{source_name}|{title_norm}"
        document_id = _sha256_text(f"{batch_date.isoformat()}|{identity_source}")

        normalized.append(
            {
                "candidate_document_id": document_id,
                "discovery_date": batch_date.isoformat(),
                "gdelt_date": str(row.get("gdelt_date") or ""),
                "source_common_name": source_name,
                "source_language": row.get("source_language"),
                "title": title,
                "normalized_title": title_norm,
                "title_sha256": _sha256_text(title_norm),
                "source_url": str(row.get("url") or ""),
                "canonical_url": canonical_url,
                "url_sha256": _sha256_text(canonical_url or identity_source),
                "sample_kind": str(row.get("sample_kind") or ""),
                "matched_token": row.get("matched_token"),
                "themes": row.get("themes"),
                "persons": row.get("persons"),
                "organizations": row.get("organizations"),
                "locations": row.get("locations"),
            }
        )
    return normalized


def _frame(rows: list[dict[str, object]], columns: list[str]) -> pl.DataFrame:
    if rows:
        return pl.DataFrame(rows)
    return pl.DataFrame({column: [] for column in columns})


def _write_parquet_immutable(frame: pl.DataFrame, path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path, compression="zstd")


def _manifest_counts(bronze_rows: list[dict[str, object]]) -> dict[str, int]:
    candidates = [row for row in bronze_rows if row["sample_kind"] == "candidate"]
    negatives = [row for row in bronze_rows if row["sample_kind"] == "negative_control"]
    return {
        "candidate_rows": len(candidates),
        "negative_control_rows": len(negatives),
        "unique_urls": len({str(row["canonical_url"]) for row in candidates}),
        "unique_titles": len({str(row["title_sha256"]) for row in candidates}),
    }


def _persist_staging(
    settings: Settings,
    manifest: dict[str, object],
    bronze_rows: list[dict[str, object]],
) -> None:
    with connection(settings) as conn, conn.transaction():
        conn.execute(
            """
            insert into staging.discovery_batch(
                batch_id, source_system, query_version, lexicon_version, batch_date,
                gcp_project_id, bigquery_location, query_bytes_processed,
                query_bytes_billed, max_bytes_billed, candidate_rows,
                negative_control_rows, unique_urls, unique_titles, raw_path,
                bronze_path, manifest_path, status, completed_at
            ) values (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'complete',now()
            )
            on conflict (batch_id) do update set
                query_bytes_processed=excluded.query_bytes_processed,
                query_bytes_billed=excluded.query_bytes_billed,
                candidate_rows=excluded.candidate_rows,
                negative_control_rows=excluded.negative_control_rows,
                unique_urls=excluded.unique_urls,
                unique_titles=excluded.unique_titles,
                raw_path=excluded.raw_path,
                bronze_path=excluded.bronze_path,
                manifest_path=excluded.manifest_path,
                status='complete',
                completed_at=now()
            """,
            (
                manifest["batch_id"],
                "gdelt-gkg",
                manifest["query_version"],
                manifest["lexicon_version"],
                manifest["batch_date"],
                manifest["gcp_project_id"],
                manifest["bigquery_location"],
                manifest["query_bytes_processed"],
                manifest["query_bytes_billed"],
                manifest["max_bytes_billed"],
                manifest["candidate_rows"],
                manifest["negative_control_rows"],
                manifest["unique_urls"],
                manifest["unique_titles"],
                manifest["raw_path"],
                manifest["bronze_path"],
                manifest["manifest_path"],
            ),
        )

        sql = """
            insert into staging.candidate_document(
                candidate_document_id, batch_id, discovery_date, gdelt_date,
                source_common_name, source_language, title, normalized_title,
                title_sha256, source_url, canonical_url, url_sha256, sample_kind,
                matched_token, metadata
            ) values (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb
            )
            on conflict (candidate_document_id) do update set
                batch_id=excluded.batch_id,
                title=excluded.title,
                normalized_title=excluded.normalized_title,
                title_sha256=excluded.title_sha256,
                canonical_url=excluded.canonical_url,
                url_sha256=excluded.url_sha256,
                sample_kind=excluded.sample_kind,
                matched_token=excluded.matched_token,
                metadata=excluded.metadata
        """
        values = []
        for row in bronze_rows:
            metadata = json.dumps(
                {
                    "themes": row.get("themes"),
                    "persons": row.get("persons"),
                    "organizations": row.get("organizations"),
                    "locations": row.get("locations"),
                },
                ensure_ascii=False,
            )
            values.append(
                (
                    row["candidate_document_id"],
                    manifest["batch_id"],
                    row["discovery_date"],
                    row["gdelt_date"],
                    row["source_common_name"],
                    row["source_language"],
                    row["title"],
                    row["normalized_title"],
                    row["title_sha256"],
                    row["source_url"],
                    row["canonical_url"],
                    row["url_sha256"],
                    row["sample_kind"],
                    row["matched_token"],
                    metadata,
                )
            )

        with conn.cursor() as cur:
            cur.executemany(sql, values)


def _load_existing_batch(
    settings: Settings,
    paths: BatchPaths,
) -> dict[str, object]:
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    bronze_rows = pl.read_parquet(paths.bronze_parquet).to_dicts()
    _persist_staging(settings, manifest, bronze_rows)
    return manifest


def execute_day(
    settings: Settings,
    batch_date: date,
    *,
    client: bigquery.Client | None = None,
) -> dict[str, object]:
    lexicon = _load_lexicon()
    paths = _paths(settings, batch_date, lexicon["version"])

    if paths.manifest.exists():
        if not paths.raw_parquet.exists() or not paths.bronze_parquet.exists():
            raise RuntimeError(f"incomplete existing discovery batch: {paths.manifest.parent}")
        return _load_existing_batch(settings, paths)

    if paths.raw_parquet.exists() or paths.bronze_parquet.exists():
        raise RuntimeError(
            f"partial discovery output exists without manifest: {paths.bronze_parquet.parent}"
        )

    ensure_ingestion_allowed(settings)

    bq_client = client or _client(settings)
    estimate = estimate_day(settings, batch_date, client=bq_client)
    if not estimate.safe:
        raise RuntimeError(
            f"dry-run estimate {estimate.total_bytes_processed / GIB:.2f} GiB exceeds "
            f"configured maximum {estimate.max_bytes_billed / GIB:.2f} GiB"
        )

    config = bigquery.QueryJobConfig(
        maximum_bytes_billed=estimate.max_bytes_billed,
        query_parameters=_query_parameters(
            batch_date,
            lexicon,
            settings.negative_sample_modulus,
        ),
        labels={"odo_stage": "discovery", "odo_query": QUERY_VERSION},
    )
    job = bq_client.query(
        _sql(),
        job_config=config,
        location=settings.bigquery_location,
    )
    query_rows = job.result()
    raw_rows = _raw_rows(query_rows)
    bronze_rows = _bronze_rows(raw_rows, batch_date)

    raw_frame = _frame(raw_rows, RAW_COLUMNS)
    bronze_columns = list(bronze_rows[0]) if bronze_rows else [
        "candidate_document_id",
        "discovery_date",
        "gdelt_date",
        "source_common_name",
        "source_language",
        "title",
        "normalized_title",
        "title_sha256",
        "source_url",
        "canonical_url",
        "url_sha256",
        "sample_kind",
        "matched_token",
        "themes",
        "persons",
        "organizations",
        "locations",
    ]
    bronze_frame = _frame(bronze_rows, bronze_columns)

    _write_parquet_immutable(raw_frame, paths.raw_parquet)
    _write_parquet_immutable(bronze_frame, paths.bronze_parquet)

    counts = _manifest_counts(bronze_rows)
    manifest = {
        "batch_id": f"gkg-{QUERY_VERSION}-{lexicon['version']}-{batch_date.isoformat()}",
        "source_system": "gdelt-gkg",
        "query_version": QUERY_VERSION,
        "lexicon_version": lexicon["version"],
        "batch_date": batch_date.isoformat(),
        "gcp_project_id": bq_client.project,
        "bigquery_location": settings.bigquery_location,
        "query_bytes_processed": int(job.total_bytes_processed or estimate.total_bytes_processed),
        "query_bytes_billed": int(job.total_bytes_billed or 0),
        "max_bytes_billed": estimate.max_bytes_billed,
        **counts,
        "raw_rows": len(raw_rows),
        "raw_path": str(paths.raw_parquet),
        "bronze_path": str(paths.bronze_parquet),
        "manifest_path": str(paths.manifest),
        "raw_sha256": _sha256_file(paths.raw_parquet),
        "bronze_sha256": _sha256_file(paths.bronze_parquet),
        "sql_sha256": _sha256_file(SQL_PATH),
        "lexicon_sha256": _sha256_file(LEXICON_PATH),
        "created_at": datetime.now(UTC).isoformat(),
    }
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _persist_staging(settings, manifest, bronze_rows)
    return manifest


def discover_range(
    settings: Settings,
    start: date,
    end: date,
    *,
    execute: bool,
) -> list[dict[str, object] | QueryEstimate]:
    bq_client = _client(settings)
    results: list[dict[str, object] | QueryEstimate] = []
    for batch_date in _iter_days(start, end):
        if execute:
            results.append(execute_day(settings, batch_date, client=bq_client))
        else:
            results.append(estimate_day(settings, batch_date, client=bq_client))
    return results


def discovery_stats(settings: Settings, start: date, end: date) -> dict[str, object]:
    lexicon = _load_lexicon()
    candidate_rows = 0
    negative_rows = 0
    query_bytes = 0
    billed_bytes = 0
    raw_bytes = 0
    bronze_bytes = 0
    urls: set[str] = set()
    titles: set[str] = set()
    batches = 0

    for batch_date in _iter_days(start, end):
        paths = _paths(settings, batch_date, lexicon["version"])
        if not paths.manifest.exists():
            continue
        manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
        batches += 1
        candidate_rows += int(manifest["candidate_rows"])
        negative_rows += int(manifest["negative_control_rows"])
        query_bytes += int(manifest["query_bytes_processed"])
        billed_bytes += int(manifest["query_bytes_billed"])
        raw_bytes += paths.raw_parquet.stat().st_size
        bronze_bytes += paths.bronze_parquet.stat().st_size

        frame = pl.read_parquet(
            paths.bronze_parquet,
            columns=["sample_kind", "canonical_url", "title_sha256"],
        ).filter(pl.col("sample_kind") == "candidate")
        urls.update(str(value) for value in frame["canonical_url"].to_list())
        titles.update(str(value) for value in frame["title_sha256"].to_list())

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "batches": batches,
        "candidate_rows": candidate_rows,
        "negative_control_rows": negative_rows,
        "unique_urls": len(urls),
        "unique_titles": len(titles),
        "query_bytes_processed": query_bytes,
        "query_bytes_billed": billed_bytes,
        "raw_bytes": raw_bytes,
        "bronze_bytes": bronze_bytes,
    }
