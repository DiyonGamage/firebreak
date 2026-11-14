from __future__ import annotations

import json
import re
import threading
from typing import Any

from firebreak.assistant.tools import (
    assess_material,
    coverage_check,
    find_gaps,
    resolve_atmosphere,
    retrieve_evidence,
    severity_estimate,
    tool_map,
)

SYSTEM = (
    "You are the Firebreak evidence router for spacecraft material flammability. "
    "Call exactly one tool that best answers the request. Never invent measurements, "
    "grades, or source data. If the request lacks a material or atmosphere, ask for it. "
    "The tools return JSON; your job is routing, not prose."
)

_AGENT = None
_LOCK = threading.Lock()

MATERIAL_ALIASES = {
    "pmma": "PMMA",
    "acrylic": "PMMA",
    "plexiglas": "PMMA",
    "polymethyl": "PMMA",
    "sibal": "SIBAL",
    "cotton": "SIBAL",
    "nomex": "Nomex",
    "silicone": "Silicone",
    "kevlar": "Kevlar/PBI",
    "pbi": "Kevlar/PBI",
}


def _extract_material(query: str) -> str | None:
    lowered = query.lower()
    for alias, material in MATERIAL_ALIASES.items():
        if alias in lowered:
            return material
    return None


def _fallback(query: str) -> dict[str, Any]:
    lowered = query.lower()
    material = _extract_material(query)
    atmosphere = resolve_atmosphere(query)
    if "gap" in lowered:
        result = find_gaps(atmosphere)
        answer = (
            f"Top evidence gaps for {result['atmosphere_label']}: "
            + "; ".join(
                f"{row['material_class']} ({row['grade']}) — {row['top_gap']}"
                for row in result["gaps"][:3]
            )
            + "."
        )
        return {"engine": "fallback", "answer": answer, "tool": "find_gaps", "result": result}
    if not material:
        return {
            "engine": "fallback",
            "answer": "Tell me a material (for example PMMA, SIBAL, Nomex, or silicone) and I will grade the available evidence.",
            "needs_clarification": True,
        }
    if "coverage" in lowered:
        result = coverage_check(material, atmosphere)
        answer = (
            f"{material} at {result['atmosphere_label']}: coverage is "
            f"{result['label']} (score {result['coverage_score']}); "
            f"{result['gaps'][0]}"
        )
        return {"engine": "fallback", "answer": answer, "tool": "coverage_check", "result": result}
    if "severity" in lowered or "co2" in lowered or "co₂" in lowered:
        result = severity_estimate(material)
        if result.get("enabled"):
            answer = (
                f"{material}: BASS-II CO₂-rise screen is {result['band']} "
                f"({round(result['probability_delta_co2_gt_0.5'] * 100)}% probability). "
                "This is not a flammability prediction."
            )
        else:
            answer = f"{material}: severity screen unavailable — {result.get('reason', 'outside model scope')}."
        return {"engine": "fallback", "answer": answer, "tool": "severity_estimate", "result": result}
    if "evidence" in lowered or "find" in lowered or "source" in lowered:
        result = retrieve_evidence(material)
        lines = [
            f"{item['experiment_id']} ({item['material']}, {item['o2_initial_pct']}% O₂, outcome={item['outcome']})"
            for item in result["matches"][:3]
        ]
        answer = f"Closest evidence for {material}: " + "; ".join(lines) + "."
        return {"engine": "fallback", "answer": answer, "tool": "retrieve_evidence", "result": result}
    result = assess_material(material, atmosphere)
    answer = _assess_answer(result)
    return {"engine": "fallback", "answer": answer, "tool": "assess_material", "result": result}


