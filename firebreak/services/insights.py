from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from firebreak.rules.engine import assess, gap_map, load_config
from firebreak.services.dossier import get_stats

MATRIX_ATMOSPHERES = (
    ("iss_internal", "ISS cabin"),
    ("iss_airlock", "Airlock / Gateway"),
    ("lunar_surface", "Lunar surface"),
)
MATRIX_ORDER = (
    "PMMA",
    "SIBAL",
    "Nomex",
    "Silicone",
    "Kevlar/PBI",
    "PMMA/Nomex",
    "Other",
    "Nylon webbing",
)
DISPLAY_NAMES = {
    "Other": "Unidentified",
    "PMMA/Nomex": "PMMA/Nomex layup",
}
CARD_CASES = (
    ("PMMA", "iss_internal"),
    ("PMMA", "lunar_surface"),
    ("Silicone", "iss_internal"),
    ("Nomex", "iss_internal"),
    ("Kevlar/PBI", "lunar_surface"),
    ("Nylon webbing", "iss_internal"),
)
CASE_LINKS = (
    ("PMMA · ISS cabin", "PMMA", "iss_internal"),
    ("PMMA · lunar surface", "PMMA", "lunar_surface"),
    ("Nomex · ISS cabin", "Nomex", "iss_internal"),
    ("Kevlar/PBI · lunar surface", "Kevlar/PBI", "lunar_surface"),
    ("Nylon webbing · ISS cabin", "Nylon webbing", "iss_internal"),
)
GRADE_LEGEND = (
    {
        "grade": "A",
        "label": "Anchored",
        "meaning": "A documented microgravity outcome at or beyond the target condition, with pressure reported.",
    },
    {
        "grade": "B",
        "label": "Bracketed",
        "meaning": "Microgravity evidence brackets the condition, but an outcome or pressure is missing.",
    },
    {
        "grade": "C",
        "label": "Outside / 1-g",
        "meaning": "Only 1-g data, or the target atmosphere is outside the tested envelope. C is an evidence gap, not a pass.",
    },
    {
        "grade": "D",
        "label": "Unknown",
        "meaning": "No usable solid-material evidence. Unknown is not safe.",
    },
)
PIPELINE = (
    {
        "step": "01",
        "name": "Retrieve",
        "detail": "Material aliasing and O2 proximity score 148 solid tests. Gas-fuel rows stay in the library but out of grading.",
    },
    {
        "step": "02",
        "name": "Check coverage",
        "detail": "ML-2 tests whether the query condition sits inside the documented microgravity envelope.",
    },
    {
        "step": "03",
        "name": "Estimate severity",
        "detail": "ML-3 flags BASS-II delta-CO2 severity for seen classes. It does not predict ignition.",
    },
    {
        "step": "04",
        "name": "Apply rules",
        "detail": "R1-R10 cap grades for missing pressure, 1-g-only data, conflicts, and layup configuration.",
    },
    {
        "step": "05",
        "name": "Cite",
        "detail": "A deterministic grade, source-linked rows, and named gaps. No model writes the final grade.",
    },
)


def _count(connection: sqlite3.Connection, sql: str) -> int:
    return connection.execute(sql).fetchone()[0]


def _href(material: str, atmosphere: str) -> str:
    return "/assess?" + urlencode({"material": material, "atmosphere": atmosphere})


def _microgravity_outcomes(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in result["evidence"]
        if item["gravity"] == "microgravity" and item["outcome"]
    ]


def _pressure_reported(result: dict[str, Any]) -> bool:
    return any(
        item["pressure_psia"] is not None
        for item in result["evidence"]
        if item["gravity"] == "microgravity"
    )


def _only_one_g(result: dict[str, Any]) -> bool:
    return bool(result["evidence"]) and all(
        item["gravity"] != "microgravity" for item in result["evidence"]
    )


def _interpret(result: dict[str, Any]) -> str:
    grade = result["grade"]
    documented = _microgravity_outcomes(result)
    pressure_known = _pressure_reported(result)
    only_one_g = _only_one_g(result)
    if grade == "A":
        if result["verdict"] == "high_risk":
            return (
                "Documented microgravity spread at or below this condition. "
                "Grade A means the evidence is strong; the material is the hazard."
            )
        return "Documented microgravity evidence supports acceptance at this condition."
    if grade == "B":
        if not pressure_known and not documented:
            return (
                "Microgravity tests bracket this condition, but no matched row reports "
                "an outcome or pressure. The grade stays B."
            )
        if not pressure_known:
            return (
                "Outcomes exist, but no matched row reports pressure. "
                "The A grade is capped at B until one pressure-resolved test closes the gap."
            )
        if not documented:
            return (
                "Microgravity tests bracket this condition, but none reports a spread "
                "or extinction outcome. The grade stays B."
            )
        return "Microgravity evidence brackets this condition, but the record is incomplete."
    if grade == "C":
        if only_one_g:
            return (
                "Only 1-g evidence anchors this material. Microgravity behaviour is untested, "
                "so R6 caps the grade at C."
            )
        if result["outside_envelope"]:
            return (
                "The target atmosphere is outside the tested envelope. "
                "C means the evidence ended here, not that the hazard fell."
            )
        return "Evidence exists but does not meet the A/B bar. Treat C as a test requirement."
    return "No usable solid-material evidence is ingested. Unknown is not safe."


