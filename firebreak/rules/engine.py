from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from firebreak.config import DB_PATH, ROOT
from firebreak.data.psi import material_class

CONFIG_PATH = ROOT / "firebreak" / "rules" / "rules.yaml"
PSI_TO_KPA = 6.894757

_STOP = {
    "the",
    "and",
    "with",
    "for",
    "sample",
    "film",
    "rod",
    "wide",
    "thick",
    "clear",
    "black",
    "data",
    "test",
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def atmosphere_presets(config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    cfg = config or load_config()
    return cfg["atmospheres"]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in _STOP
    }


def _material_similarity(query: str, candidate: str) -> float:
    query_class = material_class(query)
    candidate_class = material_class(candidate)
    if query_class == "Other" and candidate_class != "Other":
        return 0.0
    if query_class != "Other" and query_class != candidate_class:
        if query_class not in candidate_class and candidate_class not in query_class:
            return 0.0
    if query_class != "Other" and query_class == candidate_class:
        base = 1.0
    elif query_class != "Other" and (query_class in candidate_class or candidate_class in query_class):
        base = 0.75
    else:
        base = 0.0
    query_tokens = _tokens(query)
    candidate_tokens = _tokens(candidate)
    union = query_tokens | candidate_tokens
    jaccard = len(query_tokens & candidate_tokens) / len(union) if union else 0.0
    substring = 0.25 if query.lower() in candidate.lower() or candidate.lower() in query.lower() else 0.0
    return max(base, 0.5 * jaccard + substring, substring)


def _o2_score(query_o2: float, candidate_o2: float | None) -> float:
    if candidate_o2 is None:
        return 0.1
    return max(0.0, 1.0 - abs(query_o2 - candidate_o2) / 5.0)


def _pressure_psia(value: float | None) -> float | None:
    return round(value / PSI_TO_KPA, 3) if value is not None else None


def _to_evidence(row: sqlite3.Row, score: float) -> dict[str, Any]:
    return {
        "experiment_id": row["experiment_id"],
        "dataset": row["dataset"],
        "platform": row["platform"],
        "material": row["material"],
        "material_class": row["material_class"],
        "o2_initial_pct": row["o2_initial_pct"],
        "pressure_psia": _pressure_psia(row["pressure_kpa"]),
        "flow_velocity_cm_s": row["flow_velocity_cm_s"],
        "flow_direction": row["flow_direction"],
        "gravity": row["gravity"],
        "thickness_mm": row["thickness_mm"],
        "spread_rate_mm_s": row["spread_rate_mm_s"],
        "spread_rate_1g_mm_s": row["spread_rate_1g_mm_s"],
        "outcome": row["outcome"],
        "derived": bool(row["derived"]),
        "notes": row["notes"],
        "source_url": row["source_url"],
        "provenance_hash": row["provenance_hash"],
        "score": round(score, 3),
    }


def retrieve_evidence(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    pressure_psia: float,
    flow_direction: str | None = None,
    limit: int = 12,
    min_similarity: float = 0.25,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM experiments
        WHERE material_class != 'Gas fuel' AND material != 'unspecified'
        """
    ).fetchall()
    scored: list[tuple[float, sqlite3.Row]] = []
    for row in rows:
        material_score = _material_similarity(material, row["material"])
        if material_score <= 0:
            continue
        o2_score = _o2_score(o2_pct, row["o2_initial_pct"])
        if flow_direction and row["flow_direction"]:
            flow_score = 1.0 if flow_direction.lower() == row["flow_direction"].lower() else 0.5
        else:
            flow_score = 0.75
        gravity_score = 1.0 if row["gravity"] == "microgravity" else 0.5
        score = (
            0.55 * material_score
            + 0.30 * o2_score
            + 0.10 * flow_score
            + 0.05 * gravity_score
        )
        if row["outcome"]:
            score += 0.08
        if row["pressure_kpa"] is not None:
            score += 0.04
        if score >= min_similarity:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [_to_evidence(row, score) for score, row in scored[:limit]]


def _pressure_known(evidence: list[dict[str, Any]]) -> bool:
    return any(item["pressure_psia"] is not None for item in evidence)


def _grade(
    o2_pct: float,
    pressure_psia: float,
    evidence: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    o2_tolerance = config["evidence"]["o2_tolerance_pct"]
    pressure_tolerance = config["evidence"]["pressure_tolerance_psia"]
    if not evidence:
        return {
            "grade": "D",
            "verdict": "insufficient_evidence",
            "confidence": 0.2,
            "outside": False,
            "documented": [],
            "reasons": ["No solid-material evidence matched this material."],
            "gaps": ["No usable microgravity or 1-g evidence."],
        }

    microgravity = [item for item in evidence if item["gravity"] == "microgravity"]
    documented = [item for item in microgravity if item["outcome"]]
    one_g_documented = [
        item for item in evidence if item["gravity"] != "microgravity" and item["outcome"]
    ]
    o2_values = [item["o2_initial_pct"] for item in microgravity if item["o2_initial_pct"] is not None]
    min_o2 = min(o2_values) if o2_values else None
    max_o2 = max(o2_values) if o2_values else None
    pressure_values = [item["pressure_psia"] for item in microgravity if item["pressure_psia"] is not None]

    outside_o2 = max_o2 is not None and o2_pct > max_o2 + o2_tolerance
    outside_pressure = bool(pressure_values) and pressure_psia < min(pressure_values) - pressure_tolerance
    outside = outside_o2 or outside_pressure
    bracketing = (
        min_o2 is not None
        and max_o2 is not None
        and min_o2 - o2_tolerance <= o2_pct <= max_o2 + o2_tolerance
    )

    at_or_beyond: list[dict[str, Any]] = []
    for item in documented:
        item_o2 = item["o2_initial_pct"]
        if item_o2 is None:
            continue
        if item["outcome"] in {"no_spread", "not_ignited"}:
            condition = item_o2 >= o2_pct - o2_tolerance
        else:
            condition = item_o2 <= o2_pct + o2_tolerance
        pressure_condition = (
            item["pressure_psia"] is not None
            and item["pressure_psia"] >= pressure_psia - pressure_tolerance
        )
        if condition and pressure_condition:
            at_or_beyond.append(item)

    comparable = [
        item
        for item in documented
        if item["o2_initial_pct"] is not None
        and abs(item["o2_initial_pct"] - o2_pct) <= o2_tolerance
    ]
    outcomes = {item["outcome"] for item in documented}
    comparable_outcomes = {item["outcome"] for item in comparable}
    conflict = "spread" in comparable_outcomes and (
        {"no_spread", "not_ignited"} & comparable_outcomes
    )

    if at_or_beyond:
        grade = "A"
    elif documented and bracketing:
        grade = "B"
    elif microgravity and bracketing:
        grade = "B"
    elif microgravity:
        grade = "C"
    else:
        grade = "C"

    if outside and grade in {"A", "B"}:
        grade = "C"
    if conflict and grade in {"A", "B"}:
        grade = "C"

    pressure_known = _pressure_known(documented)
    if grade == "A" and not pressure_known:
        grade = "B"

    if grade == "A":
        verdict = "high_risk" if outcomes & {"spread", "ignited"} else "acceptable"
    elif grade in {"B", "C"}:
        verdict = "test_needed"
    else:
        verdict = "insufficient_evidence"

    best = evidence[0]
    reasons = [
        (
            f"Retrieved {len(evidence)} solid-material tests; {len(documented)} microgravity "
            f"and {len(one_g_documented)} 1-g rows carry a documented outcome."
        ),
        (
            f"Closest evidence: {best['experiment_id']} ({best['material']}, "
            f"{best['o2_initial_pct']}% O2, outcome={best['outcome']})."
        ),
    ]
    if grade == "A" and at_or_beyond:
        anchor = max(
            at_or_beyond,
            key=lambda item: item["o2_initial_pct"]
            if item["o2_initial_pct"] is not None
            else float("-inf"),
        )
        reasons.append(
            f"Grade A anchor: {anchor['experiment_id']} at {anchor['o2_initial_pct']}% O2 "
            f"and {anchor['pressure_psia']} psia, outcome={anchor['outcome']}."
        )
    if outside_o2:
        reasons.append(
            f"Query O2={o2_pct}% exceeds the tested maximum of {max_o2}% by more than "
            f"{o2_tolerance}%; grade downgraded."
        )
    if outside_pressure:
        reasons.append("Query pressure is below the tested pressure envelope; grade downgraded.")
    if not pressure_known and documented:
        reasons.append("Matched documentation does not report pressure; A grade is capped at B.")
    if conflict:
        reasons.append("Documented microgravity outcomes conflict near the query O2; grade lowered.")
    if not documented:
        if one_g_documented:
            reasons.append(
                f"No microgravity outcome; {len(one_g_documented)} 1-g test(s) provide an "
                "external anchor. R6 caps the grade at C."
            )
        else:
            reasons.append(
                "No documented spread or extinction outcome; conditions support a test "
                "plan, not acceptance."
            )

    gaps = []
    if not documented:
        gaps.append("Documented microgravity outcome (spread, extinction, or no ignition) at the query condition.")
    if outside_o2:
        gaps.append(f"Microgravity test at or above {o2_pct}% O2.")
    if outside_pressure:
        gaps.append(f"Test data at or below {pressure_psia} psia.")
    if not pressure_known and microgravity:
        gaps.append("Pressure-resolved microgravity test data.")
    if not pressure_known and not microgravity:
        gaps.append(
            f"Microgravity test at or below {o2_pct}% O2 with a documented outcome and pressure."
        )
    if not any(item["flow_direction"] for item in evidence):
        gaps.append("Flow direction (concurrent versus opposed).")
    if material_class(best["material"]) == "Other":
        gaps.append("Material identification or alias mapping.")
    if not gaps:
        gaps.append("Configuration-level layup or combined-material test.")

    confidence = min(0.95, 0.2 + 0.08 * len(evidence) + 0.2 * best["score"])
    if not pressure_known:
        confidence -= 0.1
    if outside:
        confidence -= 0.1
    if conflict:
        confidence -= 0.1
    confidence = round(max(0.05, min(0.95, confidence)), 2)

    return {
        "grade": grade,
        "verdict": verdict,
        "confidence": confidence,
        "outside": outside,
        "documented": documented,
        "reasons": reasons,
        "gaps": gaps,
    }


def _core_assessment(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    pressure_psia: float,
    flow_direction: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    evidence = retrieve_evidence(
        connection,
        material,
        o2_pct,
        pressure_psia,
        flow_direction=flow_direction,
        limit=config["evidence"]["max_evidence"],
        min_similarity=config["evidence"]["min_similarity"],
    )
    graded = _grade(o2_pct, pressure_psia, evidence, config)
    citations = []
    for item in evidence[:6]:
        citations.append(
            {
                "experiment_id": item["experiment_id"],
                "source_url": item["source_url"],
                "dataset": item["dataset"],
                "provenance_hash": item["provenance_hash"],
            }
        )
    result = {
        "query": {
            "material": material,
            "material_class": material_class(material),
            "o2_pct": o2_pct,
            "pressure_psia": pressure_psia,
            "flow_direction": flow_direction,
            "gravity": "microgravity",
        },
        "grade": graded["grade"],
        "verdict": graded["verdict"],
        "confidence": graded["confidence"],
        "outside_envelope": graded["outside"],
        "evidence": evidence,
        "reasons": graded["reasons"],
        "gaps": graded["gaps"],
        "citations": citations,
        "rules_applied": [rule["id"] for rule in config["rules"]],
        "boundary": "Screening support, not certification or flight approval.",
    }
    return result


def assess(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    pressure_psia: float,
    flow_direction: str | None = None,
    config: dict[str, Any] | None = None,
    include_sensitivity: bool = True,
) -> dict[str, Any]:
    cfg = config or load_config()
    connection.row_factory = sqlite3.Row
    result = _core_assessment(connection, material, o2_pct, pressure_psia, flow_direction, cfg)
    if include_sensitivity:
        variants = [
            ("baseline", o2_pct, pressure_psia),
            ("o2_minus_2", max(0.0, o2_pct - 2.0), pressure_psia),
            ("o2_plus_2", o2_pct + 2.0, pressure_psia),
            ("pressure_minus_2", o2_pct, max(0.1, pressure_psia - 2.0)),
            ("pressure_plus_2", o2_pct, pressure_psia + 2.0),
        ]
        sensitivity = []
        for label, variant_o2, variant_pressure in variants:
            variant = _core_assessment(
                connection, material, variant_o2, variant_pressure, flow_direction, cfg
            )
            sensitivity.append(
                {
                    "variant": label,
                    "o2_pct": round(variant_o2, 2),
                    "pressure_psia": round(variant_pressure, 2),
                    "grade": variant["grade"],
                    "verdict": variant["verdict"],
                }
            )
        result["sensitivity"] = sensitivity
        result["sensitivity_flips"] = len({item["grade"] for item in sensitivity}) > 1
    return result


def inventory(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT material_class,
               count(*) AS tests,
               sum(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS outcomes,
               min(o2_initial_pct) AS min_o2,
               max(o2_initial_pct) AS max_o2,
               group_concat(DISTINCT dataset) AS datasets,
               (
                   SELECT material
                   FROM experiments e2
                   WHERE e2.material_class = experiments.material_class
                     AND e2.material != 'unspecified'
                   GROUP BY material
                   ORDER BY count(*) DESC
                   LIMIT 1
               ) AS example_material
        FROM experiments
        WHERE material_class != 'Gas fuel' AND material != 'unspecified'
        GROUP BY material_class
        ORDER BY tests DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def gap_map(
    connection: sqlite3.Connection,
    atmosphere_key: str = "iss_internal",
    config: dict[str, Any] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    cfg = config or load_config()
    atmosphere = cfg["atmospheres"][atmosphere_key]
    results = []
    for row in inventory(connection):
        assessment = assess(
            connection,
            row["example_material"] or row["material_class"],
            atmosphere["o2_pct"],
            atmosphere["pressure_psia"],
            config=cfg,
            include_sensitivity=False,
        )
        priority = {"D": 3, "C": 2, "B": 1, "A": 0}[assessment["grade"]]
        results.append(
            {
                "material_class": row["material_class"],
                "example_material": row["example_material"],
                "tests": row["tests"],
                "outcomes": row["outcomes"],
                "min_o2": row["min_o2"],
                "max_o2": row["max_o2"],
                "datasets": row["datasets"],
                "grade": assessment["grade"],
                "verdict": assessment["verdict"],
                "priority": priority,
                "top_gap": assessment["gaps"][0] if assessment["gaps"] else "",
                "source": "database",
            }
        )
    for target in cfg.get("gap_targets", []):
        material = target["material"]
        assessment = assess(
            connection,
            material,
            atmosphere["o2_pct"],
            atmosphere["pressure_psia"],
            config=cfg,
            include_sensitivity=False,
        )
        if assessment["evidence"] or assessment["grade"] != "D":
            continue
        results.append(
            {
                "material_class": material,
                "example_material": material,
                "tests": 0,
                "outcomes": 0,
                "min_o2": None,
                "max_o2": None,
                "datasets": "",
                "grade": assessment["grade"],
                "verdict": assessment["verdict"],
                "priority": 4,
                "top_gap": target.get("note") or assessment["gaps"][0],
                "source": "requested_target",
            }
        )
    results.sort(key=lambda item: (-item["priority"], item["outcomes"], -item["tests"]))
    return results[:limit] if limit else results


def open_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection
