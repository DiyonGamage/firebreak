from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from firebreak.config import DB_PATH, RAW_NTRS
from firebreak.data.ntrs import SCHEMA, _http_get, _now, extract_pages

STANDARDS = {
    "JSC-29353D": {
        "url": (
            "https://standards.nasa.gov/system/files/tmp/"
            "JSC%2029353D%20Flammability%20Configuration%20Analysis%20for%20Spacecraft%20Applications.pdf"
        ),
        "title": "Flammability Configuration Analysis for Spacecraft Applications (JSC 29353D)",
        "role": "standard",
    },
    "NASA-STD-6001B": {
        "url": (
            "https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/"
            "2025_06_25_NASA-STD-6001B_w_Change_3_FINAL_Admin-Change-FINAL.pdf"
        ),
        "title": (
            "Flammability, Offgassing, and Compatibility Requirements and Test Procedures "
            "(NASA-STD-6001B w/Change 3)"
        ),
        "role": "standard",
    },
}


def _download(key: str, url: str, refresh: bool = False) -> tuple[bytes, Path]:
    RAW_NTRS.mkdir(parents=True, exist_ok=True)
    path = RAW_NTRS / f"{key}.pdf"
    if path.exists() and not refresh:
        return path.read_bytes(), path
    payload = _http_get(url)
    if not payload.startswith(b"%PDF"):
        raise ValueError(f"{key}: response is not a PDF")
    path.write_bytes(payload)
    return payload, path


def ingest_standards(db_path: Path = DB_PATH, refresh: bool = False) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    counts: dict[str, int] = {}
    for key, meta in STANDARDS.items():
        payload, pdf_path = _download(key, meta["url"], refresh=refresh)
        pages = extract_pages(payload)
        text = "\n\n".join(page["text"] for page in pages)
        text_path = RAW_NTRS / f"{key}.txt"
        pages_path = RAW_NTRS / f"{key}.pages.json"
        text_path.write_text(text, encoding="utf-8")
        pages_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        connection.execute(
            "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                key,
                meta["title"],
                meta["role"],
                str(pdf_path),
                str(text_path),
                str(pages_path),
                hashlib.sha256(payload).hexdigest(),
                len(pages),
                len(text),
                meta["url"],
                _now(),
            ),
        )
        counts[key] = len(text)
    connection.commit()
    connection.close()
    return counts
