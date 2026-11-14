from __future__ import annotations

from typing import Any


def _median(values: list[float]) -> float | None:
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return None
    mid = len(clean) // 2
    return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2


def _curator(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result["evidence"]
    datasets = sorted({_investigation(item["dataset"]) for item in evidence})
    micro = [item for item in evidence if item["gravity"] == "microgravity"]
    with_pressure = [item for item in micro if item["pressure_psia"] is not None]
    with_outcome = [item for item in evidence if item["outcome"]]
    o2_values = [item["o2_initial_pct"] for item in evidence if item["o2_initial_pct"] is not None]
    low, high = (min(o2_values), max(o2_values)) if o2_values else (None, None)
    if not evidence:
        statement = "No matching solid-material rows in the corpus. Nothing to grade."
    else:
        statement = (
            f"{len(evidence)} matching rows from {len(datasets)} investigation"
            f"{'s' if len(datasets) != 1 else ''} "
            f"({', '.join(datasets)}), spanning "
            f"{low:.1f}–{high:.1f}% O2. "
            f"{len(micro)} are microgravity, {len(with_pressure)} of those report pressure, "
            f"and {len(with_outcome)} carry a documented outcome."
        )
    return {
        "role": "Curator",
        "question": "What do we actually have?",
        "statement": statement,
        "basis": [f"{len(evidence)} rows", f"{len(datasets)} datasets"],
    }


def _investigation(dataset: str) -> str:
    return dataset.replace(" (NTRS)", "").strip()


def _critic(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result["evidence"]
    micro = [item for item in evidence if item["gravity"] == "microgravity"]
    datasets = sorted({_investigation(item["dataset"]) for item in micro})
    findings: list[str] = []

    if not evidence:
        findings.append("There is no evidence to critique, because there is none to cite.")
    else:
        if len(datasets) == 1:
            findings.append(
                f"Every microgravity row traces back to a single investigation ({datasets[0]}); "
                "there is no independent replication."
            )
        if not any(item["pressure_psia"] is not None for item in micro):
            findings.append("No microgravity row reports pressure, so the A grade cannot be reached.")
        if not any(item["outcome"] for item in micro):
            findings.append("No microgravity row reports an outcome; the record is bracket-only.")
        if result["outside_envelope"]:
            findings.append("The requested condition sits outside the tested envelope.")
        if evidence and all(item["gravity"] != "microgravity" for item in evidence):
            findings.append("Only 1-g evidence exists; R6 caps the grade at C.")
    if not findings:
        findings.append("No structural weakness found in the matched set; the gap is the open condition.")
    return {
        "role": "Critic",
        "question": "Where is this weak?",
        "statement": " ".join(findings),
        "basis": findings,
    }


def _safety(result: dict[str, Any], atmosphere_label: str) -> dict[str, Any]:
    grade = result["grade"]
    verdict = {
        "acceptable": "the evidence supports acceptance",
        "high_risk": "the evidence documents spread — the material is the hazard",
        "test_needed": "the evidence is insufficient to accept",
        "insufficient_evidence": "there is no usable evidence either way",
    }.get(result["verdict"], result["verdict"].replace("_", " "))
    meaning = {
        "A": "The evidence is strong. The answer is usable for screening.",
        "B": "The evidence brackets the condition but is incomplete. Treat as provisional.",
        "C": "The evidence ended here. C is a test requirement, not a pass.",
        "D": "Unknown is not safe. Do not read this as clearance.",
    }[grade]
    statement = f"At {atmosphere_label}, {verdict}. Grade {grade}: {meaning}"
    if result.get("reasons"):
        statement += f" Governing reason: {result['reasons'][0]}"
    return {
        "role": "Safety Officer",
        "question": "What does this mean for a crew?",
        "statement": statement,
        "basis": [f"grade {grade}", result["verdict"], *result.get("rules_applied", [])[:4]],
    }


def _experimentalist(result: dict[str, Any]) -> dict[str, Any]:
    if result["gaps"]:
        statement = result["gaps"][0]
    else:
        statement = "No structural gap is recorded at this condition; validate the as-built article."
    return {
        "role": "Experimentalist",
        "question": "What would settle it?",
        "statement": statement,
        "basis": result["gaps"][:3] or ["no recorded gap"],
    }


def build_court(result: dict[str, Any], atmosphere_label: str) -> dict[str, Any]:
    voices = [
        _curator(result),
        _critic(result),
        _safety(result, atmosphere_label),
        _experimentalist(result),
    ]
    return {
        "voices": voices,
        "verdict": {
            "grade": result["grade"],
            "verdict": result["verdict"],
            "confidence": result["confidence"],
        },
        "note": (
            "Every line above is generated from the matched rows and the rule engine. "
            "No language model writes the grade or the citations."
        ),
    }
