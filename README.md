# Firebreak

Source-linked, decision-grade screening for spacecraft material flammability.

Team: LFR
Event: NASA Space Apps Challenge 2026, Kandy (virtual)
Challenge: Flame in Freefall — AI-Powered Fire Safety Insights from Microgravity Combustion Data
Repo: https://github.com/DiyonGamage/firebreak · License: MIT
Project site: https://diyongamage.github.io/firebreak/

Firebreak answers four questions for a material and cabin atmosphere: what evidence
exists, what evidence grade it supports, what uncertainty remains, and what test is
needed next. Every result links to a PSI test row, NTRS page, or NASA standard clause.

## What it does

- Grades evidence **A/B/C/D** with a verdict and confidence.
- Shows source-linked microgravity and 1-g evidence, including negative margins.
- Flags out-of-envelope conditions and missing pressure or flow data.
- Ranks material classes by evidence gaps for a selected atmosphere.
- Screens BASS-II CO2-rise severity with one monotonic model, 80% conformal sets, and
  explicit abstention outside training support.
- Provides an optional local Cactus Needle assistant with visible tool traces.
- Exports a printable dossier; runs offline after the build.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000. The repo ships the built SQLite corpus and cached
document text, so the demo needs no build step and no network. To rebuild from the
original sources (network required):

```powershell
python scripts\build_data.py
python scripts\build_docs.py
```

## Validation

```powershell
python scripts\eval_ml.py
python scripts\audit_extraction.py
python scripts\build_case_studies.py
python -m pytest -q
python scripts\smoke_e2e.py --cactus
```

Current results: extraction audit 100% (60/60 fields, 30/30 rows), ML-1 recall@3 1.0
with 0.0 false-match rate, ML-2 5/5 coverage cases, ML-3 AUC 0.811 versus 0.605 for
the O2-only baseline, with 80% conformal sets covering 89.6% of supported-class cases
and abstention outside PMMA/SIBAL or 13.6-22.2% O2. The end-to-end smoke test passes
against the running app: 7 API assessments, Gap Map, document search, 5 assistant
routes, browser form + assistant, and one live Cactus route. See `docs/validation.md`.

## API

| Route | Purpose |
|---|---|
| `GET /` | Evidence dashboard: corpus KPIs, ranked findings, material × atmosphere matrix |
| `GET /assess` | Query-string dossier: grade card, ledger, Gap Map, assistant |
| `GET /library` | Full-text search over the indexed NASA source documents |
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
- Grade A requires a documented microgravity outcome under a pressure-bearing
  condition. Only the page-cited BASS-II NTRS rows currently satisfy that, so PMMA
  and SIBAL at ISS-internal conditions reach A. PSI solid rows without reported
  pressure cap at B rather than inventing a pressure.
- ML-3 predicts only BASS-II `delta_CO2 > 0.5` severity for PMMA and SIBAL, the two
  classes with at least ten training rows, and only within 13.6-22.2% O2. It abstains
  outside that support instead of extrapolating and does not predict ignition or flame
  spread.
- SPICE gas-jet data is retained for the library but is not used to grade solids.
- MAPTIS is excluded because it requires authenticated access.

## Data

637 curated rows: 148 graded solid-material tests, 487 gas-fuel tests, and 2 solid rows
with unspecified material; 9 source documents (501 pages). Primary sources are the NASA
PSI API (BASS-II, Saffire-I/II/III, ACME-BRE, SPICE), NTRS reports (BASS-II results and
TB 26-05), and NASA standards. Attribution and direct links: `docs/sources.md`.

## Documentation

- `PLAN.md` — scope, architecture, evidence rules, timeline, risks.
- `docs/validation.md` — audit, tests, ML gates, case studies, limitations.
- `docs/sources.md` — dataset and document provenance.
- `docs/case_studies.md` — generated case-study write-up.
- `docs/submission.md` — project-page copy, 90 s video script, checklist, offline demo.
- `artifacts/` — machine-readable validation and ML metrics, plus sample dossier PDFs.
