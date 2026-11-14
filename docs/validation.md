# Validation report

Generated for the NASA Space Apps Challenge 2026 submission. Firebreak is screening
support, not certification, flight approval, or a substitute for NASA-STD-6001 Test 1.

## Summary

| Check | Gate | Result |
|---|---|---|
| Extraction audit | >= 95% field accuracy | **100%** (60/60 fields; 30/30 raw rows preserved) |
| Rule and application tests | 55/55 | **55/55 pytest tests pass** |
| End-to-end smoke test | PASS | **7/7 API assessments, UI form, assistant, Cactus route** |
| ML-1 evidence matcher | recall@3 >= 0.8 | **1.0**; false-match rate **0.0** |
| ML-2 coverage detector | held-out cases | **5/5** expected labels |
| ML-3 severity classifier | AUC >= 0.75 and beats baseline | **AUC 0.811**; O2-only AUC 0.605; 80% conformal coverage 0.896 |
| Case studies | 6 cases documented | **6/6** documented with source-linked evidence |
| Reproducible build | one command per artifact | Yes; deterministic seeds |
| Offline runtime | works without network | Yes, after build |

## Data ingested

| Dataset | Records | Role |
|---|---:|---|
| SPICE | 469 | Gas-jet flame data; retained for library, not solid-material grading |
| BASS-II | 129 | Solid-material microgravity tests; primary PSI evidence base |
| ACME-BRE | 18 | Aggregated gas-fuel tests; not used for solid grading |
| Saffire-II | 9 | Solid samples with some documented outcomes and 1-g comparisons |
| BASS-II (NTRS) | 6 | Page-cited pressure-bearing microgravity rows from NASA/TM-20210011385 |
| Saffire-I | 2 | Metadata-only rows |
| Saffire-III | 2 | Metadata-only rows |
| TB 26-05 (1-g) | 2 | Page-cited 1-g Kevlar/PBI anchors at 8.2 psia from NTRS 20260006043 |
| **Total** | **637** | |

- **148** solid-material rows are eligible for grading; 2 additional solid rows have
  unspecified material and are retained but excluded from matching.
- **32** rows have a documented outcome: 18 ACME gas rows, 6 Saffire-II rows, 6
  BASS-II NTRS rows, and 2 TB 26-05 rows. Fourteen documented rows are solid-material;
  13 of those name a specific material.
- The 8 external curated rows are labeled `BASS-II (NTRS)` and `TB 26-05 (1-g)` and
  carry page/section notes plus a provenance hash. They are not presented as PSI rows.
- **9** source documents, **501** pages: NTRS reports and NASA standards.

## Extraction audit

Method: deterministic stratified sample of 30 rows across all six PSI datasets.
For each row, the audit checks exact raw-row preservation against the cached PSI CSV
and independently re-parses key fields (material, initial O2, initial/final CO2 for
BASS-II; material and O2 for Saffire).

- 30/30 sampled rows matched their cached raw row after whitespace normalization.
- 60/60 field checks matched.
- Deliberate normalization: empty Saffire material becomes `unspecified`; repeated
  whitespace is collapsed. These are recorded, not silent.
- Gate: >= 95%; **passed at 100%**.

Artifact: `artifacts/extraction_audit.json`.

This is a consistency audit against the cached source, not an independent laboratory
re-analysis. Human spot checks were used during ingestion to catch column shifts and
note rows.

## Rule and application tests

`python -m pytest -q` -> **55 passed**.

Coverage includes:

- evidence grading and material-similarity behavior;
- O2 outside-envelope downgrade;
- no A grade without reported pressure;
- external pressure-resolved rows enabling A for PMMA and SIBAL, with page citations;
- 1-g-only Kevlar/PBI evidence capped at C;
- conflicting outcomes lower the grade;
- unknown material returns D, never a positive acceptance;
- combined-material layup queries capped at C, with pure-material retrieval excluding layup rows;
- dashboard insight counts, card ordering, matrix cells, and grade legend;
- sensitivity variants and deterministic repeatability;
- source-linked citations;
- ML gates and assistant fallback.

