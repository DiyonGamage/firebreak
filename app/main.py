from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from firebreak.rules.engine import atmosphere_presets, gap_map, inventory, load_config, open_connection
from firebreak.services.dossier import (
    build_dossier,
    document_metadata,
    get_stats,
    search_documents,
)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(title="Firebreak", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(WEB / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB / "templates"))


def _float(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value not in (None, "") else fallback
    except (TypeError, ValueError):
        return fallback


def _query(
    config: dict[str, Any],
    atmosphere: str,
    material: str,
    o2: str | None,
    pressure: str | None,
    flow: str | None,
) -> dict[str, Any]:
    presets = config["atmospheres"]
    key = atmosphere if atmosphere in presets or atmosphere == "custom" else "iss_internal"
    preset = presets.get(key, presets["iss_internal"])
    return {
        "material": (material or "PMMA").strip(),
        "atmosphere": key,
        "o2": _float(o2, preset["o2_pct"]),
        "pressure": _float(pressure, preset["pressure_psia"]),
        "flow": flow or "",
    }


def _render(
    request: Request,
    query: dict[str, Any],
    library_query: str = "",
    library_hits: list[dict[str, Any]] | None = None,
) -> HTMLResponse:
    config = load_config()
    connection = open_connection()
    try:
        result = build_dossier(
            connection,
            query["material"],
            query["o2"],
            query["pressure"],
            query["flow"] or None,
            config=config,
        )
        context = {
            "request": request,
            "result": result,
            "form": query,
            "presets": [
                {"key": key, **value} for key, value in atmosphere_presets(config).items()
            ],
            "inventory": inventory(connection),
            "gap_rows": gap_map(connection, "iss_internal", config=config),
            "stats": get_stats(connection, config),
            "documents": document_metadata(connection),
            "library_query": library_query,
            "library_hits": library_hits or [],
        }
    finally:
        connection.close()
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    material: str = "PMMA",
    atmosphere: str = "iss_internal",
    o2: str | None = None,
    pressure: str | None = None,
    flow: str | None = None,
):
    config = load_config()
    return _render(request, _query(config, atmosphere, material, o2, pressure, flow))


@app.get("/assess", response_class=HTMLResponse)
def assess_page(
    request: Request,
    material: str = "PMMA",
    atmosphere: str = "iss_internal",
    o2: str | None = None,
    pressure: str | None = None,
    flow: str | None = None,
):
    config = load_config()
    return _render(request, _query(config, atmosphere, material, o2, pressure, flow))


@app.get("/library", response_class=HTMLResponse)
def library_page(
    request: Request,
    material: str = "PMMA",
    atmosphere: str = "iss_internal",
    o2: str | None = None,
    pressure: str | None = None,
    flow: str | None = None,
    q: str = "",
):
    config = load_config()
    query = _query(config, atmosphere, material, o2, pressure, flow)
    connection = open_connection()
    try:
        hits = search_documents(connection, q) if q.strip() else []
    finally:
        connection.close()
    return _render(request, query, library_query=q, library_hits=hits)


@app.get("/api/assess")
def api_assess(
    material: str = "PMMA",
    atmosphere: str = "iss_internal",
    o2: str | None = None,
    pressure: str | None = None,
    flow: str | None = None,
):
    config = load_config()
    query = _query(config, atmosphere, material, o2, pressure, flow)
    connection = open_connection()
    try:
        payload = build_dossier(
            connection,
            query["material"],
            query["o2"],
            query["pressure"],
            query["flow"] or None,
            config=config,
        )
    finally:
        connection.close()
    return JSONResponse(content=jsonable_encoder(payload))


@app.get("/api/gap-map")
def api_gap_map(atmosphere: str = "iss_internal"):
    config = load_config()
    connection = open_connection()
    try:
        payload = gap_map(connection, atmosphere, config=config)
    finally:
        connection.close()
    return JSONResponse(content=jsonable_encoder(payload))


@app.get("/api/stats")
def api_stats():
    connection = open_connection()
    try:
        payload = get_stats(connection)
    finally:
        connection.close()
    return JSONResponse(content=jsonable_encoder(payload))


@app.get("/api/documents")
def api_documents(q: str = ""):
    connection = open_connection()
    try:
        payload = search_documents(connection, q) if q.strip() else document_metadata(connection)
    finally:
        connection.close()
    return JSONResponse(content=jsonable_encoder(payload))


@app.get("/api/assistant")
def api_assistant(q: str = "", engine: str = "fallback"):
    from firebreak.assistant.agent import ask

    return JSONResponse(content=jsonable_encoder(ask(q, engine=engine)))


@app.get("/healthz")
def healthz():
    connection = open_connection()
    try:
        total = connection.execute("SELECT count(*) FROM experiments").fetchone()[0]
        documents = connection.execute("SELECT count(*) FROM documents").fetchone()[0]
    finally:
        connection.close()
    return {"status": "ok", "experiments": total, "documents": documents}
