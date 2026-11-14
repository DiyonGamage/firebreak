from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from firebreak.data.ntrs import ingest_documents
from firebreak.data.standards import ingest_standards


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    counts = ingest_documents(refresh=args.refresh)
    counts.update(ingest_standards(refresh=args.refresh))
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
