from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.data.external import ingest_external
from firebreak.data.psi import ingest_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    counts = ingest_all(refresh=args.refresh)
    counts.update(ingest_external())
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
