from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.rules.engine import load_config, open_connection
from firebreak.services.dossier import build_dossier

CASES = [
    {
        "key": "pmma",
        "title": "PMMA at ISS internal atmosphere",
        "material": "PMMA",
        "o2": 24.1,
        "pressure": 14.5,
        "flow": None,
        "note": "The canonical negative-margin case: 1-g blow-off at 16% O2 versus steady microgravity spread at 13.6% O2.",
    },
    {
        "key": "pmma_lunar",
        "title": "PMMA at lunar surface atmosphere",
        "material": "PMMA",
        "o2": 37.0,
        "pressure": 8.2,
        "flow": None,
        "note": "Beyond the tested O2 envelope; the grade must downgrade even for a well-studied material.",
    },
    {
        "key": "saffire",
        "title": "Saffire-II silicone and SIBAL",
        "material": "Silicone",
        "o2": 22.1,
        "pressure": 14.5,
        "flow": "concurrent",
        "note": "Microgravity no-spread for silicone versus 1.2 mm/s in 1-g; SIBAL spreads at 2.1 mm/s in microgravity.",
    },
    {
        "key": "saffire_sibal",
        "title": "Saffire-II SIBAL spread",
        "material": "SIBAL",
        "o2": 22.1,
        "pressure": 14.5,
        "flow": "concurrent",
        "note": "A documented microgravity spread outcome at 22.1% O2; the PSI table omits pressure, so the A anchor comes from a pressure-reported BASS-II NTRS row.",
    },
    {
        "key": "nomex",
        "title": "Nomex at ISS internal atmosphere",
        "material": "Nomex",
        "o2": 24.1,
        "pressure": 14.5,
        "flow": None,
        "note": "Three BASS-II Nomex conditions; no documented spread outcome and no brand/weight metadata.",
    },
    {
        "key": "kevlar_pbi",
        "title": "Kevlar/PBI webbing at lunar surface",
        "material": "Kevlar/PBI",
        "o2": 37.0,
        "pressure": 8.2,
        "flow": None,
        "note": "TB 26-05 is now ingested as two explicitly labeled 1-g rows at 8.2 psia; no microgravity row exists, so R6 caps the result at C.",
    },
]


def main() -> None:
    config = load_config()
    connection = open_connection()
    records = []
    try:
        for case in CASES:
            dossier = build_dossier(
                connection,
                case["material"],
                case["o2"],
                case["pressure"],
                case["flow"],
                config=config,
            )
            records.append(
                {
                    **case,
                    "grade": dossier["grade"],
                    "verdict": dossier["verdict"],
                    "confidence": dossier["confidence"],
                    "outside_envelope": dossier["outside_envelope"],
                    "coverage": dossier["coverage"],
                    "severity": dossier["severity"],
                    "reasons": dossier["reasons"],
                    "gaps": dossier["gaps"],
                    "evidence": dossier["evidence"][:5],
                    "citations": dossier["citations"][:3],
                }
            )
    finally:
        connection.close()
    output = ROOT / "artifacts" / "case_studies.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")

    lines = ["# Firebreak case studies", ""]
    lines.append("All grades are screening support, not certification or flight approval.")
    lines.append("")
    for record in records:
        lines.append(f"## {record['title']}")
        lines.append("")
        lines.append(record["note"])
        lines.append("")
        lines.append(
            f"- Query: {record['material']} at {record['o2']}% O2, "
            f"{record['pressure']} psia"
            + (f", {record['flow']} flow" if record["flow"] else "")
        )
        lines.append(
            f"- Result: **Grade {record['grade']}** — {record['verdict']}; "
            f"confidence {record['confidence']}; coverage {record['coverage']['label']}."
        )
        lines.append(
            f"- Outside tested envelope: {'yes' if record['outside_envelope'] else 'no'}."
        )
        if record["severity"].get("enabled"):
            lines.append(
                f"- BASS-II CO2-rise screen: {record['severity']['band']} "
                f"({round(record['severity']['probability_delta_co2_gt_0.5'] * 100)}%)."
            )
        else:
            lines.append(
                f"- BASS-II CO2-rise screen: abstains — {record['severity'].get('reason', 'outside model scope')}"
            )
        lines.append("")
        lines.append("Why:")
        for reason in record["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
        lines.append("Evidence:")
        for item in record["evidence"]:
            lines.append(
                f"- `{item['experiment_id']}` — {item['material']}, {item['o2_initial_pct']}% O2, "
                f"{item['pressure_psia'] if item['pressure_psia'] is not None else 'pressure n/r'} psia, "
                f"outcome: {item['outcome'] or 'not reported'}; "
                f"[source]({item['source_url']})"
            )
        lines.append("")
        lines.append("Gaps:")
        for gap in record["gaps"]:
            lines.append(f"- {gap}")
        lines.append("")
    (ROOT / "docs" / "case_studies.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps([{ "key": r["key"], "grade": r["grade"], "verdict": r["verdict"], "confidence": r["confidence"] } for r in records], indent=2))


if __name__ == "__main__":
    main()