The engine caps a grade at B when the source table does not report pressure. That
remains true for the PSI solid-material tables, whose rows carry `pressure n/r`.
Grade A is reachable only through the page-cited external rows where the source
reports pressure: BASS-II NTRS §2.2/§7.1.3 (PMMA at 20.7% O2; SIBAL at 1 atm) and
TB 26-05 (Kevlar/PBI at 8.2 psia). TB 26-05 is 1-g, so R6 caps Kevlar/PBI at C.
Queries that name a combined-material layup are capped at C by R8: pure-material
evidence cannot support a configuration-level A or B.

## End-to-end smoke test

`python scripts\smoke_e2e.py --cactus` -> **PASS** against the running app.

- 7/7 API assessments returned the expected grade and verdict: PMMA ISS A, PMMA lunar C,
  silicone B, SIBAL A, Nomex B, Kevlar/PBI C, unknown material D.
- Gap Map returned 8 classes with the expected grades: PMMA and SIBAL A, Nomex and
  silicone B, Kevlar/PBI C, Nylon webbing D.
- Document search returned 3 hits for `PMMA margin`.
- Five assistant queries routed to the intended tools; an under-specified query asked
  for a material instead of guessing.
- Browser form submission rendered Grade A with 12 ledger rows; the browser assistant
  returned an answer with a visible fallback trace; library search returned 6 hits.
- The browser issued **0 external requests** while the form, assistant, and library
  flows ran; every request stayed on the local app URL.
- One live Cactus query returned `engine=cactus-needle` and routed to `assess_material`.

This is a functional check, not a substitute for the unit tests or the ML gates.

## Case studies

| Case | Query | Result | Coverage | Notable evidence |
|---|---|---|---|---|
| PMMA / ISS internal | 24.1% O2, 14.5 psia | **A**, high risk | in distribution | Page-cited BASS-II NTRS row: 100-µm PMMA at 20.7% O2, 1 atm, 2.2 mm/s spread |
| PMMA / lunar surface | 37% O2, 8.2 psia | **C**, test needed | out of distribution | Outside tested O2 and pressure envelope; downgrade applied |
| Saffire-II silicone | 22.1% O2, 20 cm/s | **B**, test needed | in distribution | Microgravity no-spread; 1-g spread rate 1.2 mm/s; PSI row lacks pressure |
| Saffire-II SIBAL | 22.1% O2, 20 cm/s | **A**, high risk | in distribution | Documented microgravity spread; pressure-bearing NTRS anchor |
| Nomex / ISS internal | 24.1% O2, 14.5 psia | **B**, test needed | in distribution | Three BASS-II conditions; no documented outcome and no pressure |
| Kevlar/PBI / lunar surface | 37% O2, 8.2 psia | **C**, test needed | in distribution | Two page-cited 1-g no-spread rows at 8.2 psia; R6 caps at C |

Full write-up: `docs/case_studies.md`. Machine-readable artifact:
`artifacts/case_studies.json`.

## ML validation

### ML-1 evidence matcher

TF-IDF character n-grams plus a material-class gate and alias expansion.

- 9 alias queries (PMMA, polymethyl methacrylate, acrylic sheet, SIBAL,
  cotton-fiberglass, Nomex III, silicone rubber, PMMA & Nomex, Kevlar/PBI webbing):
  **recall@3 = 1.0**.
- 3 deliberately unknown queries (polyethylene film, Vectran fabric, unobtainium
  composite): **false-match rate = 0.0**.
- Gate: recall >= 0.8 and false-match <= 0.2; **passed**.
- Caveat: the benchmark is small and curated; it tests routing/abstention behavior,
  not general semantic understanding.

### ML-2 coverage detector

Nearest-condition distance in O2, pressure, and flow, with penalties for missing
pressure or flow metadata.

- PMMA at ISS internal -> `in_distribution`.
- PMMA at lunar surface -> `out_of_distribution`.
- Silicone at 22.1% O2 -> `in_distribution`.
- Kevlar/PBI at 37% O2, 8.2 psia -> `in_distribution` from 1-g rows, with an explicit
  "No microgravity evidence" gap.
- Vectran fabric -> `no_material_evidence`.
- Gate: 5/5; **passed**.

Coverage is descriptive. Absence of evidence is not evidence of safety.

### ML-3 severity classifier

Target: BASS-II `delta_CO2 > 0.5` percentage points. `delta_O2` is not used as a
target because the BASS-II export contains calibration artifacts (including negative
and implausibly large values).

