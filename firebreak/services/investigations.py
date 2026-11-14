from __future__ import annotations

import sqlite3
from typing import Any

from firebreak.rules.engine import gap_map, load_config

ENVIRONMENTS = (
    ("iss_internal", "ISS cabin", "14.5 psia · 24.1% O₂"),
    ("iss_airlock", "Airlock / Gateway", "10.2 psia · 30% O₂"),
    ("lunar_surface", "Lunar surface", "8.2 psia · 37% O₂"),
)

CATALOG: tuple[dict[str, Any], ...] = (
    {
        "key": "BASS",
        "name": "BASS",
        "full_name": "Burning and Suppression of Solids",
        "pillar": "Prevention",
        "role": "Material evidence",
        "platform": "ISS",
        "datasets": (),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-24",
        "purpose": "First ISS solid-fuel flammability and suppression series. Predecessor to BASS-II.",
        "relevance": {"iss_internal": 4, "iss_airlock": 2, "lunar_surface": 3},
        "relevance_note": "Named by NASA for habitability relevance; no rows extracted into Firebreak yet.",
    },
    {
        "key": "BASS-II",
        "name": "BASS-II",
        "full_name": "Burning and Suppression of Solids — II",
        "pillar": "Prevention",
        "role": "Material evidence",
        "platform": "ISS",
        "datasets": ("BASS-II", "BASS-II (NTRS)"),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        "purpose": "Solid-fuel ignition, spread, blow-off and quenching in ISS cabin atmosphere.",
        "relevance": {"iss_internal": 5, "iss_airlock": 3, "lunar_surface": 4},
        "relevance_note": "Only investigation with pressure-bearing microgravity rows for solid materials.",
    },
    {
        "key": "Saffire-I",
        "name": "Saffire-I",
        "full_name": "Spacecraft Fire Experiment — I",
        "pillar": "Prevention",
        "role": "Material evidence",
        "platform": "Cygnus",
        "datasets": ("Saffire-I",),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
        "purpose": "Large-scale flame spread over fabric in a depressurized cargo vehicle.",
        "relevance": {"iss_internal": 3, "iss_airlock": 2, "lunar_surface": 4},
        "relevance_note": "Large-scale spread at reduced pressure; metadata-only rows in Firebreak.",
    },
    {
        "key": "Saffire-II",
        "name": "Saffire-II",
        "full_name": "Spacecraft Fire Experiment — II",
        "pillar": "Prevention",
        "role": "Material evidence",
        "platform": "Cygnus",
        "datasets": ("Saffire-II",),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-99",
        "purpose": "Nine samples at varied oxygen and pressure, including low-pressure spread limits.",
        "relevance": {"iss_internal": 3, "iss_airlock": 3, "lunar_surface": 5},
        "relevance_note": "The closest microgravity analogue for low-pressure, high-oxygen spread.",
    },
    {
        "key": "Saffire-III",
        "name": "Saffire-III",
        "full_name": "Spacecraft Fire Experiment — III",
        "pillar": "Prevention",
        "role": "Material evidence",
        "platform": "Cygnus",
        "datasets": ("Saffire-III",),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-100",
        "purpose": "Follow-on spread tests at spacecraft-representative conditions.",
        "relevance": {"iss_internal": 3, "iss_airlock": 2, "lunar_surface": 3},
        "relevance_note": "Metadata-only rows in Firebreak; no documented outcomes extracted.",
    },
    {
        "key": "ACME",
        "name": "ACME-BRE",
        "full_name": "Advanced Combustion via Microgravity Experiments",
        "pillar": "Prevention",
        "role": "Context — gas fuel",
        "platform": "ISS",
        "datasets": ("ACME-BRE",),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-20",
        "purpose": "Gas-jet and droplet combustion fundamentals. Not solid-material evidence.",
        "relevance": {"iss_internal": 2, "iss_airlock": 1, "lunar_surface": 1},
        "relevance_note": "Gas fuels are excluded from solid-material grading by design.",
    },
    {
        "key": "SPICE",
        "name": "SPICE",
        "full_name": "Smoke Point In Co-flow Experiment",
        "pillar": "Prevention",
        "role": "Context — gas fuel",
        "platform": "ISS",
        "datasets": ("SPICE",),
        "source_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-107",
        "purpose": "Soot and smoke-point behaviour in microgravity co-flow flames.",
        "relevance": {"iss_internal": 2, "iss_airlock": 1, "lunar_surface": 1},
        "relevance_note": "Largest record set in the corpus; gas-phase, so outside material grading.",
    },
    {
        "key": "SAME",
        "name": "SAME",
        "full_name": "Smoke Aerosol Measurement Experiment",
        "pillar": "Detection",
        "role": "Detection evidence",
        "platform": "ISS",
        "datasets": (),
        "source_url": "https://psi.nasa.gov/physci/search?keywords=smoke",
        "purpose": "Smoke particle size and transport for spacecraft smoke detectors.",
        "relevance": {"iss_internal": 4, "iss_airlock": 3, "lunar_surface": 3},
        "relevance_note": "Covers the detection pillar. Catalogued, not extracted.",
    },
    {
        "key": "SAME-R",
        "name": "SAME-R",
        "full_name": "Smoke Aerosol Measurement Experiment — Reflight",
        "pillar": "Detection",
        "role": "Detection evidence",
        "platform": "ISS",
        "datasets": (),
        "source_url": "https://psi.nasa.gov/physci/search?keywords=smoke",
        "purpose": "Reflight of SAME with revised smoke-generation hardware.",
        "relevance": {"iss_internal": 4, "iss_airlock": 3, "lunar_surface": 3},
        "relevance_note": "Covers the detection pillar. Catalogued, not extracted.",
    },
    {
        "key": "FLEX",
        "name": "FLEX",
        "full_name": "Flame Extinguishment Experiment",
        "pillar": "Suppression",
        "role": "Suppression evidence",
        "platform": "ISS",
        "datasets": (),
        "source_url": "https://psi.nasa.gov/physci/search?keywords=extinguishment",
        "purpose": "Droplet extinction and low-stretch flame behaviour under suppressants.",
        "relevance": {"iss_internal": 4, "iss_airlock": 3, "lunar_surface": 2},
        "relevance_note": "Covers the suppression pillar. Catalogued, not extracted.",
    },
    {
        "key": "SLICE",
        "name": "SLICE",
        "full_name": "Structure and Liftoff In Combustion Experiment",
        "pillar": "Prevention",
        "role": "Near-limit evidence",
        "platform": "ISS",
        "datasets": (),
        "source_url": "https://psi.nasa.gov/physci/search?keywords=liftoff",
        "purpose": "Near-limit jet flame structure and liftoff, relevant to reduced-gravity limits.",
        "relevance": {"iss_internal": 2, "iss_airlock": 2, "lunar_surface": 3},
        "relevance_note": "Partial-gravity adjacent. Catalogued, not extracted.",
    },
)

