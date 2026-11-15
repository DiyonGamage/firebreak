# Firebreak — Build Plan

**Team:** LFR
**Event:** NASA Space Apps Challenge 2026 — Kandy, Sri Lanka (virtual)
**Deadline:** 15 Nov 2026, 23:59 SLST (UTC+5:30)
**Challenge:** Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data
**Repo:** public, open license, no restricted data

## Current status (2026-11-15)

Core is built, validated and published: PSI/NTRS/standards ingestion over 1,170 records
(637 experiment rows plus 533 non-graded characterisation records), A/B/C/D rule engine,
63 passing tests, ML gates passed, FastAPI UI with an investigations view and a four-role
evidence court, optional Cactus Needle assistant, extraction audit at 100%, and six
generated case studies. Page-cited external rows from the BASS-II summary and TB 26-05 add
pressure-resolved evidence, so PMMA and SIBAL reach Grade A while materials without
pressure-bearing evidence stay capped. Submission package lives in `docs/submission.md`,
slide copy in `docs/deck.md`, and the public report at `https://diyongamage.github.io/firebreak/`.
Remaining work: record and upload the video and file the project page.

## Mission

A source-linked, decision-grade screening engine for spacecraft material flammability.
Given a material and atmosphere, Firebreak answers: what is the evidence, what is the
risk, what is uncertain, and what must be tested next.

Not a MAPTIS replacement. Not a certification tool. Not a generic chatbot.

## Product

Inputs: material + atmosphere (ISS 24.1% O2/14.5 psia; 30%/10.2; exploration 34%/8.2; custom).

Outputs:
- Evidence grade A/B/C/D
- Verdict: acceptable / conditional / test needed / high risk / insufficient evidence
- Citations to PSI test ID, NTRS page, or standard clause
- Uncertainty and sensitivity panel
- Habitat material-risk matrix
- Gap Map with ranked test plan
- Dossier export (HTML/PDF)
- Offline assistant with visible tool trace

Users: mission planners, materials engineers, researchers without MAPTIS, educators.

## Verified data

| Dataset | Rows | Access |
|---|---:|---|
| PSI-25 BASS-II | 129 | metadata JSON -> presigned CSV |
| PSI-98 Saffire-I | 2 | metadata JSON -> presigned CSV |
| PSI-99 Saffire-II | 9 | metadata JSON -> presigned CSV |
| PSI-100 Saffire-III | 2 | metadata JSON -> presigned CSV |
| PSI-20 ACME BRE | 18 | metadata JSON -> presigned CSV |
| PSI-107 SPICE | 469 | metadata JSON -> presigned CSV |
| BASS-II (NTRS) | 6 | page-cited rows from NASA/TM-20210011385 |
| TB 26-05 (1-g) | 2 | page-cited 1-g rows from NTRS 20260006043 |
| **Experiment total** | **637** | |
| PSI-69/68 FLEX + FLEX-2 | 282 | characterisation: droplet extinction, never graded |
| PSI-26 BASS | 122 | characterisation: test log, never graded |
| PSI-101 SAME-R | 109 | characterisation: smoke aerosol, never graded |
| PSI-106 SLICE | 12 | characterisation: test log, never graded |
| PSI-102 SAME | 8 | characterisation: smoke aerosol, never graded |
| **Records total** | **1,170** | |
| NTRS PDFs | 7 verified | direct PDF |
| Standards | JSC 29353D, NASA-STD-6001B | public PDFs |

Endpoints:
- `https://psi.nasa.gov/geode-py/ws/repo/investigations/{ACC}`
- `https://psi.nasa.gov/geode-py/ws/studies/{ACC}/download?file={FILE_ID}&version=1&redirect=false`
  -> returns presigned S3 URL -> CSV

Excluded: MAPTIS and all auth-gated data. No restricted-source scraping.
Attribution in `docs/sources.md`.

Key facts:
- BASS-II: 129 rows, 51 material descriptions, conditions + O2/CO2/CO; no outcome column.
- Saffire-II: numeric micro-g rates for ~3 samples; 1-g rates partly qualitative.
- NTRS 20160000593: PMMA 1-g blowoff at 16% O2 vs steady micro-g spread at 13.6%;
  negative O2 margin 2.4%.
