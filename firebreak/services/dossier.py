from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from firebreak.config import ROOT
from firebreak.data.psi import material_class
from firebreak.ml.coverage import assess_coverage
from firebreak.ml.severity import predict_severity
from firebreak.rules.engine import assess, load_config

ARTIFACT = ROOT / "artifacts" / "ml_severity_metrics.json"


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def get_stats(connection: sqlite3.Connection, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    datasets = [
        _row_dict(row)
        for row in connection.execute(
            "SELECT dataset, count(*) AS tests FROM experiments GROUP BY dataset ORDER BY tests DESC"
        ).fetchall()
    ]
    total = sum(row["tests"] for row in datasets)
    solid = connection.execute(
        "SELECT count(*) FROM experiments WHERE material_class != 'Gas fuel' AND material != 'unspecified'"
    ).fetchone()[0]
    outcomes = connection.execute(
        "SELECT count(*) FROM experiments WHERE outcome IS NOT NULL"
    ).fetchone()[0]
    documents = connection.execute("SELECT count(*), coalesce(sum(pages), 0) FROM documents").fetchone()
    ml_metrics = None
    if ARTIFACT.exists():
        try:
            ml_metrics = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ml_metrics = None
    return {
        "total": total,
        "solid": solid,
        "outcomes": outcomes,
        "datasets": datasets,
        "documents": documents[0],
        "pages": documents[1],
        "atmospheres": len(cfg["atmospheres"]),
        "ml_metrics": ml_metrics,
    }


def document_metadata(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT citation_id, title, role, pages, chars, source_url
        FROM documents
        ORDER BY CASE role WHEN 'standard' THEN 0 ELSE 1 END, citation_id
        """
    ).fetchall()
    return [_row_dict(row) for row in rows]


def search_documents(
    connection: sqlite3.Connection,
    query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    terms = [term for term in re.findall(r"[a-z0-9+]+", query.lower()) if len(term) > 2]
    if not terms:
        return []
    rows = connection.execute(
        "SELECT citation_id, title, role, pages, source_url, text_path FROM documents"
    ).fetchall()
    hits = []
    for row in rows:
        path = Path(row["text_path"])
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        positions = [(lowered.find(term), term) for term in terms if lowered.find(term) >= 0]
        if not positions:
            continue
        position, term = min(positions)
        snippet = re.sub(r"\s+", " ", text[max(0, position - 220) : position + 340]).strip()
        hits.append(
            {
                "citation_id": row["citation_id"],
                "title": row["title"],
                "role": row["role"],
                "pages": row["pages"],
                "source_url": row["source_url"],
                "term": term,
                "snippet": snippet,
            }
        )
    hits.sort(key=lambda item: item["term"])
    return hits[:limit]


def build_dossier(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    pressure_psia: float,
    flow_direction: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    result = assess(
        connection,
        material,
        o2_pct,
        pressure_psia,
        flow_direction=flow_direction,
        config=cfg,
    )
    result["coverage"] = assess_coverage(connection, material, o2_pct, pressure_psia)
    result["severity"] = predict_severity(connection, material, o2_pct)
    result["facts"] = cfg["facts"]
    result["document_hits"] = search_documents(connection, material)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["query"]["material_class"] = material_class(material)
    if result["query"]["material_class"] == "Gas fuel":
        result["reasons"].append(
            "Gas-fuel experiments are retained in the library, but Firebreak v1 grades solid materials."
        )
    return result


def default_query(atmosphere_key: str = "iss_internal") -> dict[str, Any]:
    config = load_config()
    atmosphere = config["atmospheres"].get(atmosphere_key, config["atmospheres"]["iss_internal"])
    return {
        "material": "PMMA",
        "atmosphere": atmosphere_key,
        "o2": atmosphere["o2_pct"],
        "pressure": atmosphere["pressure_psia"],
        "flow": "",
    }
