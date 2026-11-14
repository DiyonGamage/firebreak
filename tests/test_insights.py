from __future__ import annotations

import pytest

from firebreak.rules.engine import open_connection
from firebreak.services.insights import build_dashboard


@pytest.fixture(scope="module")
def dashboard():
    connection = open_connection()
    try:
        yield build_dashboard(connection)
    finally:
        connection.close()


def test_dashboard_counts_match_corpus(dashboard):
    counts = dashboard["counts"]
    assert counts["total"] == 637
    assert counts["solid"] == 148
    assert counts["solid_outcomes"] == 13
    assert counts["one_g_outcomes"] == 2
    assert counts["anchors"] == 6
    assert counts["classes"] == 7


def test_dashboard_findings_are_evidence_based(dashboard):
    tags = [finding["tag"] for finding in dashboard["findings"]]
    assert tags == ["ANCHOR SCARCITY", "1-G CEILING", "EXPLORATION WALL"]
    assert dashboard["findings"][0]["value"] == "6 / 148"
    assert dashboard["findings"][2]["value"] == "0 / 8"


def test_ranked_cards_are_ordered_and_source_linked(dashboard):
    cards = dashboard["cards"]
    assert len(cards) == 6
    assert cards[0]["material"] == "PMMA"
    assert cards[0]["grade"] == "A"
    assert cards[0]["verdict"] == "high_risk"
    ranks = [card["decision_rank"] for card in cards]
    assert ranks == sorted(ranks, reverse=True)
    for card in cards:
        assert card["grade"] in {"A", "B", "C", "D"}
        assert card["interpretation"]
        assert card["change"]
        assert card["href"].startswith("/assess?")
        assert card["source_url"].startswith("https://")


def test_matrix_covers_materials_and_atmospheres(dashboard):
    matrix = dashboard["matrix"]
    assert len(matrix) == 8
    assert [cell["grade"] for cell in matrix[0]["cells"]] == ["A", "C", "C"]
    assert [cell["grade"] for cell in matrix[-1]["cells"]] == ["D", "D", "D"]
    assert len(dashboard["matrix_atmospheres"]) == 3
    for row in matrix:
        assert len(row["cells"]) == 3
        assert all(cell["href"].startswith("/assess?") for cell in row["cells"])


def test_dashboard_explains_the_method(dashboard):
    assert [item["grade"] for item in dashboard["grade_legend"]] == ["A", "B", "C", "D"]
    assert len(dashboard["pipeline"]) == 5
    assert len(dashboard["cases"]) == 5
    assert dashboard["boundary"].startswith("Screening support")
    assert "never a model" in dashboard["si_note"]
