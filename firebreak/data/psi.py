from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from firebreak.config import (
    DB_PATH,
    PSI_DOWNLOAD,
    PSI_META,
    PSI_PAGE,
    RAW_META,
    RAW_PSI,
)

DATASETS = {
    "PSI-25": "BASS-II",
    "PSI-98": "Saffire-I",
    "PSI-99": "Saffire-II",
    "PSI-100": "Saffire-III",
    "PSI-20": "ACME-BRE",
    "PSI-107": "SPICE",
}

# Non-flammability investigations: smoke aerosol (detection), droplet extinction
# (suppression) and test logs. They are stored apart from `experiments` so they can
# never enter a material grade.
AUX = {
    "PSI-101": ("SAME-R", "smoke aerosol"),
    "PSI-102": ("SAME", "smoke aerosol"),
    "PSI-106": ("SLICE", "test log"),
    "PSI-69": ("FLEX", "droplet extinction"),
    "PSI-68": ("FLEX-2", "test matrix"),
    "PSI-26": ("BASS", "test log"),
}

AUX_ID = {
    "SAME-R": ("SAME Test #",),
    "SAME": ("Sample #",),
    "SLICE": ("Test Date",),
    "FLEX": ("FLEX Test #", "FLEX Identifier"),
    "FLEX-2": ("Sample (Fuel Type)",),
    "BASS": ("As Run Test #", "Test #"),
}

AUX_MATERIAL = {
    "SAME-R": ("Sample Type", "Description"),
    "SAME": ("Sample Material", "Sample Material "),
    "SLICE": ("Fuel Type",),
    "FLEX": ("Fuel",),
    "FLEX-2": ("Sample (Fuel Type)",),
    "BASS": ("Fuel Sample Material",),
}

DATASETS.update({acc: name for acc, (name, _kind) in AUX.items()})

