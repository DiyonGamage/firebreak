from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from firebreak.data.psi import material_class

ALIAS_BENCHMARK = [
    ("PMMA", "PMMA"),
    ("polymethyl methacrylate", "PMMA"),
    ("acrylic sheet", "PMMA"),
    ("SIBAL", "SIBAL"),
    ("cotton-fiberglass", "SIBAL"),
    ("Nomex III", "Nomex"),
    ("silicone rubber", "Silicone"),
    ("PMMA & Nomex", "PMMA/Nomex"),
    ("Kevlar/PBI webbing", "Kevlar/PBI"),
]

UNKNOWN_BENCHMARK = [
    "polyethylene film",
    "Vectran fabric",
    "unobtainium composite",
]


def _expand(value: str) -> str:
    return f"{value} {material_class(value)}"


def _compatible(query_class: str, candidate_class: str) -> bool:
    if query_class == "Other" or candidate_class == "Other":
        return query_class == candidate_class
    return (
        query_class == candidate_class
        or query_class in candidate_class
        or candidate_class in query_class
    )


def build_index(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT material, material_class, count(*) AS tests
        FROM experiments
        WHERE material_class != 'Gas fuel' AND material != 'unspecified'
        GROUP BY material, material_class
        ORDER BY tests DESC
        """
    ).fetchall()
    materials = [row[0] for row in rows]
    classes = [row[1] for row in rows]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=True)
    matrix = vectorizer.fit_transform([_expand(material) for material in materials])
    return {
        "materials": materials,
        "classes": classes,
        "vectorizer": vectorizer,
        "matrix": matrix,
    }


def match_materials(
    connection: sqlite3.Connection,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    index = build_index(connection)
    query_class = material_class(query)
    query_vector = index["vectorizer"].transform([_expand(query)])
    similarities = cosine_similarity(query_vector, index["matrix"])[0]
    query_tokens = {token for token in query.lower().split() if len(token) > 2}
    results: list[dict[str, Any]] = []
    for position, material in enumerate(index["materials"]):
        candidate_class = index["classes"][position]
        if not _compatible(query_class, candidate_class):
            continue
        same_class = query_class == candidate_class and query_class != "Other"
        compatible = same_class or _compatible(query_class, candidate_class)
        if query_class == "Other" and not same_class:
            continue
        candidate_tokens = {token for token in material.lower().split() if len(token) > 2}
        token_overlap = bool(query_tokens & candidate_tokens)
        score = 0.8 * float(similarities[position]) + (0.2 if same_class else 0.12 if compatible else 0)
        if score < 0.2:
            continue
        if query_class == "Other" and not token_overlap:
            continue
        results.append(
            {
                "material": material,
                "material_class": candidate_class,
                "score": round(score, 3),
                "same_class": same_class,
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def match_evidence(
    connection: sqlite3.Connection,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    matches = match_materials(connection, query, top_k=limit)
    evidence = []
    for match in matches:
        row = connection.execute(
            """
            SELECT experiment_id, dataset, material, material_class, o2_initial_pct,
                   pressure_kpa, flow_velocity_cm_s, gravity, spread_rate_mm_s,
                   outcome, source_url
            FROM experiments
            WHERE material = ? AND material_class = ?
            ORDER BY (o2_initial_pct IS NULL), o2_initial_pct DESC
            LIMIT 1
            """,
            (match["material"], match["material_class"]),
        ).fetchone()
        if row is None:
            continue
        evidence.append(
            {
                **match,
                "experiment_id": row[0],
                "dataset": row[1],
                "material": row[2],
                "material_class": row[3],
                "o2_initial_pct": row[4],
                "pressure_psia": round(row[5] / 6.894757, 2) if row[5] else None,
                "flow_velocity_cm_s": row[6],
                "gravity": row[7],
                "spread_rate_mm_s": row[8],
                "outcome": row[9],
                "source_url": row[10],
            }
        )
    return evidence


def evaluate_matcher(connection: sqlite3.Connection) -> dict[str, Any]:
    known_hits = 0
    known_details = []
    for query, expected in ALIAS_BENCHMARK:
        results = match_materials(connection, query, top_k=3)
        hit = any(_compatible(expected, item["material_class"]) for item in results)
        known_hits += int(hit)
        known_details.append(
            {
                "query": query,
                "expected_class": expected,
                "hit_at_3": hit,
                "returned": [item["material_class"] for item in results],
            }
        )
    unknown_false_matches = 0
    unknown_details = []
    for query in UNKNOWN_BENCHMARK:
        results = match_materials(connection, query, top_k=3)
        false_match = bool(results)
        unknown_false_matches += int(false_match)
        unknown_details.append(
            {
                "query": query,
                "false_match": false_match,
                "returned": [item["material_class"] for item in results],
            }
        )
    return {
        "known_queries": len(ALIAS_BENCHMARK),
        "recall_at_3": round(known_hits / len(ALIAS_BENCHMARK), 3),
        "unknown_queries": len(UNKNOWN_BENCHMARK),
        "false_match_rate": round(unknown_false_matches / len(UNKNOWN_BENCHMARK), 3),
        "known_details": known_details,
        "unknown_details": unknown_details,
        "gate": {
            "recall_at_3_min": 0.8,
            "false_match_rate_max": 0.2,
            "passed": (
                known_hits / len(ALIAS_BENCHMARK) >= 0.8
                and unknown_false_matches / len(UNKNOWN_BENCHMARK) <= 0.2
            ),
        },
    }


def match_scores(connection: sqlite3.Connection, query: str, top_k: int = 5) -> list[float]:
    return [item["score"] for item in match_materials(connection, query, top_k=top_k)]


def mean_score(connection: sqlite3.Connection, query: str) -> float:
    scores = match_scores(connection, query)
    return float(np.mean(scores)) if scores else 0.0