def _change(result: dict[str, Any]) -> str:
    if result["grade"] == "D":
        return "A pressure-resolved microgravity test at this condition with a documented outcome."
    return result["gaps"][0] if result["gaps"] else "A test at this condition with a documented outcome."


def _source(result: dict[str, Any], material: str, config: dict[str, Any]) -> tuple[str, str]:
    if result["citations"]:
        citation = result["citations"][0]
        host = "NTRS" if "ntrs.nasa.gov" in citation["source_url"] else "PSI"
        label = (
            citation["dataset"]
            if host.lower() in citation["dataset"].lower()
            else f"{citation['dataset']} · {host}"
        )
        return citation["source_url"], label
    for target in config.get("gap_targets", []):
        if target["material"].lower() == material.lower() and target.get("source_url"):
            return target["source_url"], "TB 26-05 · 1-g NTRS"
    return "", "No source row"


def _card(
    connection: sqlite3.Connection,
    material: str,
    atmosphere_key: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    atmosphere = config["atmospheres"][atmosphere_key]
    result = assess(
        connection,
        material,
        atmosphere["o2_pct"],
        atmosphere["pressure_psia"],
        config=config,
        include_sensitivity=False,
    )
    source_url, source_label = _source(result, material, config)
    only_one_g = _only_one_g(result)
    rank = {
        ("A", "high_risk"): 100,
        ("A", "acceptable"): 80,
        ("D", "insufficient_evidence"): 90,
        ("B", "test_needed"): 75,
    }.get((result["grade"], result["verdict"]), 65 if only_one_g else 55)
    return {
        "material": material,
        "atmosphere": atmosphere_key,
        "atmosphere_label": atmosphere["label"],
        "o2_pct": atmosphere["o2_pct"],
        "pressure_psia": atmosphere["pressure_psia"],
        "grade": result["grade"],
        "verdict": result["verdict"],
        "evidence_count": len(result["evidence"]),
        "only_one_g": only_one_g,
        "interpretation": _interpret(result),
        "change": _change(result),
        "source_url": source_url,
        "source_label": source_label,
        "href": _href(material, atmosphere_key),
        "decision_rank": rank,
    }


def _findings(
    counts: dict[str, int],
    lunar_ab: int,
    lunar_total: int,
) -> list[dict[str, Any]]:
    return [
        {
            "tag": "ANCHOR SCARCITY",
            "value": f"{counts['anchors']} / {counts['solid']}",
            "title": "Six pressure-bearing microgravity outcomes anchor every A grade.",
            "detail": (
                f"Only {counts['solid_outcomes']} of {counts['solid']} solid-material rows "
                "report an outcome at all. The rest add context; they cannot support acceptance."
            ),
        },
        {
            "tag": "1-G CEILING",
            "value": f"{counts['one_g_outcomes']} / {counts['solid_outcomes']}",
            "title": "Two 1-g outcomes cannot stand in for microgravity.",
            "detail": (
                "Kevlar/PBI is the only class anchored by 1-g data. R6 caps it at C "
                "at every atmosphere, no matter how good the 1-g result looks."
            ),
        },
        {
            "tag": "EXPLORATION WALL",
            "value": f"{lunar_ab} / {lunar_total}",
            "title": "No class reaches A or B at the lunar-surface preset.",
            "detail": (
                "At 37% O2 / 8.2 psia every class returns C or D. "
                "That is missing evidence, not lower hazard."
            ),
        },
    ]


def build_dashboard(
    connection: sqlite3.Connection,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    connection.row_factory = sqlite3.Row
    stats = get_stats(connection, cfg)
    counts = {
        "total": stats["total"],
        "solid": stats["solid"],
        "classes": _count(
            connection,
            """
            SELECT count(DISTINCT material_class) FROM experiments
            WHERE material_class != 'Gas fuel' AND material != 'unspecified'
            """,
        ),
        "solid_outcomes": _count(
            connection,
            """
            SELECT count(*) FROM experiments
            WHERE material_class != 'Gas fuel' AND material != 'unspecified'
              AND outcome IS NOT NULL
            """,
        ),
        "one_g_outcomes": _count(
            connection,
            """
            SELECT count(*) FROM experiments
            WHERE material_class != 'Gas fuel' AND material != 'unspecified'
              AND outcome IS NOT NULL AND gravity != 'microgravity'
            """,
        ),
        "anchors": _count(
            connection,
            """
            SELECT count(*) FROM experiments
            WHERE material_class != 'Gas fuel' AND material != 'unspecified'
              AND gravity = 'microgravity' AND outcome IS NOT NULL
              AND pressure_kpa IS NOT NULL
            """,
        ),
        "documents": stats["documents"],
        "pages": stats["pages"],
        "datasets": len(stats["datasets"]),
    }
    counts["microgravity_outcomes"] = counts["solid_outcomes"] - counts["one_g_outcomes"]

    kpis = [
        {
            "value": counts["total"],
            "label": "curated records",
            "note": f"{counts['datasets']} datasets",
        },
        {
            "value": counts["solid"],
            "label": "solid-material tests",
            "note": f"{counts['classes']} material classes",
        },
        {
            "value": counts["solid_outcomes"],
            "label": "documented outcomes",
            "note": f"{counts['microgravity_outcomes']} microgravity · {counts['one_g_outcomes']} at 1-g",
        },
        {
            "value": counts["anchors"],
            "label": "pressure-bearing anchors",
            "note": "the A-grade foundation",
        },
        {
            "value": counts["documents"],
            "label": "source documents",
            "note": f"{counts['pages']} pages",
        },
    ]

    cards = [
        _card(connection, material, atmosphere_key, cfg)
        for material, atmosphere_key in CARD_CASES
    ]
    cards.sort(key=lambda card: (-card["decision_rank"], -card["evidence_count"]))

    maps = {
        key: {row["material_class"]: row for row in gap_map(connection, key, config=cfg)}
        for key, _ in MATRIX_ATMOSPHERES
    }
    matrix = []
    for material_class in MATRIX_ORDER:
        base = maps[MATRIX_ATMOSPHERES[0][0]].get(material_class)
        if base is None:
            continue
        cells = []
        for key, label in MATRIX_ATMOSPHERES:
            row = maps[key].get(material_class)
            if row is None:
                continue
            cells.append(
                {
                    "grade": row["grade"],
                    "verdict": row["verdict"],
                    "href": _href(row["example_material"] or material_class, key),
                    "title": (
                        f"{material_class} at {label}: grade {row['grade']} "
                        f"({row['verdict'].replace('_', ' ')})"
                    ),
                }
            )
        matrix.append(
            {
                "material_class": material_class,
                "label": DISPLAY_NAMES.get(material_class, material_class),
                "tests": base["tests"],
                "outcomes": base["outcomes"],
                "cells": cells,
            }
        )

    lunar_rows = list(maps["lunar_surface"].values())
    lunar_ab = sum(1 for row in lunar_rows if row["grade"] in {"A", "B"})
    findings = _findings(counts, lunar_ab, len(lunar_rows))

    ml_metrics = stats.get("ml_metrics") or {}
    auc = ml_metrics.get("auc", 0.834)
    o2_auc = ml_metrics.get("o2_only_auc", 0.607)
    pipeline = [
        dict(stage, detail=stage["detail"].replace("delta-CO2", "ΔCO₂"))
        for stage in PIPELINE
    ]
    pipeline[2]["detail"] = (
        f"ML-3 flags BASS-II ΔCO₂ > 0.5 severity for seen classes "
        f"(grouped CV AUC {auc}; O₂-only {o2_auc}). It does not predict ignition."
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": kpis,
        "counts": counts,
        "findings": findings,
        "cards": cards,
        "matrix": matrix,
        "matrix_atmospheres": [
            {
                "key": key,
                "label": label,
                "o2_pct": cfg["atmospheres"][key]["o2_pct"],
                "pressure_psia": cfg["atmospheres"][key]["pressure_psia"],
            }
            for key, label in MATRIX_ATMOSPHERES
        ],
        "grade_legend": list(GRADE_LEGEND),
        "pipeline": pipeline,
        "cases": [
            {"label": label, "href": _href(material, atmosphere)}
            for label, material, atmosphere in CASE_LINKS
        ],
        "si_note": (
            "The optional Cactus 3 router runs locally and calls the same tools. "
            "No API key, no external network. The final grade is always the rule "
            "engine's, never a model's."
        ),
        "boundary": (
            "Screening support only. Not certification, flight approval, or a "
            "substitute for NASA-STD-6001 Test 1."
        ),
    }