PLATFORM = {
    "BASS-II": "ISS",
    "Saffire-I": "Cygnus",
    "Saffire-II": "Cygnus",
    "Saffire-III": "Cygnus",
    "ACME-BRE": "ISS",
    "SPICE": "ISS",
    "SAME": "ISS",
    "SAME-R": "ISS",
    "SLICE": "ISS",
    "FLEX": "ISS",
    "FLEX-2": "ISS",
    "BASS": "ISS",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_files (
    dataset TEXT NOT NULL,
    file_name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    PRIMARY KEY (dataset, file_name)
);
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    dataset TEXT NOT NULL,
    platform TEXT NOT NULL,
    material TEXT NOT NULL,
    material_class TEXT NOT NULL,
    geometry TEXT NOT NULL,
    thickness_mm REAL,
    width_mm REAL,
    length_mm REAL,
    o2_initial_pct REAL,
    o2_final_pct REAL,
    co2_initial_pct REAL,
    co2_final_pct REAL,
    delta_co2_pct REAL,
    pressure_kpa REAL,
    flow_velocity_cm_s REAL,
    flow_direction TEXT,
    gravity TEXT NOT NULL,
    ignition_method TEXT,
    ignition_power_w REAL,
    ignition_time_s REAL,
    burn_time_s REAL,
    spread_rate_mm_s REAL,
    spread_rate_1g_mm_s REAL,
    outcome TEXT,
    derived INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    raw_json TEXT NOT NULL,
    provenance_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investigation_records (
    dataset TEXT NOT NULL,
    record_id TEXT NOT NULL,
    material TEXT NOT NULL,
    record_kind TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,
    PRIMARY KEY (dataset, record_id)
);
CREATE INDEX IF NOT EXISTS idx_experiments_dataset ON experiments(dataset);
CREATE INDEX IF NOT EXISTS idx_experiments_material_class ON experiments(material_class);
CREATE INDEX IF NOT EXISTS idx_experiments_o2 ON experiments(o2_initial_pct);
"""

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Firebreak/0.1 (NASA Space Apps Challenge 2026)",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _pick(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        key = _key(name)
        if key in row:
            return row[key]
    return None


def parse_number(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith(("note", "see", "fig", "figure", "pre-test")):
        return None
    if "note " in lowered or "see fig" in lowered:
        return None
    if lowered in {
        "n/a",
        "na",
        "none",
        "null",
        "insignificant",
        "complete",
        "acceleratory",
        "-",
        "no",
    }:
        return None
    match = _NUM.search(text.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def parse_length_mm(value: Any, default_unit: str = "mm") -> float | None:
    text = _clean(value)
    if not text:
        return None
    lowered = text.lower()

    fraction = re.search(r"(\d+)\s*/\s*(\d+)\s*\"", lowered)
    if fraction:
        inches = float(fraction.group(1)) / float(fraction.group(2))
        return round(inches * 25.4, 3)

    leading_zero = re.match(r"^0(\d{2})\s*(mm|cm)?$", lowered)
    if leading_zero:
        number = float("0." + leading_zero.group(1))
        unit = leading_zero.group(2) or default_unit
        return _convert_mm(number, unit)

    match = re.search(r"(\d+(?:\.\d+)?)\s*(micron|microns|um|µm|mm|cm|\")", lowered)
    if match:
        return _convert_mm(float(match.group(1)), match.group(2))

    number = parse_number(lowered)
    if number is None:
        return None
    return _convert_mm(number, default_unit)


def _convert_mm(value: float, unit: str) -> float:
    unit = unit.replace("µ", "u").lower()
    if unit in {"micron", "microns", "um"}:
        return round(value / 1000.0, 6)
    if unit == "cm":
        return round(value * 10.0, 6)
    if unit == '"':
        return round(value * 25.4, 6)
    return round(value, 6)


def material_class(material: str) -> str:
    text = _clean(material).lower()
    if "pmma" in text and "nomex" in text:
        return "PMMA/Nomex"
    if "pmma" in text or "methacrylate" in text or "acrylic" in text or "plexiglas" in text:
        return "PMMA"
    if "sibal" in text or "cotton-fiberglass" in text:
        return "SIBAL"
    if "nomex" in text:
        return "Nomex"
    if "silicone" in text:
        return "Silicone"
    if "kevlar" in text or "pbi" in text:
        return "Kevlar/PBI"
    if any(
        token in text
        for token in (
            "polyethylene",
            "polypropylene",
            "polycarbonate",
            "polyester",
            "nylon",
            "pvc",
            "ptfe",
            "teflon",
            "wool",
            "paper",
            "wood",
            "cotton",
        )
    ):
        return "Other"
    if "rod" in text and ("clear" in text or "black" in text):
        return "PMMA"
    if ("film" in text or "micron" in text) and "gas" not in text:
        return "PMMA"
    if any(token in text for token in ("c2h4", "ch4", "ethylene", "methane")):
        return "Gas fuel"
    return "Other"


def geometry_type(material: str) -> str:
    text = _clean(material).lower()
    if "film" in text:
        return "film"
    if "rod" in text:
        return "rod"
    if "fabric" in text:
        return "fabric"
    if "slab" in text or "thick" in text:
        return "slab"
    if any(token in text for token in ("c2h4", "ch4", "ethylene", "methane")):
        return "gas jet"
    return "unspecified"


def _material_thickness_mm(material: str) -> float | None:
    text = _clean(material).lower()
    if not text:
        return None
    if "rod" in text:
        return parse_length_mm(text, "mm")
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(micron|microns|um|µm|mm)\b",
        text,
    )
    if match:
        return _convert_mm(float(match.group(1)), match.group(2))
    match = re.search(r"(\d+(?:\.\d+)?)\s*cm\s+(?:thick|thickness)", text)
    if match:
        return _convert_mm(float(match.group(1)), "cm")
    return None


def _material_width_mm(material: str) -> float | None:
    text = _clean(material).lower()
    if not text:
        return None
    if "rod" in text:
        return _material_thickness_mm(material)
    match = re.search(r"(\d+(?:\.\d+)?)\s*cm\b", text)
    if match:
        return _convert_mm(float(match.group(1)), "cm")
    match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:wide|width)", text)
    if match:
        return _convert_mm(float(match.group(1)), "mm")
    return None


def load_metadata(acc: str, refresh: bool = False) -> dict[str, Any]:
    RAW_META.mkdir(parents=True, exist_ok=True)
    path = RAW_META / f"{acc}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data = json.loads(_http_get(PSI_META.format(acc=acc)).decode("utf-8"))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def download_tables(acc: str, meta: dict[str, Any], refresh: bool = False) -> list[dict[str, Any]]:
    RAW_PSI.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for entry in meta.get("experimentalTable") or []:
        file_name = _clean(entry.get("file_name"))
        if not file_name:
            continue
        file_id = entry["_id"]["$oid"]
        path = RAW_PSI / f"{acc}_{_safe_name(file_name)}"
        if path.exists() and not refresh:
            payload = path.read_bytes()
        else:
            presigned = _http_get(
                PSI_DOWNLOAD.format(acc=acc, fid=file_id, version=entry.get("version", 1))
            ).decode("utf-8").strip()
            payload = _http_get(presigned)
            path.write_bytes(payload)
            time.sleep(0.2)
        digest = hashlib.sha256(payload).hexdigest()
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = payload.decode("cp1252")
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            continue
        header = [_key(cell) for cell in rows[0]]
        records = []
        for raw in rows[1:]:
            if not any(_clean(cell) for cell in raw):
                continue
            padded = raw + [""] * (len(header) - len(raw))
            records.append(dict(zip(header, padded)))
        outputs.append(
            {
                "accession": acc,
                "dataset": DATASETS[acc],
                "file_name": file_name,
                "path": path,
                "sha256": digest,
                "bytes": len(payload),
                "source_url": PSI_PAGE.format(acc=acc),
                "rows": records,
            }
        )
    return outputs


def _base_record(table: dict[str, Any], source_id: str, material: str, derived: int = 0) -> dict[str, Any]:
    acc = table["accession"]
    dataset = table["dataset"]
    material = _clean(material) or "unspecified"
    return {
        "experiment_id": f"{acc}:{source_id}",
        "source_id": source_id,
        "source_url": table["source_url"],
        "dataset": dataset,
        "platform": PLATFORM.get(dataset, "unknown"),
        "material": material,
        "material_class": material_class(material),
        "geometry": geometry_type(material),
        "thickness_mm": None,
        "width_mm": None,
        "length_mm": None,
        "o2_initial_pct": None,
        "o2_final_pct": None,
        "co2_initial_pct": None,
        "co2_final_pct": None,
        "delta_co2_pct": None,
        "pressure_kpa": None,
        "flow_velocity_cm_s": None,
        "flow_direction": None,
        "gravity": "microgravity",
        "ignition_method": None,
        "ignition_power_w": None,
        "ignition_time_s": None,
        "burn_time_s": None,
        "spread_rate_mm_s": None,
        "spread_rate_1g_mm_s": None,
        "outcome": None,
        "derived": derived,
        "notes": "",
        "raw_json": json.dumps(table.get("raw"), ensure_ascii=False, sort_keys=True),
        "provenance_hash": "",
    }


def _normalize_bass(table: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any]:
    material = _clean(_pick(row, "Fuel Sample Material"))
    test_id = _clean(_pick(row, "Test #")) or f"row-{index}"
    record = _base_record(table, test_id, material)
    record["thickness_mm"] = _material_thickness_mm(material)
    record["width_mm"] = _material_width_mm(material)
    record["o2_initial_pct"] = parse_number(
        _pick(row, "Calibrated initial O2 % by vol", "Calibrated  initial O2 % by vol ")
    )
    record["o2_final_pct"] = parse_number(_pick(row, "Calibrated final O2 % by vol"))
    record["co2_initial_pct"] = parse_number(_pick(row, "Initial CO2 % by vol"))
    record["co2_final_pct"] = parse_number(_pick(row, "Final CO2 % by vol"))
    if record["co2_initial_pct"] is not None and record["co2_final_pct"] is not None:
        record["delta_co2_pct"] = round(record["co2_final_pct"] - record["co2_initial_pct"], 3)
    record["flow_direction"] = None
    record["notes"] = (
        f"flow_restrictor={_clean(_pick(row, 'Flow restrictor'))}; "
        f"fan={_clean(_pick(row, 'Fan display'))}; air={_clean(_pick(row, 'Air display'))}; "
        f"frames={_clean(_pick(row, 'Total Frames Shot'))}; "
        f"CO2_init={_clean(_pick(row, 'Initial CO2 % by vol'))}; "
        f"CO2_final={_clean(_pick(row, 'Final CO2 % by vol'))}; "
        f"CO_init={_clean(_pick(row, 'Initial CO (ppm)'))}; "
        f"CO_final={_clean(_pick(row, 'Final CO (ppm)'))}"
    )
    return record


def _normalize_saffire(table: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any] | None:
    material = _clean(_pick(row, "Material"))
    sample = _clean(_pick(row, "Sample Number"))
    if not material and not sample:
        return None
    if material.lower().startswith("pre-test") or sample.upper().startswith("F"):
        return None
    if sample.lower().startswith("note") or material.lower().startswith("note"):
        return None
    source_id = sample or f"row-{index}"
    record = _base_record(table, source_id, material)
    record["thickness_mm"] = parse_length_mm(
        _pick(row, "Samle Thickness", "Sample Thickness (cm)", "Sample Thickness"), "mm"
    )
    record["length_mm"] = parse_length_mm(_pick(row, "Sample Length (cm)", "Sample Length"), "cm")
    record["width_mm"] = parse_length_mm(_pick(row, "Sample Width (cm)", "Sample Width"), "cm")
    record["o2_initial_pct"] = parse_number(_pick(row, "Percent O2 (Note 1)", "Percent O2"))
    record["flow_velocity_cm_s"] = parse_number(_pick(row, "Air Flow (cm/s)", "Air Flow"))
    record["flow_direction"] = _clean(_pick(row, "Flow Direction", "Direction")) or None
    record["ignition_power_w"] = parse_number(_pick(row, "Ignition Power (W)"))
    record["ignition_time_s"] = parse_number(_pick(row, "Ignition Time (s)"))
    burn_text = _clean(_pick(row, "Burn Time (s)"))
    record["burn_time_s"] = parse_number(burn_text)
    if burn_text.lower() == "insignificant":
        record["notes"] = "burn time reported as insignificant"

    micro_spread_key = next(
        (k for k in row if "spread" in k.lower() and "1-g" not in k.lower()),
        None,
    )
    one_g_spread_key = next(
        (k for k in row if "spread" in k.lower() and "1-g" in k.lower()),
        None,
    )
    micro_burn_key = next(
        (k for k in row if "burn length" in k.lower() and "1-g" not in k.lower()),
        None,
    )
    micro_spread = parse_number(row.get(micro_spread_key)) if micro_spread_key else None
    one_g_spread = parse_number(row.get(one_g_spread_key)) if one_g_spread_key else None
    record["spread_rate_mm_s"] = micro_spread
    record["spread_rate_1g_mm_s"] = one_g_spread
    micro_burn = _clean(row.get(micro_burn_key)) if micro_burn_key else ""

    if micro_spread is not None:
        record["outcome"] = "spread" if micro_spread > 0 else "no_spread"
        record["derived"] = 1
    elif "29" in micro_burn or "complete" in micro_burn.lower():
        record["outcome"] = "spread"
        record["derived"] = 1
    elif "~ 0" in micro_burn or micro_burn.lower() == "n/a":
        record["outcome"] = "no_spread"
        record["derived"] = 1
    return record


def _normalize_saffire_meta(table: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any] | None:
    material = _clean(_pick(row, "Material"))
    sample = _clean(_pick(row, "Sample Number"))
    if not material and not sample:
        return None
    record = _base_record(table, sample or f"row-{index}", material)
    record["thickness_mm"] = parse_length_mm(_pick(row, "Sample Thickness"), "cm")
    record["length_mm"] = parse_length_mm(_pick(row, "Sample Length"), "cm")
    record["width_mm"] = parse_length_mm(_pick(row, "Sample Width"), "cm")
    record["flow_velocity_cm_s"] = parse_number(_pick(row, "Air Flow"))
    record["flow_direction"] = _clean(_pick(row, "Direction")) or None
    record["notes"] = "metadata-only row; no result columns in experimental table"
    return record


def _normalize_acme(table: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any] | None:
    fuel = _clean(_pick(row, "Fuel Bottle"))
    if not fuel:
        return None
    date_id = "-".join(
        part
        for part in (
            _clean(_pick(row, "Year")),
            _clean(_pick(row, "Month")),
            _clean(_pick(row, "Date")),
        )
        if part
    )
    record = _base_record(table, date_id or f"row-{index}", fuel)
    record["geometry"] = "gas jet"
    record["material_class"] = "Gas fuel"
    record["o2_initial_pct"] = parse_number(_pick(row, "Oxygen Conc (percent)"))
    ignited = parse_number(_pick(row, "Flames Ignited"))
    if ignited is not None:
        record["outcome"] = "ignited" if ignited > 0 else "not_ignited"
        record["derived"] = 1
    record["notes"] = (
        f"burner_size_mm={_clean(_pick(row, 'Burner Size (mm)'))}; "
        f"o2_values={_clean(_pick(row, 'Oxygen Conc (percent)'))}; "
        f"ignitions={_clean(_pick(row, 'Flames Ignited'))}; "
        f"{_clean(_pick(row, 'Notes'))}"
    )
    return record


def _normalize_spice(table: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any] | None:
    fuel = _clean(_pick(row, "Fuel"))
    if not fuel:
        return None
    source_id = _clean(_pick(row, "GMT date")) or f"row-{index}"
    record = _base_record(table, source_id, fuel)
    record["geometry"] = "gas jet"
    record["material_class"] = "Gas fuel"
    record["flow_velocity_cm_s"] = parse_number(_pick(row, "Air Rate (cm/s)"))
    record["notes"] = (
        f"nozzle_mm={_clean(_pick(row, 'Nozzle (mm)'))}; "
        f"fuel_rate_sccm={_clean(_pick(row, 'Fuel Rate (sccm)'))}; "
        f"fuel_rate_mg_s={_clean(_pick(row, 'Fuel Rate (mg/s)'))}; "
        f"hc_fuel_rate_mg_s={_clean(_pick(row, 'HC Fuel Rate (mg/s)'))}"
    )
    return record


NORMALIZERS = {
    "BASS-II": _normalize_bass,
    "Saffire-I": _normalize_saffire,
    "Saffire-II": _normalize_saffire,
    "Saffire-III": _normalize_saffire_meta,
    "ACME-BRE": _normalize_acme,
    "SPICE": _normalize_spice,
}


def _migrate(connection: sqlite3.Connection) -> None:
    existing = {
        row[1] for row in connection.execute("PRAGMA table_info(experiments)").fetchall()
    }
    for name in ("co2_initial_pct", "co2_final_pct", "delta_co2_pct"):
        if name not in existing:
            connection.execute(f"ALTER TABLE experiments ADD COLUMN {name} REAL")


def ingest_all(db_path: Path = DB_PATH, refresh: bool = False) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    _migrate(connection)
    connection.execute("DELETE FROM experiments")
    counts: dict[str, int] = {}
    seen: set[str] = set()

    for acc, dataset in DATASETS.items():
        if dataset not in NORMALIZERS:
            continue
        meta = load_metadata(acc, refresh=refresh)
        tables = download_tables(acc, meta, refresh=refresh)
        normalizer = NORMALIZERS[dataset]
        inserted = 0
        for table in tables:
            digest = hashlib.sha256(
                (table["sha256"] + json.dumps(table, sort_keys=True, default=str)).encode("utf-8")
            ).hexdigest()
            connection.execute(
                "INSERT OR REPLACE INTO raw_files VALUES (?, ?, ?, ?, ?, ?)",
                (
                    dataset,
                    table["file_name"],
                    table["sha256"],
                    table["bytes"],
                    table["source_url"],
                    _now(),
                ),
            )
            for index, raw in enumerate(table["rows"], start=1):
                table_row = {**table, "raw": raw}
                record = normalizer(table_row, raw, index)
                if record is None:
                    continue
                experiment_id = record["experiment_id"]
                if experiment_id in seen:
                    experiment_id = f"{experiment_id}#{index}"
                    record["experiment_id"] = experiment_id
                seen.add(experiment_id)
                record["provenance_hash"] = hashlib.sha256(
                    (digest + json.dumps(raw, sort_keys=True, default=str)).encode("utf-8")
                ).hexdigest()[:16]
                connection.execute(
                    """
                    INSERT OR REPLACE INTO experiments (
                        experiment_id, source_id, source_url, dataset, platform,
                        material, material_class, geometry, thickness_mm, width_mm,
                        length_mm, o2_initial_pct, o2_final_pct,
                        co2_initial_pct, co2_final_pct, delta_co2_pct,
                        pressure_kpa,
                        flow_velocity_cm_s, flow_direction, gravity, ignition_method,
                        ignition_power_w, ignition_time_s, burn_time_s,
                        spread_rate_mm_s, spread_rate_1g_mm_s, outcome, derived,
                        notes, raw_json, provenance_hash
                    ) VALUES (
                        :experiment_id, :source_id, :source_url, :dataset, :platform,
                        :material, :material_class, :geometry, :thickness_mm, :width_mm,
                        :length_mm, :o2_initial_pct, :o2_final_pct,
                        :co2_initial_pct, :co2_final_pct, :delta_co2_pct,
                        :pressure_kpa,
                        :flow_velocity_cm_s, :flow_direction, :gravity, :ignition_method,
                        :ignition_power_w, :ignition_time_s, :burn_time_s,
                        :spread_rate_mm_s, :spread_rate_1g_mm_s, :outcome, :derived,
                        :notes, :raw_json, :provenance_hash
                    )
                    """,
                    record,
                )
                inserted += 1
        counts[dataset] = inserted

    connection.commit()
    connection.close()
    summary = {
        "generated_at": _now(),
        "db_path": str(db_path),
        "counts": counts,
        "total": sum(counts.values()),
    }
    (db_path.parent / "ingest_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return counts


def ingest_auxiliary(db_path: Path = DB_PATH, refresh: bool = False) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    connection.execute("DELETE FROM investigation_records")
    counts: dict[str, int] = {}

    for acc, (dataset, kind) in AUX.items():
        meta = load_metadata(acc, refresh=refresh)
        tables = download_tables(acc, meta, refresh=refresh)
        inserted = 0
        for table in tables:
            connection.execute(
                "INSERT OR REPLACE INTO raw_files VALUES (?, ?, ?, ?, ?, ?)",
                (
                    dataset,
                    table["file_name"],
                    table["sha256"],
                    table["bytes"],
                    table["source_url"],
                    _now(),
                ),
            )
            seen: set[str] = set()
            for index, raw in enumerate(table["rows"], start=1):
                material = _clean(_pick(raw, *AUX_MATERIAL[dataset]))
                record_id = _clean(_pick(raw, *AUX_ID[dataset])) or f"row-{index}"
                if not material:
                    continue
                if record_id in seen:
                    record_id = f"{record_id}#{index}"
                seen.add(record_id)
                connection.execute(
                    "INSERT OR REPLACE INTO investigation_records VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        dataset,
                        record_id,
                        material,
                        kind,
                        table["source_url"],
                        json.dumps(raw, ensure_ascii=False, sort_keys=True),
                        hashlib.sha256(
                            (table["sha256"] + json.dumps(raw, sort_keys=True, default=str)).encode(
                                "utf-8"
                            )
                        ).hexdigest()[:16],
                    ),
                )
                inserted += 1
        counts[dataset] = inserted

    connection.commit()
    connection.close()
    return counts