- TB 26-05: webbing MOC 37%/35% at 8.2 psia; ingested as two labeled 1-g rows.
- NASA-STD-6001B/JSC 29353D: extract exact clause values during build; do not hardcode
  unverified numbers.

## Architecture

```
PSI JSON -> presigned CSV
NTRS PDFs -> PyMuPDF text
Standards -> text/rules
        -> normalize -> SQLite + JSON snapshots
        -> Evidence Matcher (ML-1)
        -> Coverage Detector (ML-2)
        -> Severity Classifier (ML-3, gated)
        -> Rule Engine + Evidence Grades
        -> Verdict + citations + sensitivity + Gap Map
        -> Dossier + UI + Cactus Needle assistant
```

Runtime is offline. Build step downloads and hashes sources. No external API at demo time.

## Harmonized schema

`experiment_id, source_id, source_url, dataset, platform, material, material_class,
geometry, thickness_mm, width_mm, length_mm, o2_initial_pct, o2_final_pct,
pressure_kpa, flow_velocity_cm_s, flow_direction, gravity, ignition_method,
ignition_power_w, burn_time_s, spread_rate_mm_s, outcome, notes, provenance_hash`

Rules: every numeric field has provenance; missing stays missing; unit normalization
logged; duplicates deduplicated by platform + test ID + condition.

## Evidence grading

| Grade | Criteria | Verdict |
|---|---|---|
| A | Micro-g data at or beyond target; same/similar material and geometry; documented outcome | Acceptable, with caveats |
| B | Micro-g data bracketing target within one condition step | Conditional / test needed |
| C | 1-g screening/standard only, non-comparable micro-g data, or query outside the tested envelope | High uncertainty / test needed |
| D | No usable evidence or conflicting evidence | Insufficient evidence |

"Acceptable" always means screening support, not certification.

## Rule engine

Versioned YAML + Python evaluator. Every rule has a citation, unit test, and failure mode.

1. O2 monotonicity: higher O2 cannot reduce risk.
2. Pressure: encode published non-monotonic behavior; never assume monotonic.
3. Flow direction: concurrent vs opposed; quench and blow-off limits.
4. Geometry/thickness: thin films vs rods/slabs.
5. 1-g derating: apply documented negative margins (PMMA 2.4% O2) when only 1-g data.
6. A-rating applicability: 1-g rating does not automatically cover micro-g/exploration.
7. Unknown data forces D; no guessing.
8. Conflicting sources surface both and lower confidence.
9. Outside tested envelope downgrades the grade.
10. Cross-material transfer only with explicit similarity; otherwise D.

Gate: 63/63 tests pass (rules, insights, investigations, ML, assistant). A is awarded only when a documented
microgravity outcome has reported pressure; PSI solid rows lack pressure and cap at B,
while page-cited BASS-II rows at 1 atm enable A for PMMA and SIBAL. TB 26-05 is 1-g, so
Kevlar/PBI caps at C.

## ML layer (approved)

| Module | Task | Data | Validation | Gate |
|---|---|---|---|---|
| ML-1 Evidence Matcher | Retrieve analogous tests | 129 BASS-II + 9 Saffire-II + metadata | Recall@3 on case queries | >= 0.8 (actual 1.0) |
| ML-2 Coverage Detector | Inside/near/outside tested envelope | All solid-material conditions | Held-out material cases | 5/5 expected labels |
| ML-3 Severity Classifier | High/low dCO2 (BASS-II) | 121 usable rows | GroupKFold by material; baseline | AUC 0.811 vs O2-only 0.605; 80% conformal coverage 0.896 |

ML-3 is exploratory, never certification. dO2 is not used as a target (calibration artifacts).
SPICE smoke-point model is optional and cut unless core is done by 18:00.

