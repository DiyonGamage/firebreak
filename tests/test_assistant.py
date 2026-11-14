from __future__ import annotations

from firebreak.assistant.agent import ask, run_fallback
from firebreak.assistant.tools import (
    assess_material,
    coverage_check,
    find_gaps,
    resolve_atmosphere,
    severity_estimate,
    tool_schemas,
)


def test_atmosphere_alias_resolution():
    assert resolve_atmosphere("ISS internal") == "iss_internal"
    assert resolve_atmosphere("ISS airlock") == "iss_airlock"
    assert resolve_atmosphere("lunar surface") == "lunar_surface"
    assert resolve_atmosphere("Gateway") == "gateway"


def test_assess_tool_contract():
    result = assess_material("SIBAL", "ISS internal")
    assert result["grade"] in {"A", "B", "C", "D"}
    assert result["query"]["o2_pct"] == 24.1
    assert result["top_evidence"]


def test_coverage_tool_airlock():
    result = coverage_check("Silicone", "ISS airlock")
    assert result["atmosphere"] == "iss_airlock"
    assert result["label"] in {"in_distribution", "near_envelope", "out_of_distribution"}


def test_gap_tool_contract():
    result = find_gaps("Gateway", limit=3)
    assert result["atmosphere"] == "gateway"
    assert 0 < len(result["gaps"]) <= 3


def test_severity_tool_defaults():
    result = severity_estimate("PMMA")
    assert "enabled" in result


def test_severity_tool_abstains_outside_support():
    result = severity_estimate("PMMA", o2_pct=24.1)
    assert result["enabled"] is False
    assert result["status"] == "outside_support"
    assert result["nearest_supported_o2"] == 22.2


def test_tool_schemas():
    names = {schema["name"] for schema in tool_schemas()}
    assert {"assess_material", "retrieve_evidence", "coverage_check", "severity_estimate", "find_gaps"} <= names
    severity = next(schema for schema in tool_schemas() if schema["name"] == "severity_estimate")
    assert severity["parameters"]["required"] == ["material"]


def test_fallback_assessment():
    result = ask("Assess SIBAL at ISS internal")
    assert result["engine"] == "fallback"
    assert "grade" in result["answer"].lower() or "grade B" in result["answer"]
    assert result["tool"] == "assess_material"


def test_fallback_clarification():
    result = run_fallback("What is safe?")
    assert result.get("needs_clarification") is True


def test_fallback_gap_query():
    result = run_fallback("Find evidence gaps for Gateway")
    assert result["tool"] == "find_gaps"
    assert "Gateway" in result["answer"]
