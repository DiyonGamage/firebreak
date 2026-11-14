# Firebreak

Source-linked, decision-grade screening for spacecraft material flammability.

Team: LFR
Event: NASA Space Apps Challenge 2026, Kandy (virtual)
Challenge: Flame in Freefall — AI-Powered Fire Safety Insights from Microgravity Combustion Data

Firebreak answers four questions for a material and cabin atmosphere: what evidence
exists, what evidence grade it supports, what uncertainty remains, and what test is
needed next. Every result links to a PSI test row, NTRS page, or NASA standard clause.

## What it does

- Grades evidence **A/B/C/D** with a verdict and confidence.
- Shows source-linked microgravity and 1-g evidence, including negative margins.
- Flags out-of-envelope conditions and missing pressure or flow data.
- Ranks material classes by evidence gaps for a selected atmosphere.
- Screens BASS-II CO2-rise severity with a scoped, validated ML model.
- Provides an optional local Cactus 3 assistant with visible tool traces.
- Exports a printable dossier; runs offline after the build.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\build_data.py
python scripts\build_docs.py
python -m uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000. The app reads the local SQLite database and cached
document text; no network is required at runtime.

## Validation

```powershell
python scripts\eval_ml.py
python scripts\audit_extraction.py
python scripts\build_case_studies.py
python -m pytest -q
```

Current results: extraction audit 100% (60/60 fields, 30/30 rows), 38 tests passing,
ML-1 recall@3 1.0 with 0.0 false-match rate, ML-2 4/4 coverage cases, ML-3 AUC 0.834
versus 0.607 for the O2-only baseline. See `docs/validation.md`.

## API

| Route | Purpose |
|---|---|
| `GET /` | Assessment UI, ledger, Gap Map, assistant |
| `GET /assess` | Query-string assessment |
| `GET /api/assess?material=PMMA&atmosphere=iss_internal` | JSON assessment |
| `GET /api/gap-map?atmosphere=iss_internal` | Ranked evidence gaps |
| `GET /api/stats` | Dataset and document counts |
| `GET /api/documents?q=...` | Source-document search |
| `GET /api/assistant?q=...&engine=cactus` | Assistant; Cactus is optional |
| `GET /healthz` | Health check |

The deterministic assistant fallback is the default. Cactus routing is local and
slow on CPU (~12-36 s in testing), so the UI exposes it as an optional checkbox.

## Scope and honesty boundaries

- Screening support, **not certification, flight approval, or a replacement for
  NASA-STD-6001 Test 1**.
- A-grade is currently unreachable from this corpus because the PSI solid-material
  tables do not report pressure; grades cap at B rather than invent pressure.
- ML-3 predicts only BASS-II `delta_CO2 > 0.5` severity for material classes seen in
  training. It does not predict ignition or flame spread.
- SPICE gas-jet data is retained for the library but is not used to grade solids.
- MAPTIS is excluded because it requires authenticated access.

## Data

629 curated rows: 140 graded solid-material tests, 487 gas-fuel tests, and 2 solid rows
with unspecified material; 7 source documents (356 pages). Primary sources are the NASA
PSI API (BASS-II, Saffire-I/II/III, ACME-BRE, SPICE), NTRS, and NASA standards.
Attribution and direct links: `docs/sources.md`.

## Documentation

- `PLAN.md` — scope, architecture, evidence rules, timeline, risks.
- `docs/validation.md` — audit, tests, ML gates, case studies, limitations.
- `docs/sources.md` — dataset and document provenance.
- `docs/case_studies.md` — generated case-study write-up.
- `docs/submission.md` — project-page copy, 90 s video script, checklist, offline demo.
- `artifacts/` — machine-readable validation and ML metrics, plus sample dossier PDFs.
