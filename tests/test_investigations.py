from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firebreak.rules.engine import load_config, open_connection
from firebreak.services.court import build_court
from firebreak.services.investigations import build_investigations, catalog


@pytest.fixture(scope="module")
def connection():
    conn = open_connection()
    yield conn
    conn.close()


def test_catalog_covers_every_named_investigation(connection):
    rows = catalog(connection)
    names = {row["name"] for row in rows}
    for expected in (
        "BASS",
        "BASS-II",
        "Saffire-I",
        "Saffire-II",
        "Saffire-III",
        "ACME-BRE",
        "SPICE",
        "SAME",
        "SAME-R",
        "FLEX",
        "SLICE",
    ):
        assert expected in names
    assert len(rows) == 11


def test_characterisation_records_never_enter_grading(connection):
    aux_datasets = ("BASS", "SAME", "SAME-R", "FLEX", "FLEX-2", "SLICE")
    placeholders = ",".join("?" for _ in aux_datasets)
    assert (
        connection.execute(
            f"SELECT count(*) FROM experiments WHERE dataset IN ({placeholders})", aux_datasets
        ).fetchone()[0]
        == 0
    )
    for row in catalog(connection):
        if row["experiments"] == 0:
            assert row["outcomes"] == 0
            assert row["o2"] is None
            assert row["kinds"], row["name"]


def test_extracted_counts_are_real(connection):
    payload = build_investigations(connection, "iss_internal", load_config())
    by_name = {row["name"]: row for row in payload["investigations"]}
    assert by_name["BASS-II"]["records"] == 135
    assert by_name["SPICE"]["records"] == 469
    assert by_name["SAME-R"]["records"] == 109
    assert by_name["FLEX"]["records"] == 282
    assert by_name["BASS"]["records"] == 122
    assert payload["totals"]["aux"] == 533
    assert payload["totals"]["all_records"] == 1170
    assert payload["totals"]["outside_catalog"] == 2


def test_three_pillars_are_reported(connection):
    payload = build_investigations(connection, "iss_internal", load_config())
    pillars = {row["pillar"]: row for row in payload["pillars"]}
    assert pillars["Prevention"]["experiments"] > 0
    assert pillars["Detection"]["experiments"] == 0
    assert pillars["Detection"]["records"] == 117
    assert pillars["Suppression"]["experiments"] == 0
    assert pillars["Suppression"]["records"] == 282
    assert all(row["extracted"] == row["investigations"] for row in pillars.values())


def test_lunar_surface_has_no_anchored_class(connection):
    payload = build_investigations(connection, "lunar_surface", load_config())
    lunar = {row["key"]: row for row in payload["readiness"]}["lunar_surface"]
    assert lunar["anchored"] == 0
    assert lunar["provisional"] == 0
    assert lunar["gap"] == lunar["classes"]


def test_spacesuit_is_not_graded(connection):
    payload = build_investigations(connection, "iss_internal", load_config())
    suit = {row["key"]: row for row in payload["readiness"]}["suit"]
    assert suit["classes"] == 0
    assert suit["anchored"] == 0
    assert "inventing pressure" in suit["note"]


def test_pmma_contradiction_margin():
    payload = build_investigations(open_connection(), "iss_internal", load_config())
    pmma = next(item for item in payload["contradictions"] if item["material"] == "PMMA")
    assert pmma["margin_pp"] == 2.4
    assert pmma["one_g"]["condition"] == "1-g, 16% O2"
    assert pmma["microgravity"]["condition"] == "microgravity, 13.6% O2"


def test_court_has_four_rule_driven_voices():
    from firebreak.services.dossier import build_dossier

    connection = open_connection()
    try:
        result = build_dossier(connection, "PMMA", 24.1, 14.5)
    finally:
        connection.close()
    court = build_court(result, "ISS cabin")
    assert [voice["role"] for voice in court["voices"]] == [
        "Curator",
        "Critic",
        "Safety Officer",
        "Experimentalist",
    ]
    assert court["verdict"]["grade"] == result["grade"]
    assert "No language model" in court["note"]
    assert all(voice["statement"] for voice in court["voices"])