- 121 usable rows, 35 positive, 86 negative.
- Histogram gradient boosting (depth 2, 200 iterations) with median thickness
  imputation and one-hot material class, constrained monotonic in O2.
- **GroupKFold(5), grouped by material description: AUC 0.811**, accuracy 0.826,
  balanced accuracy 0.751, F1 0.656, Brier 0.148, ECE 0.035.
- O2-only baseline AUC 0.605; majority-class accuracy 0.711 (86/121).
- The unconstrained variant scored AUC 0.815 but produced **28 monotonicity
  violations** (higher O2 lowering predicted risk); it was rejected in favour of
  the constrained model. The constrained model has 0 violations.
- Support floor: 10 rows per class. PMMA (90 rows, 35 positive) and SIBAL (25 rows,
  0 positive) are supported; Nomex (2) and Other (4) are excluded and cause an
  abstention. O2 support is 13.6-22.2%; queries outside it abstain rather than
  extrapolate, including the 24.1% ISS cabin preset.
- Uncertainty: 80% CV+ conformal prediction sets over five material-grouped folds,
  evaluated with nested GroupKFold(5 outer x 3 inner) on supported classes:
  **coverage 0.896**, mean set size 1.45, abstention 45.2% (PMMA 48.9%,
  SIBAL 32.0%). An abstention means the set contains both bands and the record is
  routed to testing, not that the material is safe.
- Gate: AUC >= 0.75, beats baseline, and 0 monotonicity violations; **passed**.
- Headline claim: a modest, scoped CO2-rise screen, not a flammability predictor.
- Scope: BASS-II classes only. The model is **not validated for unseen material
  classes** and is disabled for them.

Artifacts: `artifacts/ml_severity_metrics.json`, `artifacts/ml_eval.json`.

## Cactus Needle assistant

Six tools: `assess_material`, `retrieve_evidence`, `coverage_check`,
`severity_estimate`, `find_gaps`, `build_dossier`.

- Cactus Needle is the optional local router; answers are generated only from tool JSON.
- Deterministic fallback router is the default for speed and reliability.
- No Cactus fine-tuning was performed. Schema/description tightening was sufficient.
- Manual smoke tests: assess, lunar assessment, gap query, airlock coverage, severity,
  and PMMA assessment all routed to the intended tool after schema tightening.
- Latency was approximately 12-36 seconds on this CPU-only machine; the UI labels the
  Cactus option as slow and keeps the fast fallback.

This is not a formal routing benchmark; it is a functional validation with visible
tool traces.

## Reproducibility

```powershell
python scripts\build_data.py
python scripts\build_docs.py
python scripts\eval_ml.py
python scripts\audit_extraction.py
python scripts\build_case_studies.py
python -m pytest -q
uvicorn app.main:app --port 8000
```

The app reads the local SQLite database and local document text after the build. The
demo can run with Wi-Fi disabled.

## Limitations and known discrepancies

1. PSI solid-material tables do not report pressure; those rows cap at B. Grade A
   depends on page-cited external rows where the report states pressure, so coverage
   of A-grade materials is limited to PMMA and SIBAL today. `delta_O2` is not trusted.
2. Saffire-II has only nine samples; several outcomes or materials are missing, and
   some 1-g spread descriptions are qualitative.
3. ACME-BRE rows are daily aggregates with inconsistent O2 text (including typo-scale
   values) and are excluded from solid-material grading.
4. SPICE is gas-jet data, not a solid-material test set.
5. TB 26-05 is 1-g evidence at 8.2 psia, explicitly labeled and cited to NTRS
   20260006043. It anchors Kevlar/PBI but cannot satisfy the microgravity requirement,
   so Kevlar/PBI remains Grade C.
6. ML-3 is scoped to BASS-II material classes and material-description-grouped CV. It
   is not a certification model and does not predict ignition or flame spread.
7. JSC 29353D Table 1 lists 36-40% O2 at 8.2 psia (HLS max 37%); the 2018 fire-safety
   brief cites 34%. Both are recorded in the rule facts; the preset uses the HLS max.
8. NTRS citation 20150020937 is JSC 29353B, not D. JSC 29353D is sourced from
   NASA Standards.


