from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from odo.config import Settings
from odo.db import connection

VALID_LABELS = {"relevant", "not_relevant", "uncertain"}

NON_RELEVANT_REASONS: tuple[tuple[str, str], ...] = (
    ("political_noncoercive", "Politique, mais non coercitif"),
    ("weather_or_safety", "Météo / sécurité"),
    ("ordinary_crime", "Crime ordinaire"),
    ("sport_or_entertainment", "Sport / divertissement"),
    ("routine_regulation", "Réglementation courante"),
    ("commercial_or_nonpolitical_hr", "Commercial / RH non politique"),
    ("infrastructure_or_transport", "Transport / infrastructure"),
    ("nonpolitical_legal_case", "Affaire juridique non politique"),
    ("other_nonpolitical", "Autre non politique"),
)


@dataclass(frozen=True)
class ReviewItem:
    candidate_document_id: str
    discovery_date: date
    source_common_name: str
    source_language: str | None
    title: str
    canonical_url: str
    sample_kind: str
    language_bucket: str
    human_relevance: str | None
    reason_code: str | None
    evidence_text: str | None
    notes: str | None
    reviewer_id: str | None
    reviewed_at: object | None


@dataclass(frozen=True)
class ReviewQueue:
    run_id: str
    sample_size: int
    target: int
    items: tuple[ReviewItem, ...]

    @property
    def reviewed(self) -> int:
        return sum(item.human_relevance is not None for item in self.items)

    @property
    def remaining(self) -> int:
        return self.target - self.reviewed


def _rank(seed: str, item_id: str) -> str:
    return hashlib.sha256(f"{seed}|{item_id}".encode("utf-8")).hexdigest()


def _largest_remainder_allocation(
    sizes: dict[str, int],
    target: int,
) -> dict[str, int]:
    available = sum(sizes.values())
    if target <= 0 or available <= 0:
        return {key: 0 for key in sizes}

    target = min(target, available)
    raw = {
        key: (target * size / available)
        for key, size in sizes.items()
    }
    allocated = {
        key: min(size, int(raw[key]))
        for key, size in sizes.items()
    }
    remaining = target - sum(allocated.values())

    order = sorted(
        sizes,
        key=lambda key: (
            raw[key] - int(raw[key]),
            sizes[key] - allocated[key],
            key,
        ),
        reverse=True,
    )
    while remaining > 0:
        progressed = False
        for key in order:
            if allocated[key] < sizes[key]:
                allocated[key] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break
    return allocated


def _select_stratified_prefix(
    items: Iterable[ReviewItem],
    target: int,
    seed: str,
) -> tuple[ReviewItem, ...]:
    rows = list(items)
    if target >= len(rows):
        return tuple(sorted(rows, key=lambda item: _rank(seed, item.candidate_document_id)))

    by_kind: dict[str, list[ReviewItem]] = {}
    for item in rows:
        by_kind.setdefault(item.sample_kind, []).append(item)

    kind_alloc = _largest_remainder_allocation(
        {kind: len(values) for kind, values in by_kind.items()},
        target,
    )

    selected: list[ReviewItem] = []
    for kind, kind_rows in by_kind.items():
        by_language: dict[str, list[ReviewItem]] = {}
        for item in kind_rows:
            by_language.setdefault(item.language_bucket, []).append(item)

        language_alloc = _largest_remainder_allocation(
            {language: len(values) for language, values in by_language.items()},
            kind_alloc[kind],
        )
        for language, language_rows in by_language.items():
            ranked = sorted(
                language_rows,
                key=lambda item: _rank(
                    f"{seed}|{kind}|{language}",
                    item.candidate_document_id,
                ),
            )
            selected.extend(ranked[: language_alloc[language]])

    # Final order deliberately ignores sample_kind/language so the reviewer is blind
    # to the source stratum while every prefix remains a deterministic sample.
    return tuple(
        sorted(
            selected,
            key=lambda item: _rank(f"{seed}|blind", item.candidate_document_id),
        )
    )


def load_review_queue(
    settings: Settings,
    run_id: str,
    *,
    target: int = 150,
) -> ReviewQueue:
    if target <= 0:
        raise ValueError("target must be positive")

    with connection(settings) as conn:
        run = conn.execute(
            """
            select sample_size
            from staging.semantic_review_run
            where sample_run_id = %s
            """,
            (run_id,),
        ).fetchone()
        if run is None:
            raise KeyError(f"unknown sample run: {run_id}")

        rows = conn.execute(
            """
            select
                g.candidate_document_id,
                d.discovery_date,
                d.source_common_name,
                d.source_language,
                d.title,
                d.canonical_url,
                g.sample_kind,
                g.language_bucket,
                g.human_relevance,
                g.reason_code,
                g.evidence_text,
                g.notes,
                g.reviewer_id,
                g.reviewed_at
            from staging.semantic_gold_label g
            join staging.candidate_document d
              on d.candidate_document_id = g.candidate_document_id
            where g.sample_run_id = %s
            """,
            (run_id,),
        ).fetchall()

    items = [
        ReviewItem(
            candidate_document_id=str(row[0]),
            discovery_date=row[1],
            source_common_name=str(row[2] or ""),
            source_language=row[3],
            title=str(row[4] or ""),
            canonical_url=str(row[5] or ""),
            sample_kind=str(row[6]),
            language_bucket=str(row[7]),
            human_relevance=row[8],
            reason_code=row[9],
            evidence_text=row[10],
            notes=row[11],
            reviewer_id=row[12],
            reviewed_at=row[13],
        )
        for row in rows
    ]

    effective_target = min(target, int(run[0]), len(items))
    selected = _select_stratified_prefix(
        items,
        effective_target,
        f"{run_id}|target={effective_target}",
    )
    return ReviewQueue(
        run_id=run_id,
        sample_size=int(run[0]),
        target=effective_target,
        items=selected,
    )


