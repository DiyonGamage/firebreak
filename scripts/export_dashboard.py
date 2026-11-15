from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.config import DB_PATH
from firebreak.ml.severity import get_model, predict_severity
from firebreak.rules.engine import assess, gap_map, load_config, open_connection
from firebreak.services.court import build_court
from firebreak.services.dossier import get_stats
from firebreak.services.investigations import catalog, pillars

OUT = ROOT / "docs" / "assets" / "data" / "dashboard.json"
CASES = ROOT / "artifacts" / "case_studies.json"


def stats(connection: sqlite3.Connection, base: dict) -> dict[str, int]:
    solid_filter = "material_class != 'Gas fuel' AND material != 'unspecified'"
    q = lambda sql: connection.execute(sql).fetchone()[0]
    solid_outcomes = q(
        f"SELECT count(*) FROM experiments WHERE {solid_filter} AND outcome IS NOT NULL"
    )
    one_g = q(
        f"SELECT count(*) FROM experiments WHERE {solid_filter} "
        "AND outcome IS NOT NULL AND gravity != 'microgravity'"
    )
    return {
        "all_records": base["records"],
        "experiments": base["total"],
        "characterisation": base["characterisation"],
        "solid_tests": base["solid"],
        "outcomes": solid_outcomes,
        "microgravity_outcomes": solid_outcomes - one_g,
        "one_g_outcomes": one_g,
        "anchors": q(
            f"SELECT count(*) FROM experiments WHERE {solid_filter} "
            "AND gravity = 'microgravity' AND outcome IS NOT NULL AND pressure_kpa IS NOT NULL"
        ),
        "documents": base["documents"],
        "pages": base["pages"],
        "datasets": len(base["datasets"]) + q("SELECT count(DISTINCT dataset) FROM investigation_records"),
    }


def main() -> None:
    cfg = load_config()
    connection = open_connection(DB_PATH)
    connection.row_factory = sqlite3.Row
    iss = cfg["atmospheres"]["iss_internal"]

    cases = []
    for case in json.loads(CASES.read_text(encoding="utf-8")):
        result = assess(
            connection,
            case["material"],
            case["o2"],
            case["pressure"],
            flow_direction=case.get("flow"),
            config=cfg,
            include_sensitivity=True,
        )
        cases.append(
            {
                "key": case["key"],
                "title": case["title"],
                "material": case["material"],
                "o2": case["o2"],
                "pressure": case["pressure"],
                "grade": result["grade"],
                "verdict": result["verdict"],
                "confidence": result["confidence"],
                "outside_envelope": result["outside_envelope"],
                "reasons": result["reasons"][:4],
                "gaps": result["gaps"][:4],
                "boundary": result["boundary"],
                "nearest": [
                    {
                        "experiment_id": row["experiment_id"],
                        "dataset": row["dataset"],
                        "material": row["material"],
                        "o2": row["o2_initial_pct"],
                        "pressure_psia": row["pressure_psia"],
                        "outcome": row["outcome"],
                        "source_url": row["source_url"],
                        "provenance_hash": row["provenance_hash"],
                        "o2_gap": row.get("o2_gap_pct"),
                    }
                    for row in result["evidence"][:3]
                ],
                "citations": result["citations"][:4],
                "court": build_court(result, iss["label"])["voices"],
                "sensitivity": result["sensitivity"],
                "flips": result.get("sensitivity_flips", False),
            }
        )

    curve = []
    step = 0.25
    o2 = 13.6
    while o2 <= 24.1001:
        graded = assess(
            connection,
            "PMMA",
            round(o2, 2),
            iss["pressure_psia"],
            config=cfg,
            include_sensitivity=False,
        )
        severity = predict_severity(connection, "PMMA", round(o2, 2), 6.35)
        curve.append(
            {
                "o2": round(o2, 2),
                "grade": graded["grade"],
                "verdict": graded["verdict"],
                "enabled": severity["enabled"],
                "status": severity["status"],
                "p": severity.get("probability_delta_co2_gt_0.5"),
                "set": (severity.get("conformal") or {}).get("labels"),
                "band": severity.get("band"),
            }
        )
        o2 += step

    model = get_model(connection)
    metrics = model["metrics"]

    payload = {
        "stats": stats(connection, get_stats(connection, cfg)),
        "presets": [
            {"key": key, "label": value["label"], "o2": value["o2_pct"], "pressure": value["pressure_psia"]}
            for key, value in cfg["atmospheres"].items()
        ],
        "iss": {"label": iss["label"], "o2": iss["o2_pct"], "pressure": iss["pressure_psia"]},
        "cases": cases,
        "curve": curve,
        "model": {
            "auc": metrics["auc"],
            "o2_only_auc": metrics["o2_only_auc"],
            "brier": metrics["brier"],
            "ece": metrics["ece"],
            "coverage": metrics["conformal"]["coverage"],
            "target_coverage": metrics["conformal"]["target_coverage"],
            "set_size": metrics["conformal"]["average_set_size"],
            "o2_min": metrics["o2_support"][0],
            "o2_max": metrics["o2_support"][1],
            "n": metrics["n"],
            "positives": metrics["positives"],
            "violations": metrics["monotonic"]["violations"],
        },
        "pillars": pillars(connection),
        "catalog": [
            {"name": r["name"], "pillar": r["pillar"], "records": r["records"], "experiments": r["experiments"], "outcomes": r["outcomes"]}
            for r in catalog(connection)
        ],
        "gapmap": gap_map(connection, "iss_internal", config=cfg),
        "anchors": [
            {
                **dict(row),
                "pressure_psia": round(row["pressure_kpa"] * 0.1450377, 2)
                if row["pressure_kpa"] is not None
                else None,
            }
            for row in connection.execute(
                """
                SELECT material, material_class, o2_initial_pct AS o2, pressure_kpa,
                       gravity, outcome, dataset, source_url, provenance_hash
                FROM experiments
                WHERE material_class != 'Gas fuel' AND material != 'unspecified'
                  AND outcome IS NOT NULL
                ORDER BY material, o2_initial_pct
                """
            ).fetchall()
        ],
        "reported": {
            "one_g_o2": 16.0,
            "microgravity_o2": 13.6,
            "margin": 2.4,
            "quote": (
                "PMMA 1-g blowoff at 16 percent O2 versus steady microgravity spread at "
                "13.6 percent O2: negative oxygen margin of safety 2.4 percent."
            ),
            "citation": "NASA/TM-20210011385",
            "url": "https://ntrs.nasa.gov/citations/20210011385",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT, OUT.stat().st_size, "bytes")
    print("stats", payload["stats"])
    print("cases", [(c["key"], c["grade"], c["verdict"]) for c in cases])
    print("curve", len(curve), "resolved", sum(1 for p in curve if p["enabled"]))
    print("grades on curve", sorted({p["grade"] for p in curve}))
    print("pillars", [(p["pillar"], p["records"], p["experiments"]) for p in payload["pillars"]])


if __name__ == "__main__":
    main()
