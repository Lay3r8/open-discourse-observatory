from datetime import date

from odo.review import (
    ReviewItem,
    _largest_remainder_allocation,
    _select_stratified_prefix,
)


def _item(index: int, kind: str, language: str) -> ReviewItem:
    return ReviewItem(
        candidate_document_id=f"doc-{index}",
        discovery_date=date(2025, 1, 1),
        source_common_name="example.com",
        source_language=None if language == "eng_or_unknown" else language,
        title=f"title {index}",
        canonical_url=f"https://example.com/{index}",
        sample_kind=kind,
        language_bucket=language,
        human_relevance=None,
        reason_code=None,
        evidence_text=None,
        notes=None,
        reviewer_id=None,
        reviewed_at=None,
    )


def test_largest_remainder_allocation_hits_target():
    allocation = _largest_remainder_allocation(
        {"eng": 249, "fra": 76, "nld": 25},
        105,
    )
    assert sum(allocation.values()) == 105
    assert allocation["eng"] > allocation["fra"] > allocation["nld"]


def test_review_prefix_preserves_candidate_negative_mix_and_is_deterministic():
    rows = [
        *[_item(i, "candidate", "eng_or_unknown") for i in range(249)],
        *[_item(300 + i, "candidate", "fra") for i in range(76)],
        *[_item(400 + i, "candidate", "nld") for i in range(25)],
        *[_item(500 + i, "negative_control", "eng_or_unknown") for i in range(109)],
        *[_item(700 + i, "negative_control", "fra") for i in range(25)],
        *[_item(800 + i, "negative_control", "nld") for i in range(16)],
    ]

    first = _select_stratified_prefix(rows, 150, "seed")
    second = _select_stratified_prefix(rows, 150, "seed")

    assert [x.candidate_document_id for x in first] == [
        x.candidate_document_id for x in second
    ]
    assert len(first) == 150
    assert sum(x.sample_kind == "candidate" for x in first) == 105
    assert sum(x.sample_kind == "negative_control" for x in first) == 45
    assert {x.language_bucket for x in first} == {"eng_or_unknown", "fra", "nld"}
