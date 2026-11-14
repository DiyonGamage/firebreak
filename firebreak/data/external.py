from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from firebreak.config import DB_PATH, NTRS_SITE
from firebreak.data.psi import SCHEMA, _migrate, geometry_type, material_class

BASS2_URL = f"{NTRS_SITE}/citations/20210011385"
TB2605_URL = f"{NTRS_SITE}/citations/20260006043"

# Curated rows transcribed from NASA source documents. Every row carries a
# page-level note; the PSI export remains the primary machine-readable corpus.
RECORDS: list[dict[str, Any]] = [
    {
        "experiment_id": "NTRS-BASS2:PMMA-100um-20.7",
        "source_id": "TM-20210011385 §2.2.4-2.2.5",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "PMMA sheet, 100 micron",
        "geometry": "film",
        "thickness_mm": 0.1,
        "width_mm": 20.0,
        "length_mm": 95.0,
        "o2_initial_pct": 20.7,
        "pressure_kpa": 99.35,
        "flow_velocity_cm_s": 2.5,
        "flow_direction": "opposed",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "spread_rate_mm_s": 2.2,
        "outcome": "spread",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 pp. 22-23 and 38: 100-um PMMA sheet, 20.7% O2, "
            "1 atm, 2.5 cm/s opposed flow; steady spread 2.2 mm/s. Chapter 2 "
            "reports 99.2-99.5 kPa monitored total pressure; 99.35 kPa midpoint used."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "2.2.4 Data Analysis; 2.2.5 Extinction Velocity; 2.3.5",
            "pages": [22, 23, 38],
            "quote": (
                "ambient conditions of 20.7 percent O2, 1 atm, and an opposed-flow "
                "velocity of 2.5 cm/s ... steady spread rate of 2.2 mm/s ... total "
                "pressure ... varied from 99.2 to 99.5 kPa in the tests reported."
            ),
        },
    },
    {
        "experiment_id": "NTRS-BASS2:PMMA-100um-16.0",
        "source_id": "TM-20210011385 §2.2.5",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "PMMA sheet, 100 micron",
        "geometry": "film",
        "thickness_mm": 0.1,
        "width_mm": 20.0,
        "length_mm": 95.0,
        "o2_initial_pct": 16.0,
        "pressure_kpa": 99.35,
        "flow_velocity_cm_s": 2.6,
        "flow_direction": "opposed",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "outcome": "no_spread",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 p. 25: at about 16% O2 the extinction velocity was "
            "about 2.6 cm/s for 100-um PMMA; pressure 99.2-99.5 kPa (midpoint) per p. 38."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "2.2.5 Extinction Velocity",
            "pages": [25, 38],
            "quote": (
                "Tests were also conducted at a lower O2 level of about 16 percent ... "
                "extinction velocities are found to be about 2.6 cm/s for 100 um."
            ),
        },
    },
    {
        "experiment_id": "NTRS-BASS2:SIBAL-GMT96-T7",
        "source_id": "TM-20210011385 Table 7.1, GMT96-T7",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide",
        "thickness_mm": 0.32,
        "width_mm": 22.0,
        "length_mm": 100.0,
        "o2_initial_pct": 21.0,
        "pressure_kpa": 101.325,
        "flow_velocity_cm_s": 10.0,
        "flow_direction": "concurrent",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "outcome": "spread",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 p. 96 Table 7.1 (GMT96-T7, BASS, 2.2 cm, 10 cm/s, "
            "21% O2); steady spread at 21% documented with Fig. 7.2 p. 97. Ambient "
            "pressure 1 atm per §7.1.3 p. 94."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "7.1.3 Experimental; 7.1.4 Results; Table 7.1",
            "pages": [94, 96, 97],
            "quote": (
                "Ambient pressure was 1 atm. ... Figure 7.2 shows flame development "
                "stages of a 2.2-cm sample in 10-cm/s flow and 21 percent O2."
            ),
        },
    },
    {
        "experiment_id": "NTRS-BASS2:SIBAL-GMT45-T4",
        "source_id": "TM-20210011385 Table 7.1, GMT45-T4",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide",
        "thickness_mm": 0.32,
        "width_mm": 22.0,
        "length_mm": 100.0,
        "o2_initial_pct": 18.7,
        "pressure_kpa": 101.325,
        "flow_velocity_cm_s": 2.2,
        "flow_direction": "concurrent",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "outcome": "no_spread",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 p. 96 Table 7.1 (GMT45-T4, 2.2 cm, flow 10 to 2.2 cm/s, "
            "18.7% O2, Quenched); ambient pressure 1 atm per §7.1.3 p. 94."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "7.1.3 Experimental; Table 7.1",
            "pages": [94, 96],
            "quote": "GMT45-T4 | 2.2 | 10 to 2.2 | 18.7 | Quenched",
        },
    },
    {
        "experiment_id": "NTRS-BASS2:SIBAL-GMT175-T9",
        "source_id": "TM-20210011385 Table 7.1, GMT175-T9",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide",
        "thickness_mm": 0.32,
        "width_mm": 22.0,
        "length_mm": 100.0,
        "o2_initial_pct": 16.4,
        "pressure_kpa": 101.325,
        "flow_velocity_cm_s": 10.0,
        "flow_direction": "concurrent",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "outcome": "not_ignited",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 p. 96 Table 7.1 (GMT175-T9, 2.2 cm, 10 cm/s, 16.4% O2, "
            "No ignition); ambient pressure 1 atm per §7.1.3 p. 94."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "7.1.3 Experimental; Table 7.1",
            "pages": [94, 96],
            "quote": "GMT175-T9 | 2.2 | 10 | 16.4 | No ignition",
        },
    },
    {
        "experiment_id": "NTRS-BASS2:SIBAL-GMT216-T25",
        "source_id": "TM-20210011385 Table 7.1, GMT216-T25",
        "source_url": BASS2_URL,
        "dataset": "BASS-II (NTRS)",
        "platform": "ISS",
        "material": "SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide",
        "thickness_mm": 0.32,
        "width_mm": 22.0,
        "length_mm": 100.0,
        "o2_initial_pct": 20.8,
        "pressure_kpa": 101.325,
        "flow_velocity_cm_s": 2.5,
        "flow_direction": "concurrent",
        "gravity": "microgravity",
        "ignition_method": "hot wire",
        "outcome": "ignited",
        "derived": 0,
        "notes": (
            "NASA/TM-20210011385 p. 96 Table 7.1 (GMT216-T25, 2.2 cm, flow 5 to 2.5 cm/s, "
            "20.8% O2, reused sample, ignited); ambient pressure 1 atm per §7.1.3 p. 94."
        ),
        "raw": {
            "citation": "NASA/TM-20210011385",
            "section": "7.1.3 Experimental; Table 7.1",
            "pages": [94, 96],
            "quote": "GMT216-T25 | 2.2 | 5 to 2.5 | 20.8 | Reused, ignited",
        },
    },
    {
        "experiment_id": "TB26-05:natural-37",
        "source_id": "NESC TB 26-05 p. 1, natural webbing",
        "source_url": TB2605_URL,
        "dataset": "TB 26-05 (1-g)",
        "platform": "WSTF",
        "material": "Kevlar/PBI webbing (60% Kevlar, 40% PBI), natural",
        "geometry": "fabric",
        "width_mm": 25.4,
        "o2_initial_pct": 37.0,
        "pressure_kpa": 56.537,
        "gravity": "1-g",
        "ignition_method": "NASA-STD-6001B Test 1, unshielded J",
        "outcome": "no_spread",
        "derived": 1,
        "notes": (
            "NESC TB 26-05 p. 1 (DOC ID 20260006043): 1-in webbing, NASA-STD-6001B "
            "Test 1 unshielded J, MOC 37% at 8.2 psia; natural webbing passed at 37% O2."
        ),
        "raw": {
            "citation": "NESC TB 26-05",
            "doc_id": "20260006043",
            "pages": [1],
            "quote": (
                "The webbings had MOCs of 37% and 35% oxygen for the natural and black "
                "webbing, respectively, at 8.2 psia ... natural version, passed "
                "flammability testing ... at 37% oxygen and 8.2 psia."
            ),
            "interpretation": "MOC pass encoded as no hazardous propagation at the MOC.",
        },
    },
    {
        "experiment_id": "TB26-05:black-35",
        "source_id": "NESC TB 26-05 p. 1, black webbing",
        "source_url": TB2605_URL,
        "dataset": "TB 26-05 (1-g)",
        "platform": "WSTF",
        "material": "Kevlar/PBI webbing (60% Kevlar, 40% PBI), black",
        "geometry": "fabric",
        "width_mm": 25.4,
        "o2_initial_pct": 35.0,
        "pressure_kpa": 56.537,
        "gravity": "1-g",
        "ignition_method": "NASA-STD-6001B Test 1, unshielded J",
        "outcome": "no_spread",
        "derived": 1,
        "notes": (
            "NESC TB 26-05 p. 1 (DOC ID 20260006043): 1-in black webbing, "
            "NASA-STD-6001B Test 1 unshielded J, MOC 35% at 8.2 psia."
        ),
        "raw": {
            "citation": "NESC TB 26-05",
            "doc_id": "20260006043",
            "pages": [1],
            "quote": (
                "The webbings had MOCs of 37% and 35% oxygen for the natural and black "
                "webbing, respectively, at 8.2 psia."
            ),
            "interpretation": "MOC pass encoded as no hazardous propagation at the MOC.",
        },
    },
]

