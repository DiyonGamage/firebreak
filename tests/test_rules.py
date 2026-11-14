from __future__ import annotations

import pytest

from firebreak.rules.engine import (
    assess,
    atmosphere_presets,
    gap_map,
    inventory,
    load_config,
    open_connection,
    retrieve_evidence,
)


@pytest.fixture()
def conn():
    connection = open_connection()
    yield connection
    connection.close()


def test_config_contract():
    config = load_config()
    assert "atmospheres" in config
    assert "evidence" in config
    assert "rules" in config
    assert len(config["rules"]) >= 10


def test_atmosphere_presets_reference():
    presets = atmosphere_presets()
    assert presets["iss_internal"]["o2_pct"] == 24.1
    assert presets["iss_internal"]["pressure_psia"] == 14.5
    assert presets["iss_airlock"]["o2_pct"] == 30.0
    assert presets["lunar_surface"]["o2_pct"] == 37.0


def test_material_similarity_same_class(conn):
    evidence = retrieve_evidence(conn, "PMMA", 22.2, 14.7)
    assert evidence
    assert evidence[0]["material_class"] == "PMMA"


def test_material_similarity_alias(conn):
    evidence = retrieve_evidence(conn, "polymethyl methacrylate", 22.2, 14.7)
    assert evidence


def test_retrieve_evidence_unknown_material(conn):
    assert retrieve_evidence(conn, "unobtainium composite", 22.0, 14.7) == []


def test_retrieve_respects_limit(conn):
    evidence = retrieve_evidence(conn, "PMMA", 22.2, 14.7, limit=5)
    assert 0 < len(evidence) <= 5


def test_assessment_shape(conn):
    result = assess(conn, "PMMA", 24.1, 14.5)
    assert {"query", "grade", "verdict", "evidence", "reasons", "gaps", "citations"} <= set(result)
    assert result["grade"] in {"A", "B", "C", "D"}
    assert result["boundary"].startswith("Screening support")


def test_pmma_iss_internal_grade(conn):
    result = assess(conn, "PMMA", 24.1, 14.5)
    assert result["grade"] == "B"
    assert result["verdict"] == "test_needed"
    assert result["outside_envelope"] is False


def test_pmma_exploration_is_outside(conn):
    result = assess(conn, "PMMA", 37.0, 8.2)
    assert result["outside_envelope"] is True
    assert result["grade"] in {"C", "D"}


def test_sibal_outcome_is_documented(conn):
    result = assess(conn, "SIBAL", 24.1, 14.5)
    outcomes = [item["outcome"] for item in result["evidence"] if item["outcome"]]
    assert "spread" in outcomes


def test_silicone_outcome_is_no_spread(conn):
    result = assess(conn, "Silicone", 22.1, 14.5)
    outcomes = {item["outcome"] for item in result["evidence"] if item["outcome"]}
    assert "no_spread" in outcomes


def test_no_a_grade_when_pressure_unknown(conn):
    result = assess(conn, "Silicone", 22.1, 14.5)
    assert result["grade"] != "A"
    assert any("pressure" in reason.lower() for reason in result["reasons"])


def test_kevlar_pbi_insufficient(conn):
    result = assess(conn, "Kevlar/PBI", 37.0, 8.2)
    assert result["grade"] == "D"
    assert result["verdict"] == "insufficient_evidence"


def test_sensitivity_variants(conn):
    result = assess(conn, "PMMA", 24.1, 14.5)
    assert len(result["sensitivity"]) == 5
    assert result["sensitivity"][0]["variant"] == "baseline"


def test_inventory_solid_total(conn):
    rows = inventory(conn)
    assert sum(row["tests"] for row in rows) == 140
    assert all(row["material_class"] != "Gas fuel" for row in rows)


def test_gap_map_contract(conn):
    rows = gap_map(conn, "iss_internal")
    assert rows
    assert {"material_class", "example_material", "grade", "top_gap"} <= set(rows[0])
    priorities = [row["priority"] for row in rows]
    assert priorities == sorted(priorities, reverse=True)


def test_gap_map_includes_absent_target(conn):
    rows = gap_map(conn, "iss_internal")
    absent = [row for row in rows if row.get("source") == "requested_target"]
    assert absent
    assert any(row["material_class"] == "Kevlar/PBI" for row in absent)
    assert all(row["grade"] == "D" and row["tests"] == 0 for row in absent)


def test_citations_are_source_linked(conn):
    result = assess(conn, "PMMA", 24.1, 14.5)
    assert result["citations"]
    assert all(citation["source_url"].startswith("https://") for citation in result["citations"])


def test_assessment_is_deterministic(conn):
    first = assess(conn, "PMMA", 24.1, 14.5)
    second = assess(conn, "PMMA", 24.1, 14.5)
    assert first["grade"] == second["grade"]
    assert first["confidence"] == second["confidence"]
    assert first["evidence"][0]["experiment_id"] == second["evidence"][0]["experiment_id"]
