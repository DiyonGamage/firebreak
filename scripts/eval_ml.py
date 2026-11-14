from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.ml.coverage import evaluate_coverage
from firebreak.ml.evidence import evaluate_matcher
from firebreak.ml.severity import train_and_evaluate
from firebreak.rules.engine import open_connection


def main() -> None:
    connection = open_connection()
    evidence = evaluate_matcher(connection)
    coverage = evaluate_coverage(connection)
    severity = train_and_evaluate(connection, save_artifact=True)["metrics"]
    payload = {
        "evidence_matcher": evidence,
        "coverage_detector": coverage,
        "severity_classifier": severity,
    }
    output = ROOT / "artifacts" / "ml_eval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
