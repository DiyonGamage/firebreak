from __future__ import annotations

import sqlite3
from typing import Any

from firebreak.data.psi import material_class
from firebreak.ml.coverage import assess_coverage
from firebreak.ml.evidence import match_evidence
from firebreak.ml.severity import predict_severity
from firebreak.rules.engine import assess, atmosphere_presets, gap_map, load_config, open_connection
from firebreak.services.dossier import build_dossier

ATMOSPHERE_ALIASES = {
    "iss": "iss_internal",
    "iss internal": "iss_internal",
    "internal": "iss_internal",
    "airlock": "iss_airlock",
    "iss airlock": "iss_airlock",
    "gateway": "gateway",
    "mpcv": "mpcv",
    "orion": "mpcv",
    "lunar": "lunar_surface",
    "mars": "lunar_surface",
    "surface": "lunar_surface",
    "artemis": "artemis_iii",
    "shuttle": "shuttle_legacy",
    "payload": "iss_payload_bay",
    "external": "iss_payload_bay",
}


def resolve_atmosphere(value: str | None) -> str:
    presets = atmosphere_presets()
    if value and value in presets:
        return value
    text = (value or "").lower()
    for alias in sorted(ATMOSPHERE_ALIASES, key=len, reverse=True):
        if alias in text:
            return ATMOSPHERE_ALIASES[alias]
    return "iss_internal"


def _atmosphere(value: str | None, o2_pct: float | None, pressure_psia: float | None):
    key = resolve_atmosphere(value)
    preset = atmosphere_presets()[key]
    return key, preset, (
        float(o2_pct) if o2_pct is not None else preset["o2_pct"],
        float(pressure_psia) if pressure_psia is not None else preset["pressure_psia"],
    )


def assess_material(
    material: str,
    atmosphere: str = "iss_internal",
    o2_pct: float | None = None,
    pressure_psia: float | None = None,
) -> dict[str, Any]:
    """Grade a spacecraft material at a cabin atmosphere using NASA evidence."""
    key, preset, (o2, pressure) = _atmosphere(atmosphere, o2_pct, pressure_psia)
    connection = open_connection()
    try:
        result = assess(connection, material, o2, pressure)
        coverage = assess_coverage(connection, material, o2, pressure)
        severity = predict_severity(connection, material, o2)
    finally:
        connection.close()
    return {
        "query": {
            "material": material,
            "material_class": material_class(material),
            "atmosphere": key,
            "atmosphere_label": preset["label"],
            "o2_pct": o2,
            "pressure_psia": pressure,
        },
        "grade": result["grade"],
        "verdict": result["verdict"],
        "confidence": result["confidence"],
        "outside_envelope": result["outside_envelope"],
        "reasons": result["reasons"],
        "gaps": result["gaps"],
        "coverage": {
            "label": coverage["label"],
            "score": coverage["coverage_score"],
            "gaps": coverage["gaps"],
        },
        "severity": {
            "enabled": severity["enabled"],
            "status": severity.get("status"),
            "band": severity.get("band"),
            "probability": severity.get("probability_delta_co2_gt_0.5"),
            "conformal_set": (severity.get("conformal") or {}).get("labels"),
            "reason": severity.get("reason"),
            "nearest_supported_o2": severity.get("nearest_supported_o2"),
        },
        "top_evidence": [
            {
                "experiment_id": item["experiment_id"],
                "dataset": item["dataset"],
                "material": item["material"],
                "o2_initial_pct": item["o2_initial_pct"],
                "outcome": item["outcome"],
                "source_url": item["source_url"],
            }
            for item in result["evidence"][:4]
        ],
        "boundary": result["boundary"],
    }


def retrieve_evidence(material: str, limit: int = 5) -> dict[str, Any]:
    """Find the closest source-linked NASA test rows for a material name or alias."""
    connection = open_connection()
    try:
        matches = match_evidence(connection, material, limit=int(limit))
    finally:
        connection.close()
    return {"material": material, "matches": matches}


def coverage_check(material: str, atmosphere: str = "iss_internal") -> dict[str, Any]:
    """Check whether Firebreak has evidence near a material and atmosphere condition."""
    key, preset, (o2, pressure) = _atmosphere(atmosphere, None, None)
    connection = open_connection()
    try:
        coverage = assess_coverage(connection, material, o2, pressure)
    finally:
        connection.close()
    return {
        "material": material,
        "atmosphere": key,
        "atmosphere_label": preset["label"],
        "o2_pct": o2,
        "pressure_psia": pressure,
        **coverage,
    }


def severity_estimate(material: str, o2_pct: float = 22.2) -> dict[str, Any]:
    """Estimate the BASS-II CO2-rise severity band for a material at an O2 level (default 22.2%)."""
    connection = open_connection()
    try:
        result = predict_severity(
            connection,
            material,
            float(o2_pct),
        )
    finally:
        connection.close()
    return result


def find_gaps(atmosphere: str = "iss_internal", limit: int = 6) -> dict[str, Any]:
    """Rank material classes by evidence gaps for a cabin atmosphere."""
    key = resolve_atmosphere(atmosphere)
    config = load_config()
    connection = open_connection()
    try:
        rows = gap_map(connection, key, config=config, limit=int(limit))
    finally:
        connection.close()
    return {
        "atmosphere": key,
        "atmosphere_label": config["atmospheres"][key]["label"],
        "gaps": rows,
    }


def build_dossier(
    material: str,
    atmosphere: str = "iss_internal",
    o2_pct: float | None = None,
    pressure_psia: float | None = None,
) -> dict[str, Any]:
    """Build a full source-linked dossier for a material and cabin atmosphere."""
    key, preset, (o2, pressure) = _atmosphere(atmosphere, o2_pct, pressure_psia)
    connection = open_connection()
    try:
        result = build_dossier(connection, material, o2, pressure)
    finally:
        connection.close()
    result["query"]["atmosphere"] = key
    result["query"]["atmosphere_label"] = preset["label"]
    return result


def tool_map() -> dict[str, Any]:
    return {
        "assess_material": assess_material,
        "retrieve_evidence": retrieve_evidence,
        "coverage_check": coverage_check,
        "severity_estimate": severity_estimate,
        "find_gaps": find_gaps,
        "build_dossier": build_dossier,
    }


def tool_schemas() -> list[dict[str, Any]]:
    from needle import build_schema

    return [build_schema(function) for function in tool_map().values()]


def open_db() -> sqlite3.Connection:
    return open_connection()
