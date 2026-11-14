from __future__ import annotations

import pytest

from firebreak.ml.coverage import assess_coverage, evaluate_coverage
from firebreak.ml.evidence import evaluate_matcher, match_evidence, match_materials
from firebreak.ml.severity import predict_severity, train_and_evaluate
from firebreak.rules.engine import open_connection


@pytest.fixture()
def conn():
    connection = open_connection()
    yield connection
    connection.close()


def test_matcher_gate(conn):
    result = evaluate_matcher(conn)
    assert result["recall_at_3"] >= 0.8
    assert result["false_match_rate"] <= 0.2
    assert result["gate"]["passed"] is True


def test_matcher_rejects_unknown(conn):
    assert match_materials(conn, "polyethylene film") == []
    assert match_materials(conn, "unobtainium composite") == []


def test_matcher_alias(conn):
    results = match_materials(conn, "polymethyl methacrylate", top_k=3)
    assert results
    assert results[0]["material_class"] == "PMMA"


def test_match_evidence_is_linked(conn):
    results = match_evidence(conn, "SIBAL", limit=3)
    assert results
    assert all(item["source_url"].startswith("https://") for item in results)


def test_coverage_gate(conn):
    result = evaluate_coverage(conn)
    assert result["accuracy"] == 1.0
    assert result["gate"]["passed"] is True


def test_coverage_out_of_distribution(conn):
    result = assess_coverage(conn, "PMMA", 37.0, 8.2)
    assert result["label"] == "out_of_distribution"
    assert result["coverage_score"] < 0.2


def test_coverage_unknown_material(conn):
    result = assess_coverage(conn, "Vectran fabric", 37.0, 8.2)
    assert result["label"] == "no_material_evidence"


def test_coverage_kevlar_1g_only(conn):
    result = assess_coverage(conn, "Kevlar/PBI", 37.0, 8.2)
    assert result["label"] == "in_distribution"
    assert any("No microgravity evidence" in gap for gap in result["gaps"])


def test_severity_gate(conn):
    payload = train_and_evaluate(conn)
    metrics = payload["metrics"]
    assert metrics["n"] == 121
    assert metrics["auc"] >= 0.75
    assert metrics["auc"] > metrics["o2_only_auc"]
    assert metrics["gate"]["passed"] is True


def test_severity_prediction(conn):
    result = predict_severity(conn, "PMMA", 22.2, thickness_mm=0.1)
    assert result["enabled"] is True
    assert 0.0 <= result["probability_delta_co2_gt_0.5"] <= 1.0
    assert result["band"] in {"low", "high"}


def test_severity_unseen_material(conn):
    result = predict_severity(conn, "Kevlar/PBI", 37.0)
    assert result["enabled"] is False


def test_severity_support_is_bounded(conn):
    metrics = train_and_evaluate(conn)["metrics"]
    assert metrics["min_class_support"] == 10
    assert metrics["supported_classes"] == ["PMMA", "SIBAL"]
    assert "Nomex" in metrics["excluded_classes"]
    assert metrics["o2_support"] == [13.6, 22.2]


def test_severity_abstains_below_class_support(conn):
    result = predict_severity(conn, "Nomex", 22.2)
    assert result["enabled"] is False
    assert result["status"] == "low_support"


def test_severity_abstains_outside_o2_support(conn):
    result = predict_severity(conn, "PMMA", 24.1)
    assert result["enabled"] is False
    assert result["status"] == "outside_support"
    assert result["nearest_supported_o2"] == 22.2


def test_severity_conformal_is_explicit(conn):
    resolved = predict_severity(conn, "PMMA", 22.2)
    assert resolved["status"] == "resolved"
    assert resolved["conformal"]["labels"] == [resolved["band"]]
    unresolved = predict_severity(conn, "PMMA", 16.0, thickness_mm=2.0)
    assert unresolved["status"] == "indeterminate"
    assert unresolved["conformal"]["labels"] == ["low", "high"]


def test_severity_is_monotonic_in_o2(conn):
    probabilities = [
        predict_severity(conn, "PMMA", o2, thickness_mm=2.0)[
            "probability_delta_co2_gt_0.5"
        ]
        for o2 in (14.0, 16.0, 18.0, 20.0, 22.2)
    ]
    assert probabilities == sorted(probabilities)
    metrics = train_and_evaluate(conn)["metrics"]
    assert metrics["monotonic"]["violations"] == 0
    assert metrics["unconstrained"]["monotonicity_violations"] > 0


def test_severity_conformal_evaluation(conn):
    conformal = train_and_evaluate(conn)["metrics"]["conformal"]
    assert conformal["target_coverage"] == 0.8
    assert conformal["coverage"] >= 0.8
    assert conformal["evaluated_rows"] > 0
    assert 0.0 <= conformal["abstention_rate"] < 1.0