def _assess_answer(result: dict[str, Any]) -> str:
    query = result["query"]
    verdict = {
        "acceptable": "evidence supports acceptance",
        "high_risk": "evidence indicates spread",
        "test_needed": "evidence is insufficient for acceptance",
        "insufficient_evidence": "no usable evidence",
    }.get(result["verdict"], result["verdict"])
    parts = [
        f"{query['material']} at {query['atmosphere_label']} "
        f"({query['o2_pct']}% O₂, {query['pressure_psia']} psia): "
        f"grade {result['grade']} — {verdict}."
    ]
    if result.get("coverage"):
        parts.append(f"Coverage: {result['coverage']['label']}.")
    if result.get("severity", {}).get("enabled"):
        parts.append(
            f"BASS-II CO₂-rise screen: {result['severity']['band']} band."
        )
    if result.get("reasons"):
        parts.append(result["reasons"][0])
    if result.get("gaps"):
        parts.append(f"Top gap: {result['gaps'][0]}")
    parts.append(result.get("boundary", "Screening support only."))
    return " ".join(parts)


def _answer_from_trace(trace: list[dict[str, Any]]) -> str:
    results = [entry.get("result") for entry in trace if isinstance(entry.get("result"), dict)]
    if not results:
        return "No evidence tool returned a result."
    lines = []
    for entry in trace:
        name = entry.get("name")
        result = entry.get("result") or {}
        if name == "assess_material" and "grade" in result:
            lines.append(_assess_answer(result))
        elif name == "coverage_check" and "label" in result:
            lines.append(
                f"Coverage for {result['material']} at {result['atmosphere_label']}: "
                f"{result['label']} (score {result['coverage_score']})."
            )
        elif name == "severity_estimate" and "enabled" in result:
            if result["enabled"]:
                lines.append(
                    f"BASS-II CO₂-rise screen for {result['material_class']}: "
                    f"{result['band']} band."
                )
            else:
                lines.append(f"Severity screen unavailable: {result.get('reason', 'outside model scope')}.")
        elif name == "retrieve_evidence" and "matches" in result:
            matches = result["matches"][:3]
            lines.append(
                f"Closest evidence for {result['material']}: "
                + "; ".join(
                    f"{item['experiment_id']} ({item['o2_initial_pct']}% O₂, outcome={item['outcome']})"
                    for item in matches
                )
                + "."
            )
        elif name == "find_gaps" and "gaps" in result:
            lines.append(
                f"Top gaps for {result['atmosphere_label']}: "
                + "; ".join(
                    f"{row['material_class']} ({row['grade']})" for row in result["gaps"][:3]
                )
                + "."
            )
        elif name == "build_dossier" and "grade" in result:
            lines.append(_assess_answer(result))
        elif "error" in result:
            lines.append(f"Tool error: {result['error']}")
    return " ".join(lines) if lines else "The evidence router did not return a usable result."


def _engine():
    global _AGENT
    if _AGENT is None:
        from needle import Needle

        _AGENT = Needle(tools=list(tool_map().values()), system=SYSTEM)
    return _AGENT


def ask(query: str, max_steps: int = 4, engine: str = "fallback") -> dict[str, Any]:
    if not query or not query.strip():
        return {"engine": "fallback", "answer": "Ask a material and atmosphere question.", "needs_clarification": True}
    if engine != "cactus":
        return _fallback(query)
    try:
        with _LOCK:
            agent = _engine()
            agent.reset()
            response = agent.complete(query, max_new_tokens=64)
            trace: list[dict[str, Any]] = []
            for _ in range(max_steps):
                calls = response.get("function_calls") or []
                if response.get("type") != "call" or not calls:
                    break
                results = []
                for call in calls:
                    name = call.get("name")
                    arguments = call.get("arguments") or {}
                    function = tool_map().get(name)
                    if function is None:
                        result = {"error": f"unknown tool: {name}"}
                    else:
                        try:
                            result = function(**arguments)
                        except Exception as exc:
                            result = {"error": str(exc)}
                    trace.append({"name": name, "arguments": arguments, "result": result})
                    results.append(result)
                response = agent.complete(json.dumps(results, default=str), max_new_tokens=64)
        if trace:
            return {
                "engine": "cactus-needle",
                "answer": _answer_from_trace(trace),
                "trace": trace,
                "router_note": response.get("reasoning"),
                "router_confidence": response.get("confidence"),
                "boundary": "Router selects tools; answers are generated only from tool JSON.",
            }
    except Exception as exc:
        fallback = _fallback(query)
        fallback["engine_error"] = str(exc)
        return fallback
    return _fallback(query)


def run_fallback(query: str) -> dict[str, Any]:
    return _fallback(query)
