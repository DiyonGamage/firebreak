from __future__ import annotations

import hashlib
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from firebreak.config import DB_PATH, NTRS_API, RAW_NTRS

DOCUMENTS = {
    "20150020937": "standard",
    "20160000593": "report",
    "20200000557": "paper",
    "20180004258": "report",
    "20170000230": "paper",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    citation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    role TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    text_path TEXT NOT NULL,
    pages_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    pages INTEGER NOT NULL,
    chars INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    downloaded_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Firebreak/0.1 (NASA Space Apps Challenge 2026)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_citation(citation_id: str) -> dict[str, Any]:
    try:
        data = json.loads(_http_get(f"{NTRS_API}/{citation_id}", timeout=60).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def download_pdf(citation_id: str, refresh: bool = False) -> tuple[bytes, Path]:
    RAW_NTRS.mkdir(parents=True, exist_ok=True)
    path = RAW_NTRS / f"{citation_id}.pdf"
    if path.exists() and not refresh:
        return path.read_bytes(), path
    url = f"{NTRS_API}/{citation_id}/downloads/{citation_id}.pdf"
    payload = _http_get(url)
    if not payload.startswith(b"%PDF"):
        raise ValueError(f"{citation_id}: response is not a PDF")
    path.write_bytes(payload)
    return payload, path


def extract_pages(payload: bytes) -> list[dict[str, Any]]:
    import pymupdf

    document = pymupdf.open(stream=payload, filetype="pdf")
    pages = []
    for index, page in enumerate(document, start=1):
        pages.append({"page": index, "text": page.get_text()})
    return pages


def ingest_documents(db_path: Path = DB_PATH, refresh: bool = False) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    counts: dict[str, int] = {}
    for citation_id, role in DOCUMENTS.items():
        payload, pdf_path = download_pdf(citation_id, refresh=refresh)
        pages = extract_pages(payload)
        text = "\n\n".join(page["text"] for page in pages)
        text_path = RAW_NTRS / f"{citation_id}.txt"
        pages_path = RAW_NTRS / f"{citation_id}.pages.json"
        text_path.write_text(text, encoding="utf-8")
        pages_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        citation = fetch_citation(citation_id)
        title = (
            citation.get("title")
            or citation.get("stiTypeDetails")
            or f"NTRS {citation_id}"
        )
        connection.execute(
            "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                citation_id,
                title,
                role,
                str(pdf_path),
                str(text_path),
                str(pages_path),
                hashlib.sha256(payload).hexdigest(),
                len(pages),
                len(text),
                f"https://ntrs.nasa.gov/citations/{citation_id}",
                _now(),
            ),
        )
        counts[citation_id] = len(text)
    connection.commit()
    connection.close()
    return counts
