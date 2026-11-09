from datetime import date

from odo.discovery import _frame, _load_lexicon, canonicalize_url, normalize_title


def test_normalize_title_decodes_html_and_unicode():
    decoded, normalized = normalize_title(
        "  D&#xE9;bat   annul&#xE9; apr&#xE8;s pression  "
    )
    assert decoded == "Débat annulé après pression"
    assert normalized == "débat annulé après pression"


def test_canonicalize_url_removes_tracking_and_fragment():
    url = (
        "https://Example.COM:443/news/item/?utm_source=x&b=2&a=1&fbclid=abc#section"
    )
    assert canonicalize_url(url) == "https://example.com/news/item?a=1&b=2"


def test_canonicalize_url_preserves_non_tracking_query():
    assert canonicalize_url("https://example.com/x?id=42") == "https://example.com/x?id=42"


def test_date_object_is_stable_for_discovery_identity():
    assert date.fromisoformat("2025-01-01").isoformat() == "2025-01-01"



def test_frame_infers_nullable_string_beyond_default_sample():
    rows = [
        {"title": f"row-{index}", "matched_token": None}
        for index in range(150)
    ]
    rows.append({"title": "political cancellation", "matched_token": "annul"})

    frame = _frame(rows, ["title", "matched_token"])

    assert frame.height == 151
    assert frame["matched_token"][-1] == "annul"



def test_current_lexicon_uses_real_word_boundaries():
    lexicon = _load_lexicon()

    assert lexicon["version"] == "v2"
    assert lexicon["english"].startswith(r"\b(")
    assert lexicon["dutch"].startswith(r"\b(")
    assert r"\\b" not in lexicon["english"]
    assert r"\\b" not in lexicon["dutch"]