CONTRADICTIONS: tuple[dict[str, Any], ...] = (
    {
        "material": "PMMA",
        "title": "Ground tests under-predict microgravity spread for PMMA",
        "one_g": {"condition": "1-g, 16% O2", "outcome": "blow-off — no sustained spread"},
        "microgravity": {"condition": "microgravity, 13.6% O2", "outcome": "steady spread"},
        "margin_pp": 2.4,
        "reading": (
            "Microgravity sustains spread 2.4 percentage points below the oxygen level at which "
            "1-g testing extinguishes it. Clearance margins derived from 1-g tests are optimistic."
        ),
        "source_url": "https://ntrs.nasa.gov/citations/20160000593",
        "source_label": "NTRS 20160000593 · BASS-II",
    },
    {
        "material": "Kevlar/PBI",
        "title": "The only 1-g anchor has no microgravity counterpart",
        "one_g": {"condition": "1-g, 8.2 psia", "outcome": "no spread"},
        "microgravity": {"condition": "no microgravity test", "outcome": "not tested"},
        "margin_pp": None,
        "reading": (
            "A clean 1-g result cannot be promoted to a microgravity claim. R6 caps this class "
            "at grade C at every atmosphere, including the lunar preset."
        ),
        "source_url": "https://ntrs.nasa.gov/citations/20260006043",
        "source_label": "NTRS 20260006043 · TB 26-05",
    },
)

MISSING_TESTS = {
    "PMMA": "One microgravity spread test at 37% O2 / 8.2 psia with pressure reported.",
    "SIBAL": "One microgravity spread test at 37% O2 / 8.2 psia with a documented outcome.",
    "Nomex": "Any pressure-resolved microgravity test above 30% O2.",
    "Silicone": "A microgravity test at lunar-surface pressure; current rows stop at ISS cabin.",
    "Kevlar/PBI": "A microgravity test at 8.2 psia — the class is anchored only by 1-g data.",
    "PMMA/Nomex": "A layup-specific microgravity test; single-material results do not transfer.",
    "Other": "Material identification first, then a pressure-resolved microgravity test.",
    "Nylon webbing": "Any microgravity test at all; only a 1-g NASA technical bulletin exists.",
}


