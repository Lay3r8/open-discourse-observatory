from datetime import date

from odo.semantic import ReviewDocument, _language_balanced_sample


def _row(index: int, language: str | None, kind: str = "candidate") -> ReviewDocument:
    return ReviewDocument(
        candidate_document_id=f"doc-{index}",
        discovery_date=date(2025, 1, 1),
        source_common_name="example.com",
        source_language=language,
        title=f"title {index}",
        canonical_url=f"https://example.com/{index}",
        sample_kind=kind,
        matched_token="banned" if kind == "candidate" else None,
    )


def test_semantic_sample_is_deterministic():
    rows = [_row(i, "eng") for i in range(100)]
    first = _language_balanced_sample(rows, 25, "seed")
    second = _language_balanced_sample(rows, 25, "seed")
    assert [x.candidate_document_id for x in first] == [
        x.candidate_document_id for x in second
    ]


def test_semantic_sample_keeps_small_language_stratum():
    rows = (
        [_row(i, "eng") for i in range(100)]
        + [_row(200 + i, "fra") for i in range(40)]
        + [_row(300 + i, "nld") for i in range(5)]
    )
    sample = _language_balanced_sample(rows, 50, "seed", minimum_per_language=10)
    languages = [row.language_bucket for row in sample]
    assert "fra" in languages
    assert languages.count("nld") == 5
