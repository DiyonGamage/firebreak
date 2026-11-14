# Validation report

Generated for the NASA Space Apps Challenge 2026 submission. Firebreak is screening
support, not certification, flight approval, or a substitute for NASA-STD-6001 Test 1.

## Summary

| Check | Gate | Result |
|---|---|---|
| Extraction audit | >= 95% field accuracy | **100%** (60/60 fields; 30/30 raw rows preserved) |
| Rule and application tests | 38/38 | **38/38 pytest tests pass** |
| ML-1 evidence matcher | recall@3 >= 0.8 | **1.0**; false-match rate **0.0** |
| ML-2 coverage detector | held-out cases | **4/4** expected labels |
| ML-3 severity classifier | AUC >= 0.75 and beats baseline | **AUC 0.834**; O2-only AUC 0.607 |
| Case studies | 4/4 documented | **6/6** documented with source-linked evidence |
| Reproducible build | one command per artifact | Yes; deterministic seeds |
| Offline runtime | works without network | Yes, after build |

## Data ingested

| Dataset | Records | Role |
|---|---:|---|
| SPICE | 469 | Gas-jet flame data; retained for library, not solid-material grading |
| BASS-II | 129 | Solid-material microgravity tests; primary evidence base |
| ACME-BRE | 18 | Aggregated gas-fuel tests; not used for solid grading |
| Saffire-II | 9 | Solid samples with some documented outcomes and 1-g comparisons |
| Saffire-I | 2 | Metadata-only rows |
| Saffire-III | 2 | Metadata-only rows |
| **Total** | **629** | |

- **140** solid-material rows are eligible for grading; 2 additional solid rows have
  unspecified material and are retained but excluded from matching.
- **24** rows have a documented outcome: 18 ACME gas rows and 6 Saffire-II rows.
  Five Saffire-II outcomes are usable for solid-material grading (one is on an
  unspecified material).
- **7** source documents, **356** pages: NTRS reports and NASA standards.

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

`python -m pytest -q` -> **38 passed**.

Coverage includes:

- evidence grading and material-similarity behavior;
- O2 outside-envelope downgrade;
- no A grade without reported pressure;
- conflicting outcomes lower the grade;
- unknown material returns D, never a positive acceptance;
- sensitivity variants and deterministic repeatability;
- source-linked citations;
- ML gates and assistant fallback.

The engine deliberately caps a grade at B when the source table does not report
pressure. Current PSI solid-material tables do not report pressure, so **no A grade is
awarded from this corpus**; the A path is tested but remains unused until a
pressure-resolved source is ingested.

## Case studies

| Case | Query | Result | Coverage | Notable evidence |
|---|---|---|---|---|
| PMMA / ISS internal | 24.1% O2, 14.5 psia | **B**, test needed | in distribution | BASS-II PMMA series at 22.2%; no documented spread outcome |
| PMMA / lunar surface | 37% O2, 8.2 psia | **C**, test needed | out of distribution | Outside tested O2 envelope |
| Saffire-II silicone | 22.1% O2, 20 cm/s | **B**, test needed | in distribution | Microgravity no-spread; 1-g spread rate 1.2 mm/s |
| Saffire-II SIBAL | 22.1% O2, 20 cm/s | **B**, test needed | in distribution | Documented microgravity spread at 2.1 mm/s |
| Nomex / ISS internal | 24.1% O2, 14.5 psia | **B**, test needed | in distribution | Three BASS-II conditions; no documented outcome |
| Kevlar/PBI / lunar surface | 37% O2, 8.2 psia | **D**, insufficient evidence | no material evidence | TB 26-05 external anchor; source URL not yet ingested |

Full write-up: `docs/case_studies.md`. Machine-readable artifact:
`artifacts/case_studies.json`.

## ML validation

### ML-1 evidence matcher

TF-IDF character n-grams plus a material-class gate and alias expansion.

- 8 alias queries (PMMA, polymethyl methacrylate, acrylic sheet, SIBAL,
  cotton-fiberglass, Nomex III, silicone rubber, PMMA & Nomex): **recall@3 = 1.0**.
- 3 deliberately unknown queries (polyethylene film, Kevlar/PBI, unobtainium
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
- Kevlar/PBI -> `no_material_evidence`.
- Gate: 4/4; **passed**.

Coverage is descriptive. Absence of evidence is not evidence of safety.

### ML-3 severity classifier

Target: BASS-II `delta_CO2 > 0.5` percentage points. `delta_O2` is not used as a
target because the BASS-II export contains calibration artifacts (including negative
and implausibly large values).

- 121 usable rows, 35 positive, 86 negative.
- Random forest with numeric imputation/scaling and one-hot material class.
- **GroupKFold(5), grouped by material description: AUC 0.834**, accuracy 0.744,
  balanced accuracy 0.693, F1 0.563.
- O2-only baseline AUC 0.607; majority-class accuracy 0.711.
- Gate: AUC >= 0.75 and beats baseline; **passed**.
- Headline claim: a modest, scoped CO2-rise screen, not a flammability predictor.
- Scope: BASS-II classes only (PMMA, SIBAL, Nomex, Other). It is **not validated for
  unseen material classes**; a class-held-out check is not statistically meaningful
  with four classes. The model is disabled for unseen classes.

Artifacts: `artifacts/ml_severity_metrics.json`, `artifacts/ml_eval.json`.

## Cactus 3 assistant

Six tools: `assess_material`, `retrieve_evidence`, `coverage_check`,
`severity_estimate`, `find_gaps`, `build_dossier`.

- Cactus is the optional local router; answers are generated only from tool JSON.
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

1. BASS-II tables do not report pressure or a direct spread outcome; grades are capped
   at B. `delta_O2` is not trusted.
2. Saffire-II has only nine samples; several outcomes or materials are missing, and
   some 1-g spread descriptions are qualitative.
3. ACME-BRE rows are daily aggregates with inconsistent O2 text (including typo-scale
   values) and are excluded from solid-material grading.
4. SPICE is gas-jet data, not a solid-material test set.
5. The TB 26-05 Kevlar/PBI anchor (37%/35% MOC at 8.2 psia) is known from the
   literature but its source URL has not been ingested; it is flagged in the case
   study rather than silently treated as database evidence.
6. ML-3 is scoped to BASS-II material classes and material-description-grouped CV. It
   is not a certification model and does not predict ignition or flame spread.
7. JSC 29353D Table 1 lists 36-40% O2 at 8.2 psia (HLS max 37%); the 2018 fire-safety
   brief cites 34%. Both are recorded in the rule facts; the preset uses the HLS max.
8. NTRS citation 20150020937 is JSC 29353B, not D. JSC 29353D is sourced from
   NASA Standards.


