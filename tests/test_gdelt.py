from pathlib import Path

from odo.gdelt import GDELT_EVENT_COLUMNS, parse_export_tsv, sha256_file


def test_parse_gdelt_fixture():
    path = Path(__file__).parent / "fixtures" / "gdelt_sample.tsv"
    rows = parse_export_tsv(path)
    assert len(rows) == 2
    assert rows[0]["GLOBALEVENTID"] == "1000000001"
    assert rows[0]["SOURCEURL"] == "https://example.test/article-1"
    assert set(rows[0]) == set(GDELT_EVENT_COLUMNS)


def test_sha256_is_stable():
    path = Path(__file__).parent / "fixtures" / "gdelt_sample.tsv"
    assert len(sha256_file(path)) == 64
