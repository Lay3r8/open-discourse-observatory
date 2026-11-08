from odo.import_pilot import normalize_incident_row


def test_normalize_incident_row_booleans_and_year():
    row = {
        "incident_id": "T001",
        "year": "2026",
        "include_left_right": "1",
        "violence": "0",
    }
    normalized = normalize_incident_row(row)
    assert normalized["incident_id"] == "T001"
    assert normalized["year"] == 2026
    assert normalized["include_left_right"] is True
    assert normalized["violence"] is False