Cactus Needle is the orchestrator, not the predictor. Strict enum schemas; visible call trace;
deterministic fallback router. Tools: assess_material, retrieve_evidence, coverage_check,
severity_estimate, find_gaps, build_dossier, investigation_lookup, pillar_coverage. Manual smoke tests route correctly; a
formal 25-query routing benchmark is optional and not yet run. No fine-tuning.

## UI

FastAPI + Jinja + vanilla JS + vendored Chart.js; SQLite; offline badge.
Pages: Overview, Investigations (ranked, pillars, readiness, contradictions), Material Matrix,
Material Detail, Gap Map, Ask, Validation, Dossier export.
Demo must work with Wi-Fi disabled.

## Validation

1. Extraction audit: 30 stratified rows; 60/60 fields, 30/30 rows; 100%.
2. Rule/application tests: 55/55 pass.
3. Case studies:
   - PMMA: negative 2.4% O2 margin; pressure-bearing BASS-II NTRS row at 20.7% O2.
   - Saffire-II: silicone/SIBAL micro-g vs 1-g behavior.
   - Nomex: brand/weight/color variability.
   - Kevlar/PBI webbing: 1-g only, 37%/35% MOC at 8.2 psia, capped at C.
4. ML metrics: recall@3, leave-one-material-out coverage, grouped CV AUC/calibration;
   report failures honestly.
5. Reproducibility: one command rebuilds data and validation report; deterministic seeds;
   offline runtime.
6. Limitations: explicit page; screening support, not certification.

## Timeline

| Block | Work | Gate |
|---|---|---|
| 0 (30 min) | Folder, PLAN.md, scaffold, requirements | Repo runs |
| 1 (3 h) | PSI ingestion, NTRS pulls, standards text, schema, audit sample | >= 120 solid-material rows; audit >= 95% |
| 2 (5 h) | Rule engine, evidence grades, verdicts, Gap Map, dossier | 15/15 tests; 6/6 case studies |
| 3 (3 h) | ML-1, ML-2, ML-3 + gates | Matcher >= 0.8; severity gate |
| 4 (5 h) | UI + Cactus tools + offline packaging | End-to-end demo offline |
| 5 (4 h) | Validation report, README, sources, project page | Package complete |
| 6 (3 h) | 90 s video, rehearsal, submission | Submit before 23:59 |
| Buffer (6 h) | Fixes, virtual judging prep | - |

Cut list: SPICE ML, PMMA physics demo, 3D habitat, video frame analysis, fine-tuning,
graph visualizations, multi-user features.

## Deliverables

- Public repo with code, build scripts, tests, attribution
- Running app (offline)
- Sample dossiers
- `docs/validation.md` with audit, tests, case studies, ML metrics
- 90 s video
- Project page text
- Completed submission checklist

## Risks

| Risk | Mitigation |
|---|---|
| Time overrun | Pre-approved cut list; core-first order |
| ML gate fails | Cut severity model; keep matcher/coverage; state honestly |
| Cactus routing errors | Strict schemas, fallback router, eval |
| Standards extraction errors | Human audit, clause citations, unit tests |
| Data artifacts | Provenance hashes, audit, no silent imputation |
| Virtual judging failure | Offline app, recorded backup, screen-share rehearsal |
| Scientific criticism | Screening support, not certification; limitations page |

## File structure

```
Firebreak/
  PLAN.md
  README.md
  requirements.txt
  .gitignore
  app/main.py
  firebreak/
    config.py
    data/psi.py, ntrs.py, standards.py, harmonize.py, external.py
    rules/engine.py, rules.yaml
    ml/evidence.py, coverage.py, severity.py
    services/dossier.py
    assistant/tools.py, agent.py
  scripts/build_data.py, build_docs.py, eval_ml.py, audit_extraction.py,
          build_case_studies.py, build_corpus_diagram.py
  data/raw/
  data/processed/firebreak.sqlite
  tests/
  web/templates/
  web/static/
  docs/validation.md, case_studies.md, sources.md
  artifacts/
```

## Open items

1. Team name: **LFR** (confirmed 2026-11-14).
2. Kandy virtual judging: time and platform not announced as of 2026-11-14.
3. Repo: public at https://github.com/DiyonGamage/firebreak, MIT licensed.
