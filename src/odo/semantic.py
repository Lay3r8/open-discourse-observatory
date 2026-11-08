from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from odo.config import Settings
from odo.db import connection

SCHEMA_VERSION = "semantic-review-v1"
CURRENT_LEXICON_VERSION = "v2"
VALID_LABELS = {"relevant", "not_relevant", "uncertain"}
LANGUAGE_BUCKETS = ("eng_or_unknown", "fra", "nld")


@dataclass(frozen=True)
class ReviewDocument:
    candidate_document_id: str
    discovery_date: date
    source_common_name: str
    source_language: str | None
    title: str
    canonical_url: str
    sample_kind: str
    matched_token: str | None

    @property
    def language_bucket(self) -> str:
        if self.source_language == "fra":
            return "fra"
        if self.source_language == "nld":
            return "nld"
        return "eng_or_unknown"


@dataclass(frozen=True)
class ReviewSample:
    sample_run_id: str
    output_path: Path
    sample_size: int
    candidate_count: int
    negative_count: int
    population_counts: dict[str, int]
    sample_counts: dict[str, int]


def _hash_rank(seed: str, document_id: str) -> str:
    return hashlib.sha256(f"{seed}|{document_id}".encode("utf-8")).hexdigest()


def _language_balanced_sample(
    rows: list[ReviewDocument],
    target: int,
    seed: str,
    *,
    minimum_per_language: int = 25,
) -> list[ReviewDocument]:
    if target <= 0 or not rows:
        return []

    target = min(target, len(rows))
    groups = {
        bucket: [row for row in rows if row.language_bucket == bucket]
        for bucket in LANGUAGE_BUCKETS
    }
    active = [bucket for bucket, values in groups.items() if values]
    if not active:
        return []

    allocations = {bucket: 0 for bucket in LANGUAGE_BUCKETS}
    base = min(minimum_per_language, max(1, target // len(active)))
    for bucket in active:
        allocations[bucket] = min(base, len(groups[bucket]))

    allocated = sum(allocations.values())
    while allocated < target:
        candidates = [
            bucket
            for bucket in active
            if allocations[bucket] < len(groups[bucket])
        ]
        if not candidates:
            break

        # Fill remaining capacity proportionally, one deterministic slot at a time.
        bucket = max(
            candidates,
            key=lambda name: (
                (len(groups[name]) - allocations[name]) / len(groups[name]),
                len(groups[name]) - allocations[name],
                name,
            ),
        )
        allocations[bucket] += 1
        allocated += 1

    selected: list[ReviewDocument] = []
    for bucket in active:
        ranked = sorted(
            groups[bucket],
            key=lambda row: _hash_rank(f"{seed}|{bucket}", row.candidate_document_id),
        )
        selected.extend(ranked[: allocations[bucket]])

    return sorted(
        selected,
        key=lambda row: _hash_rank(seed, row.candidate_document_id),
    )


def _population_rows(
    settings: Settings,
    start: date,
    end: date,
    lexicon_version: str,
) -> list[ReviewDocument]:
    if end <= start:
        raise ValueError("end must be later than start")

    sql = """
        select distinct on (d.candidate_document_id)
            d.candidate_document_id,
            d.discovery_date,
            d.source_common_name,
            d.source_language,
            d.title,
            d.canonical_url,
            m.sample_kind,
            m.matched_token
        from staging.discovery_batch_document m
        join staging.discovery_batch b
          on b.batch_id = m.batch_id
        join staging.candidate_document d
          on d.candidate_document_id = m.candidate_document_id
        where b.lexicon_version = %s
          and b.batch_date >= %s
          and b.batch_date < %s
          and (
              m.sample_kind = 'candidate'
              or (
                  m.sample_kind = 'negative_control'
                  and (
                      d.source_language is null
                      or d.source_language in ('eng', 'fra', 'nld')
                  )
              )
          )
        order by d.candidate_document_id, b.batch_date desc
    """
    with connection(settings) as conn:
        rows = conn.execute(sql, (lexicon_version, start, end)).fetchall()

    return [
        ReviewDocument(
            candidate_document_id=str(row[0]),
            discovery_date=row[1],
            source_common_name=str(row[2] or ""),
            source_language=row[3],
            title=str(row[4] or ""),
            canonical_url=str(row[5] or ""),
            sample_kind=str(row[6]),
            matched_token=row[7],
        )
        for row in rows
    ]


def _counts(rows: Iterable[ReviewDocument]) -> dict[str, int]:
    counter = Counter(
        f"{row.sample_kind}:{row.language_bucket}"
        for row in rows
    )
    counter["candidate:total"] = sum(
        1 for row in rows if row.sample_kind == "candidate"
    )
    counter["negative_control:total"] = sum(
        1 for row in rows if row.sample_kind == "negative_control"
    )
    counter["all:total"] = sum(counter[key] for key in ("candidate:total", "negative_control:total"))
    return dict(sorted(counter.items()))


def _run_id(
    start: date,
    end: date,
    sample_size: int,
    candidate_target: int,
    seed: str,
) -> str:
    digest = hashlib.sha256(
        f"{start}|{end}|{sample_size}|{candidate_target}|{seed}|{CURRENT_LEXICON_VERSION}".encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    return f"semantic-v1-{start.isoformat()}-{end.isoformat()}-{digest}"


def create_review_sample(
    settings: Settings,
    start: date,
    end: date,
    *,
    sample_size: int = 500,
    candidate_fraction: float = 0.70,
    seed: str = "odo-semantic-v1",
    output_path: Path | None = None,
) -> ReviewSample:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not 0 < candidate_fraction < 1:
        raise ValueError("candidate_fraction must be between 0 and 1")

    population = _population_rows(
        settings,
        start,
        end,
        CURRENT_LEXICON_VERSION,
    )
    candidates = [row for row in population if row.sample_kind == "candidate"]
    negatives = [row for row in population if row.sample_kind == "negative_control"]

    candidate_target = min(round(sample_size * candidate_fraction), len(candidates))
    negative_target = min(sample_size - candidate_target, len(negatives))
    remaining = sample_size - candidate_target - negative_target

    if remaining > 0:
        extra_candidates = min(remaining, len(candidates) - candidate_target)
        candidate_target += extra_candidates
        remaining -= extra_candidates
    if remaining > 0:
        negative_target += min(remaining, len(negatives) - negative_target)

    actual_size = candidate_target + negative_target
    if actual_size == 0:
        raise RuntimeError("no discovery documents available for semantic sampling")

    selected_candidates = _language_balanced_sample(
        candidates,
        candidate_target,
        f"{seed}|candidate",
    )
    selected_negatives = _language_balanced_sample(
        negatives,
        negative_target,
        f"{seed}|negative",
    )
    selected = selected_candidates + selected_negatives
    selected = sorted(
        selected,
        key=lambda row: (
            row.sample_kind,
            _hash_rank(seed, row.candidate_document_id),
        ),
    )

    sample_run_id = _run_id(start, end, actual_size, candidate_target, seed)
    if output_path is None:
        output_path = (
            settings.data_dir
            / "silver"
            / "semantic-review"
            / SCHEMA_VERSION
            / f"{sample_run_id}.csv"
        )

    if output_path.exists():
        raise FileExistsError(
            f"review sample already exists: {output_path}; refusing to overwrite human-review data"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    population_counts = _counts(population)
    sample_counts = _counts(selected)

    with connection(settings) as conn, conn.transaction():
        conn.execute(
            """
            insert into staging.semantic_review_run(
                sample_run_id, schema_version, lexicon_version, start_date, end_date,
                sample_size, candidate_target, negative_target, seed,
                population_counts, sample_counts, output_path
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
            on conflict (sample_run_id) do nothing
            """,
            (
                sample_run_id,
                SCHEMA_VERSION,
                CURRENT_LEXICON_VERSION,
                start,
                end,
                actual_size,
                candidate_target,
                negative_target,
                seed,
                json.dumps(population_counts),
                json.dumps(sample_counts),
                str(output_path),
            ),
        )

        values = [
            (
                sample_run_id,
                row.candidate_document_id,
                row.sample_kind,
                row.language_bucket,
                rank,
            )
            for rank, row in enumerate(selected, start=1)
        ]
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into staging.semantic_gold_label(
                    sample_run_id, candidate_document_id, sample_kind,
                    language_bucket, sampling_rank
                ) values (%s,%s,%s,%s,%s)
                on conflict (sample_run_id, candidate_document_id) do nothing
                """,
                values,
            )

    fields = [
        "sample_run_id",
        "sampling_rank",
        "candidate_document_id",
        "sample_kind",
        "language_bucket",
        "discovery_date",
        "source_common_name",
        "source_language",
        "matched_token",
        "title",
        "canonical_url",
        "human_relevance",
        "reason_code",
        "evidence_text",
        "notes",
    ]
    by_id = {row.candidate_document_id: row for row in selected}
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, row in enumerate(selected, start=1):
            current = by_id[row.candidate_document_id]
            writer.writerow(
                {
                    "sample_run_id": sample_run_id,
                    "sampling_rank": rank,
                    "candidate_document_id": current.candidate_document_id,
                    "sample_kind": current.sample_kind,
                    "language_bucket": current.language_bucket,
                    "discovery_date": current.discovery_date.isoformat(),
                    "source_common_name": current.source_common_name,
                    "source_language": current.source_language or "",
                    "matched_token": current.matched_token or "",
                    "title": current.title,
                    "canonical_url": current.canonical_url,
                    "human_relevance": "",
                    "reason_code": "",
                    "evidence_text": "",
                    "notes": "",
                }
            )

    return ReviewSample(
        sample_run_id=sample_run_id,
        output_path=output_path,
        sample_size=actual_size,
        candidate_count=len(selected_candidates),
        negative_count=len(selected_negatives),
        population_counts=population_counts,
        sample_counts=sample_counts,
    )


def import_review_labels(
    settings: Settings,
    path: Path,
    *,
    reviewer_id: str,
) -> dict[str, int]:
    reviewed = 0
    skipped = 0
    invalid = 0

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    with connection(settings) as conn, conn.transaction():
        for row in rows:
            label = (row.get("human_relevance") or "").strip()
            if not label:
                skipped += 1
                continue
            if label not in VALID_LABELS:
                invalid += 1
                continue

            result = conn.execute(
                """
                update staging.semantic_gold_label
                set human_relevance = %s,
                    reason_code = nullif(%s, ''),
                    evidence_text = nullif(%s, ''),
                    notes = nullif(%s, ''),
                    reviewer_id = %s,
                    reviewed_at = now()
                where sample_run_id = %s
                  and candidate_document_id = %s
                """,
                (
                    label,
                    (row.get("reason_code") or "").strip(),
                    (row.get("evidence_text") or "").strip(),
                    (row.get("notes") or "").strip(),
                    reviewer_id,
                    (row.get("sample_run_id") or "").strip(),
                    (row.get("candidate_document_id") or "").strip(),
                ),
            )
            if result.rowcount != 1:
                invalid += 1
            else:
                reviewed += 1

    return {"reviewed": reviewed, "skipped": skipped, "invalid": invalid}


def review_stats(settings: Settings, sample_run_id: str) -> dict[str, object]:
    with connection(settings) as conn:
        run = conn.execute(
            """
            select sample_size, candidate_target, negative_target,
                   population_counts, sample_counts
            from staging.semantic_review_run
            where sample_run_id = %s
            """,
            (sample_run_id,),
        ).fetchone()
        if run is None:
            raise KeyError(f"unknown sample run: {sample_run_id}")

        counts = conn.execute(
            """
            select
                count(*) filter (where human_relevance is not null) as reviewed,
                count(*) filter (where human_relevance = 'relevant') as relevant,
                count(*) filter (where human_relevance = 'not_relevant') as not_relevant,
                count(*) filter (where human_relevance = 'uncertain') as uncertain
            from staging.semantic_gold_label
            where sample_run_id = %s
            """,
            (sample_run_id,),
        ).fetchone()

    return {
        "sample_run_id": sample_run_id,
        "sample_size": int(run[0]),
        "candidate_target": int(run[1]),
        "negative_target": int(run[2]),
        "population_counts": run[3],
        "sample_counts": run[4],
        "reviewed": int(counts[0]),
        "relevant": int(counts[1]),
        "not_relevant": int(counts[2]),
        "uncertain": int(counts[3]),
    }
