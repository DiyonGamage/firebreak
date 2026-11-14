from __future__ import annotations

import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.config import DB_PATH, RAW_PSI
from firebreak.rules.engine import open_connection

FILES = {
    "BASS-II": "PSI-25_PSI-25_Experimental_table_BASS-II.csv",
    "Saffire-I": "PSI-98_PSI-98_Experimental_table_SAFFIRE-1.csv",
    "Saffire-II": "PSI-99_PSI-99_Experimental_table_SAFFIRE-2.csv",
    "Saffire-III": "PSI-100_PSI-100_Experimental_table_SAFFIRE-3.csv",
    "ACME-BRE": "PSI-20_PSI-20_Experimental_table_ACME_BRE.csv",
    "SPICE": "PSI-107_PSI-107_Experimental_table_Spice.csv",
}

SAMPLE_SIZE = {
    "BASS-II": 10,
    "Saffire-I": 3,
    "Saffire-II": 6,
    "Saffire-III": 3,
    "ACME-BRE": 4,
    "SPICE": 6,
}


def _number(value: Any) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def _raw_rows(dataset: str) -> list[dict[str, str]]:
    path = RAW_PSI / FILES[dataset]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _norm_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _preserved(raw: dict[str, Any], source: dict[str, str]) -> bool:
    normalized_source = {_norm_key(key): value for key, value in source.items()}
    if len(raw) != len(normalized_source):
        return False
    for key, value in raw.items():
        source_value = normalized_source.get(_norm_key(key))
        if source_value is None:
            return False
        if _norm_text(value) != _norm_text(source_value):
            return False
    return True


def main() -> None:
    connection = open_connection()
    random.seed(42)
    details = []
    field_total = 0
    field_matches = 0
    preserved_total = 0
    sampled_total = 0
    for dataset, sample_size in SAMPLE_SIZE.items():
        rows = connection.execute(
            "SELECT * FROM experiments WHERE dataset = ?", (dataset,)
        ).fetchall()
        source_rows = _raw_rows(dataset)
        for row in random.sample(rows, min(sample_size, len(rows))):
            sampled_total += 1
            raw = json.loads(row["raw_json"])
            preserved = any(_preserved(raw, source) for source in source_rows)
            preserved_total += int(preserved)
            checks = []
            if dataset == "BASS-II":
                checks = [
                    ("material", _norm_text(raw.get("Fuel Sample Material")), _norm_text(row["material"])),
                    (
                        "o2_initial_pct",
                        _number(raw.get("Calibrated initial O2 % by vol")),
                        row["o2_initial_pct"],
                    ),
                    (
                        "co2_initial_pct",
                        _number(raw.get("Initial CO2 % by vol")),
                        row["co2_initial_pct"],
                    ),
                    (
                        "co2_final_pct",
                        _number(raw.get("Final CO2 % by vol")),
                        row["co2_final_pct"],
                    ),
                ]
            elif dataset.startswith("Saffire"):
                checks = [
                    ("material", _norm_text(raw.get("Material") or raw.get("Fuel Sample Material")), _norm_text(row["material"])),
                    ("o2_initial_pct", _number(raw.get("Percent O2 (Note 1)") or raw.get("Percent O2")), row["o2_initial_pct"]),
                ]
            details.append(
                {
                    "dataset": dataset,
                    "experiment_id": row["experiment_id"],
                    "field": "raw_row",
                    "source_value": "exact",
                    "database_value": "exact" if preserved else "mismatch",
                    "raw_preserved": preserved,
                }
            )
            for name, expected, actual in checks:
                field_total += 1
                matched = expected == actual or (
                    isinstance(expected, float) and expected == actual
                )
                if name == "material" and expected == "" and actual == "unspecified":
                    matched = True
                if matched:
                    field_matches += 1
                else:
                    details.append(
                        {
                            "dataset": dataset,
                            "experiment_id": row["experiment_id"],
                            "field": name,
                            "source_value": expected,
                            "database_value": actual,
                            "raw_preserved": preserved,
                        }
                    )
    accuracy = round(field_matches / field_total, 3) if field_total else 1.0
    payload = {
        "sample_size": sampled_total,
        "raw_rows_preserved": preserved_total,
        "field_checks": field_total,
        "field_matches": field_matches,
        "field_accuracy": accuracy,
        "gate": {"field_accuracy_min": 0.95, "passed": accuracy >= 0.95},
        "method": "Deterministic stratified sample; exact raw-row match and independent field parse against cached PSI CSV.",
        "details": details,
    }
    output = ROOT / "artifacts" / "extraction_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "details"}, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
