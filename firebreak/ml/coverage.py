from __future__ import annotations

import sqlite3
from typing import Any

from firebreak.data.psi import material_class


def _condition_penalty(
    o2_pct: float,
    pressure_psia: float,
    flow_velocity_cm_s: float | None,
    row: sqlite3.Row,
) -> tuple[float, dict[str, Any]]:
    o2_gap = abs(o2_pct - row["o2_initial_pct"]) if row["o2_initial_pct"] is not None else 10.0
    pressure_value = row["pressure_kpa"] / 6.894757 if row["pressure_kpa"] else None
    pressure_gap = abs(pressure_psia - pressure_value) if pressure_value is not None else None
    flow_value = row["flow_velocity_cm_s"]
    flow_gap = (
        abs(flow_velocity_cm_s - flow_value)
        if flow_velocity_cm_s is not None and flow_value is not None
        else None
    )
    penalty = o2_gap / 10.0
    if pressure_gap is not None:
        penalty += pressure_gap / 5.0
    else:
        penalty += 0.15
    if flow_gap is not None:
        penalty += flow_gap / 20.0
    else:
        penalty += 0.10
    detail = {
        "o2_gap_pct": round(o2_gap, 2) if row["o2_initial_pct"] is not None else None,
        "pressure_gap_psia": round(pressure_gap, 2) if pressure_gap is not None else None,
        "flow_gap_cm_s": round(flow_gap, 2) if flow_gap is not None else None,
    }
    return min(1.0, penalty), detail


def assess_coverage(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    pressure_psia: float,
    flow_velocity_cm_s: float | None = None,
) -> dict[str, Any]:
    query_class = material_class(material)
    rows = connection.execute(
        """
        SELECT experiment_id, dataset, material, material_class, o2_initial_pct,
               pressure_kpa, flow_velocity_cm_s, flow_direction, gravity, outcome,
               spread_rate_mm_s, source_url
        FROM experiments
        WHERE material_class != 'Gas fuel' AND material != 'unspecified'
        """
    ).fetchall()
    compatible = [
        row
        for row in rows
        if query_class != "Other"
        and (
            query_class == row["material_class"]
            or query_class in row["material_class"]
            or row["material_class"] in query_class
        )
    ]
    if not compatible:
        return {
            "material": material,
            "material_class": query_class,
            "coverage_score": 0.0,
            "label": "no_material_evidence",
            "evidence_count": 0,
            "outcome_count": 0,
            "nearest": [],
            "gaps": ["No microgravity or 1-g evidence for this material class."],
            "caveat": "Coverage is descriptive; absence of evidence is not evidence of safety.",
        }

    scored = []
    for row in compatible:
        penalty, detail = _condition_penalty(o2_pct, pressure_psia, flow_velocity_cm_s, row)
        scored.append((penalty, row, detail))
    scored.sort(key=lambda item: item[0])
    best_penalty, best_row, best_detail = scored[0]
    coverage_score = round(max(0.0, 1.0 - best_penalty), 3)
    if coverage_score >= 0.5:
        label = "in_distribution"
    elif coverage_score >= 0.2:
        label = "near_envelope"
    else:
        label = "out_of_distribution"

    nearest = []
    for penalty, row, detail in scored[:3]:
        nearest.append(
            {
                "experiment_id": row["experiment_id"],
                "dataset": row["dataset"],
                "material": row["material"],
                "o2_initial_pct": row["o2_initial_pct"],
                "pressure_psia": round(row["pressure_kpa"] / 6.894757, 2)
                if row["pressure_kpa"]
                else None,
                "flow_velocity_cm_s": row["flow_velocity_cm_s"],
                "outcome": row["outcome"],
                "penalty": round(penalty, 3),
                "source_url": row["source_url"],
                **detail,
            }
        )

    o2_values = [row["o2_initial_pct"] for row in compatible if row["o2_initial_pct"] is not None]
    pressure_values = [row["pressure_kpa"] / 6.894757 for row in compatible if row["pressure_kpa"]]
    gaps = []
    if o2_values and o2_pct > max(o2_values) + 2.0:
        gaps.append(f"Query O2 is {round(o2_pct - max(o2_values), 1)} points above tested evidence.")
    if pressure_values and pressure_psia < min(pressure_values) - 1.5:
        gaps.append("Query pressure is below the tested pressure envelope.")
    if not pressure_values:
        gaps.append("Pressure is not reported in the matched evidence.")
    if not any(row["gravity"] == "microgravity" for row in compatible):
        gaps.append("No microgravity evidence in the matched material class; 1-g evidence only.")
    if not any(row["flow_direction"] for row in compatible):
        gaps.append("Flow direction is not reported in the matched evidence.")
    if not gaps:
        gaps.append("No condition-level gap detected; configuration-level gaps may remain.")

    return {
        "material": material,
        "material_class": query_class,
        "coverage_score": coverage_score,
        "label": label,
        "evidence_count": len(compatible),
        "outcome_count": sum(1 for row in compatible if row["outcome"]),
        "nearest": nearest,
        "gaps": gaps,
        "caveat": "Coverage is descriptive; absence of evidence is not evidence of safety.",
    }


def evaluate_coverage(connection: sqlite3.Connection) -> dict[str, Any]:
    cases = [
        ("PMMA", 24.1, 14.5, "in_distribution"),
        ("PMMA", 37.0, 8.2, "out_of_distribution"),
        ("Silicone", 22.1, 14.5, "in_distribution"),
        ("Kevlar/PBI", 37.0, 8.2, "in_distribution"),
        ("Vectran fabric", 24.1, 14.5, "no_material_evidence"),
    ]
    results = []
    correct = 0
    for material, o2_pct, pressure_psia, expected in cases:
        result = assess_coverage(connection, material, o2_pct, pressure_psia)
        ok = result["label"] == expected
        correct += int(ok)
        results.append(
            {
                "material": material,
                "o2_pct": o2_pct,
                "pressure_psia": pressure_psia,
                "expected": expected,
                "actual": result["label"],
                "score": result["coverage_score"],
                "passed": ok,
            }
        )
    return {
        "cases": results,
        "accuracy": round(correct / len(cases), 3),
        "gate": {"accuracy_min": 1.0, "passed": correct == len(cases)},
    }
