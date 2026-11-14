# Firebreak case studies

All grades are screening support, not certification or flight approval.

## PMMA at ISS internal atmosphere

The canonical negative-margin case: 1-g blow-off at 16% O2 versus steady microgravity spread at 13.6% O2.

- Query: PMMA at 24.1% O2, 14.5 psia
- Result: **Grade B** — test_needed; confidence 0.85; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: high (67%).

Why:
- Retrieved 12 solid-material tests; 0 include a documented outcome.
- Closest evidence: PSI-25:B1 (100 micron PMMA film 2 cm wide, 22.2% O2, outcome=None).
- No documented spread or extinction outcome; conditions support a test plan, not acceptance.

Evidence:
- `PSI-25:B1` — 100 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B2` — 200 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B3` — 100 micron film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B4` — 300 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B5` — 200 micron 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- Documented outcome (spread, extinction, or no ignition) at the query condition.
- Pressure-resolved test data.
- Flow direction (concurrent versus opposed).

## PMMA at lunar surface atmosphere

Beyond the tested O2 envelope; the grade must downgrade even for a well-studied material.

- Query: PMMA at 37.0% O2, 8.2 psia
- Result: **Grade C** — test_needed; confidence 0.75; coverage out_of_distribution.
- Outside tested envelope: yes.
- BASS-II CO2-rise screen: high (67%).

Why:
- Retrieved 12 solid-material tests; 0 include a documented outcome.
- Closest evidence: PSI-25:B1 (100 micron PMMA film 2 cm wide, 22.2% O2, outcome=None).
- Query O2=37.0% exceeds the tested maximum of 22.2% by more than 2.0%; grade downgraded.
- No documented spread or extinction outcome; conditions support a test plan, not acceptance.

Evidence:
- `PSI-25:B1` — 100 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B2` — 200 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B3` — 100 micron film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B4` — 300 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B5` — 200 micron 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- Documented outcome (spread, extinction, or no ignition) at the query condition.
- Microgravity test at or above 37.0% O2.
- Pressure-resolved test data.
- Flow direction (concurrent versus opposed).

## Saffire-II silicone and SIBAL

Microgravity no-spread for silicone versus 1.2 mm/s in 1-g; SIBAL spreads at 2.1 mm/s in microgravity.

- Query: Silicone at 22.1% O2, 14.5 psia, concurrent flow
- Result: **Grade B** — test_needed; confidence 0.62; coverage in_distribution.
- Outside tested envelope: no.

Why:
- Retrieved 4 solid-material tests; 4 include a documented outcome.
- Closest evidence: PSI-99:2-2 (Silicone, 22.1% O2, outcome=no_spread).
- Source tables do not report pressure; A grade is capped at B.

Evidence:
- `PSI-99:2-2` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-3` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-1` — Silicone, 21.5% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-4` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)

Gaps:
- Pressure-resolved test data.

## Saffire-II SIBAL spread

A documented microgravity spread outcome at 22.1% O2; pressure is not reported in the source table.

- Query: SIBAL at 22.1% O2, 14.5 psia, concurrent flow
- Result: **Grade B** — test_needed; confidence 0.85; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: low (7%).

Why:
- Retrieved 12 solid-material tests; 1 include a documented outcome.
- Closest evidence: PSI-99:2-5 (Cotton-Fiberglass (SIBAL), 22.1% O2, outcome=spread).
- Source tables do not report pressure; A grade is capped at B.

Evidence:
- `PSI-99:2-5` — Cotton-Fiberglass (SIBAL), 22.1% O2, pressure n/r psia, outcome: spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-98:S1` — SIBAL Fabric, 21.5% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-98)
- `PSI-98:S2` — SIBAL Fabric, 21.5% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-98)
- `PSI-25:T25` — 2 cm SIBAL, 20.8% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:T26` — 2 cm SIBAL, 20.8% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- Pressure-resolved test data.

## Nomex at ISS internal atmosphere

Three BASS-II Nomex conditions; no documented spread outcome and no brand/weight metadata.

- Query: Nomex at 24.1% O2, 14.5 psia
- Result: **Grade B** — test_needed; confidence 0.59; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: low (25%).

Why:
- Retrieved 4 solid-material tests; 0 include a documented outcome.
- Closest evidence: PSI-25:F1 (Nomex natural (nomex III), 22.2% O2, outcome=None).
- No documented spread or extinction outcome; conditions support a test plan, not acceptance.

Evidence:
- `PSI-25:F1` — Nomex natural (nomex III), 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:F3` — Nomex natural (nomex III), 21.7% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:F2` — Nomex natural (nomex III), 21.0% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-99:2-7` — PMMA & Nomex, 22.1% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)

Gaps:
- Documented outcome (spread, extinction, or no ignition) at the query condition.
- Pressure-resolved test data.

## Kevlar/PBI webbing at lunar surface

No Firebreak microgravity evidence. TB 26-05 reports 37%/35% MOC at 8.2 psia; source URL not yet ingested.

- Query: Kevlar/PBI at 37.0% O2, 8.2 psia
- Result: **Grade D** — insufficient_evidence; confidence 0.2; coverage no_material_evidence.
- Outside tested envelope: no.

Why:
- No solid-material evidence matched this material.

Evidence:

Gaps:
- No usable microgravity or 1-g evidence.