def save_review(
    settings: Settings,
    run_id: str,
    candidate_document_id: str,
    *,
    label: str,
    reviewer_id: str,
    reason_code: str | None = None,
    evidence_text: str | None = None,
    notes: str | None = None,
) -> None:
    if label not in VALID_LABELS:
        raise ValueError(f"invalid label: {label}")
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")

    reason_code = (reason_code or "").strip() or None
    evidence_text = (evidence_text or "").strip() or None
    notes = (notes or "").strip() or None

    if label == "not_relevant" and not reason_code:
        raise ValueError("reason_code is required for not_relevant")

    with connection(settings) as conn, conn.transaction():
        previous = conn.execute(
            """
            select human_relevance, reason_code, evidence_text, notes, reviewer_id, reviewed_at
            from staging.semantic_gold_label
            where sample_run_id = %s
              and candidate_document_id = %s
            for update
            """,
            (run_id, candidate_document_id),
        ).fetchone()
        if previous is None:
            raise KeyError("review item not found")

        conn.execute(
            """
            insert into staging.semantic_gold_label_audit(
                sample_run_id,
                candidate_document_id,
                previous_relevance,
                previous_reason_code,
                previous_evidence_text,
                previous_notes,
                previous_reviewer_id,
                previous_reviewed_at,
                new_relevance,
                new_reason_code,
                new_evidence_text,
                new_notes,
                new_reviewer_id
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                run_id,
                candidate_document_id,
                previous[0],
                previous[1],
                previous[2],
                previous[3],
                previous[4],
                previous[5],
                label,
                reason_code,
                evidence_text,
                notes,
                reviewer_id.strip(),
            ),
        )

        conn.execute(
            """
            update staging.semantic_gold_label
            set human_relevance = %s,
                reason_code = %s,
                evidence_text = %s,
                notes = %s,
                reviewer_id = %s,
                reviewed_at = now()
            where sample_run_id = %s
              and candidate_document_id = %s
            """,
            (
                label,
                reason_code,
                evidence_text,
                notes,
                reviewer_id.strip(),
                run_id,
                candidate_document_id,
            ),
        )


def undo_last_review(
    settings: Settings,
    run_id: str,
    *,
    reviewer_id: str,
) -> str | None:
    with connection(settings) as conn, conn.transaction():
        audit = conn.execute(
            """
            select
                audit_id,
                candidate_document_id,
                previous_relevance,
                previous_reason_code,
                previous_evidence_text,
                previous_notes,
                previous_reviewer_id,
                previous_reviewed_at
            from staging.semantic_gold_label_audit
            where sample_run_id = %s
              and new_reviewer_id = %s
              and undone_at is null
            order by changed_at desc, audit_id desc
            limit 1
            for update
            """,
            (run_id, reviewer_id),
        ).fetchone()
        if audit is None:
            return None

        conn.execute(
            """
            update staging.semantic_gold_label
            set human_relevance = %s,
                reason_code = %s,
                evidence_text = %s,
                notes = %s,
                reviewer_id = %s,
                reviewed_at = %s
            where sample_run_id = %s
              and candidate_document_id = %s
            """,
            (
                audit[2],
                audit[3],
                audit[4],
                audit[5],
                audit[6],
                audit[7],
                run_id,
                audit[1],
            ),
        )
        conn.execute(
            """
            update staging.semantic_gold_label_audit
            set undone_at = now()
            where audit_id = %s
            """,
            (audit[0],),
        )
        return str(audit[1])


def label_counts(queue: ReviewQueue) -> dict[str, int]:
    counts = {
        "relevant": 0,
        "not_relevant": 0,
        "uncertain": 0,
    }
    for item in queue.items:
        if item.human_relevance in counts:
            counts[item.human_relevance] += 1
    return counts



def previous_reviewed_item(
    items: tuple[ReviewItem, ...],
    current_document_id: str | None = None,
) -> ReviewItem | None:
    reviewed = sorted(
        (item for item in items if item.reviewed_at is not None),
        key=lambda item: item.reviewed_at,
        reverse=True,
    )
    if not reviewed:
        return None

    if current_document_id is None:
        return reviewed[0]

    for index, item in enumerate(reviewed):
        if item.candidate_document_id == current_document_id:
            next_index = index + 1
            return reviewed[next_index] if next_index < len(reviewed) else None

    return reviewed[0]