_FIELDS = (
    "experiment_id, source_id, source_url, dataset, platform, material, "
    "material_class, geometry, thickness_mm, width_mm, length_mm, o2_initial_pct, "
    "o2_final_pct, co2_initial_pct, co2_final_pct, delta_co2_pct, pressure_kpa, "
    "flow_velocity_cm_s, flow_direction, gravity, ignition_method, ignition_power_w, "
    "ignition_time_s, burn_time_s, spread_rate_mm_s, spread_rate_1g_mm_s, outcome, "
    "derived, notes, raw_json, provenance_hash"
)
_VALUES = ", ".join(f":{name.strip()}" for name in _FIELDS.split(","))


def _row(spec: dict[str, Any]) -> dict[str, Any]:
    material = spec["material"]
    raw_json = json.dumps(spec["raw"], ensure_ascii=False, sort_keys=True)
    record = {
        "o2_final_pct": None,
        "co2_initial_pct": None,
        "co2_final_pct": None,
        "delta_co2_pct": None,
        "pressure_kpa": None,
        "flow_velocity_cm_s": None,
        "flow_direction": None,
        "ignition_method": None,
        "ignition_power_w": None,
        "ignition_time_s": None,
        "burn_time_s": None,
        "spread_rate_mm_s": None,
        "spread_rate_1g_mm_s": None,
        "length_mm": None,
        "width_mm": None,
        "thickness_mm": None,
        **spec,
        "material_class": material_class(material),
        "geometry": spec.get("geometry") or geometry_type(material),
        "raw_json": raw_json,
    }
    record.pop("raw", None)
    record["provenance_hash"] = hashlib.sha256(
        (spec["source_url"] + raw_json).encode("utf-8")
    ).hexdigest()[:16]
    return record


def ingest_external(db_path: Path = DB_PATH) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    _migrate(connection)
    connection.execute(
        "DELETE FROM experiments WHERE dataset IN ('BASS-II (NTRS)', 'TB 26-05 (1-g)')"
    )
    counts: dict[str, int] = {}
    for spec in RECORDS:
        record = _row(spec)
        connection.execute(
            f"INSERT OR REPLACE INTO experiments ({_FIELDS}) VALUES ({_VALUES})",
            record,
        )
        counts[record["dataset"]] = counts.get(record["dataset"], 0) + 1
    connection.commit()
    connection.close()
    return counts