def _stats(connection: sqlite3.Connection, datasets: tuple[str, ...]) -> dict[str, Any]:
    if not datasets:
        return {"records": 0, "solid": 0, "outcomes": 0, "materials": [], "o2": None, "pressure": None}
    marks = ",".join("?" for _ in datasets)
    row = connection.execute(
        f"""
        SELECT count(*) AS records,
               sum(CASE WHEN material_class != 'Gas fuel' AND material != 'unspecified' THEN 1 ELSE 0 END) AS solid,
               sum(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS outcomes,
               round(min(CASE WHEN o2_initial_pct BETWEEN 0 AND 100 THEN o2_initial_pct END), 1) AS o2_min,
               round(max(CASE WHEN o2_initial_pct BETWEEN 0 AND 100 THEN o2_initial_pct END), 1) AS o2_max,
               round(min(pressure_kpa), 1) AS p_min,
               round(max(pressure_kpa), 1) AS p_max
        FROM experiments WHERE dataset IN ({marks})
        """,
        datasets,
    ).fetchone()
    materials = [
        item[0]
        for item in connection.execute(
            f"""
            SELECT DISTINCT material_class FROM experiments
            WHERE dataset IN ({marks}) AND material_class NOT IN ('Gas fuel', 'Other')
            ORDER BY material_class
            """,
            datasets,
        )
    ]
    o2 = (row["o2_min"], row["o2_max"]) if row["o2_min"] is not None else None
    pressure = (row["p_min"], row["p_max"]) if row["p_min"] is not None else None
    return {
        "records": row["records"] or 0,
        "solid": row["solid"] or 0,
        "outcomes": row["outcomes"] or 0,
        "materials": materials,
        "o2": o2,
        "pressure": pressure,
    }


def catalog(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for entry in CATALOG:
        stats = _stats(connection, entry["datasets"])
        rows.append(
            {
                **entry,
                "extracted": bool(entry["datasets"]),
                **stats,
            }
        )
    return rows


def ranked(connection: sqlite3.Connection, environment: str = "iss_internal") -> list[dict[str, Any]]:
    rows = catalog(connection)
    for row in rows:
        row["score"] = row["relevance"].get(environment, 1)
    rows.sort(key=lambda row: (-row["score"], -row["extracted"], -row["records"]))
    return rows


def pillars(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = catalog(connection)
    out = []
    for name in ("Prevention", "Detection", "Suppression"):
        members = [row for row in rows if row["pillar"] == name]
        extracted = [row for row in members if row["extracted"]]
        out.append(
            {
                "pillar": name,
                "investigations": len(members),
                "extracted": len(extracted),
                "records": sum(row["records"] for row in members),
                "status": "covered" if extracted else "catalogued only",
                "names": [row["name"] for row in members],
            }
        )
    return out


def readiness(connection: sqlite3.Connection, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    out = []
    for key, label, condition in ENVIRONMENTS:
        rows = gap_map(connection, key, config=cfg)
        anchored = [row for row in rows if row["grade"] == "A"]
        provisional = [row for row in rows if row["grade"] == "B"]
        out.append(
            {
                "key": key,
                "label": label,
                "condition": condition,
                "classes": len(rows),
                "anchored": len(anchored),
                "anchored_names": [row["material_class"] for row in anchored],
                "provisional": len(provisional),
                "provisional_names": [row["material_class"] for row in provisional],
                "gap": len(rows) - len(anchored) - len(provisional),
                "gaps": [
                    {
                        "material_class": row["material_class"],
                        "grade": row["grade"],
                        "missing": MISSING_TESTS.get(
                            row["material_class"], "A pressure-resolved microgravity test."
                        ),
                    }
                    for row in rows
                    if row["grade"] not in {"A", "B"}
                ],
            }
        )
    out.append(
        {
            "key": "suit",
            "label": "Spacesuit (4.3 psia, 100% O₂)",
            "condition": "no corpus coverage",
            "classes": 0,
            "anchored": 0,
            "anchored_names": [],
            "provisional": 0,
            "provisional_names": [],
            "gap": 0,
            "gaps": [],
            "note": (
                "No ingested row reports 4.3 psia or 100% oxygen, so Firebreak does not grade suits. "
                "Grading them would require inventing pressure."
            ),
        }
    )
    return out


def build_investigations(
    connection: sqlite3.Connection,
    environment: str = "iss_internal",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    rows = ranked(connection, environment)
    extracted = [row for row in rows if row["extracted"]]
    totals = {
        "investigations": len(rows),
        "extracted": len(extracted),
        "records": sum(row["records"] for row in rows),
        "outcomes": sum(row["outcomes"] for row in rows),
    }
    totals["all_records"] = connection.execute("SELECT count(*) FROM experiments").fetchone()[0]
    totals["outside_catalog"] = totals["all_records"] - totals["records"]
    return {
        "environment": environment,
        "environments": [
            {"key": key, "label": label, "condition": cond} for key, label, cond in ENVIRONMENTS
        ],
        "totals": totals,
        "investigations": rows,
        "pillars": pillars(connection),
        "readiness": readiness(connection, config),
        "contradictions": list(CONTRADICTIONS),
        "boundary": (
            "Investigation relevance is an analyst weighting for crew-environment fit, "
            "not a NASA score. Catalogued investigations have no extracted rows and are never graded."
        ),
    }
