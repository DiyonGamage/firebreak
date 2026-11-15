# Firebreak case studies

All grades are screening support, not certification or flight approval.

## PMMA at ISS internal atmosphere

The canonical negative-margin case: 1-g blow-off at 16% O2 versus steady microgravity spread at 13.6% O2.

- Query: PMMA at 24.1% O2, 14.5 psia
- Result: **Grade A** — high_risk; confidence 0.95; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: abstains — 24.1% O₂ is outside the BASS-II training range (13.6–22.2%).

Why:
- Retrieved 12 solid-material tests; 1 microgravity and 0 1-g rows carry a documented outcome.
- Closest evidence: NTRS-BASS2:PMMA-100um-20.7 (PMMA sheet, 100 micron, 20.7% O2, outcome=spread).
- Grade A anchor: NTRS-BASS2:PMMA-100um-20.7 at 20.7% O2 and 14.409 psia, outcome=spread.

Evidence:
- `NTRS-BASS2:PMMA-100um-20.7` — PMMA sheet, 100 micron, 20.7% O2, 14.409 psia, outcome: spread; [source](https://ntrs.nasa.gov/citations/20210011385)
- `PSI-25:B1` — 100 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B2` — 200 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B3` — 100 micron film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B4` — 300 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- No missing evidence at this condition; a contradicting pressure-resolved microgravity outcome would change the verdict.

## PMMA at lunar surface atmosphere

Beyond the tested O2 envelope; the grade must downgrade even for a well-studied material.

- Query: PMMA at 37.0% O2, 8.2 psia
- Result: **Grade C** — test_needed; confidence 0.85; coverage out_of_distribution.
- Outside tested envelope: yes.
- BASS-II CO2-rise screen: abstains — 37.0% O₂ is outside the BASS-II training range (13.6–22.2%).

Why:
- Retrieved 12 solid-material tests; 2 microgravity and 0 1-g rows carry a documented outcome.
- Closest evidence: NTRS-BASS2:PMMA-100um-20.7 (PMMA sheet, 100 micron, 20.7% O2, outcome=spread).
- Query O2=37.0% exceeds the tested maximum of 22.2% by more than 2.0%; grade downgraded.
- Query pressure is below the tested pressure envelope; grade downgraded.

Evidence:
- `NTRS-BASS2:PMMA-100um-20.7` — PMMA sheet, 100 micron, 20.7% O2, 14.409 psia, outcome: spread; [source](https://ntrs.nasa.gov/citations/20210011385)
- `NTRS-BASS2:PMMA-100um-16.0` — PMMA sheet, 100 micron, 16.0% O2, 14.409 psia, outcome: no_spread; [source](https://ntrs.nasa.gov/citations/20210011385)
- `PSI-25:B1` — 100 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B2` — 200 micron PMMA film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:B3` — 100 micron film 2 cm wide, 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- Microgravity test at or above 37.0% O2.
- Test data at or below 8.2 psia.

## Saffire-II silicone and SIBAL

Microgravity no-spread for silicone versus 1.2 mm/s in 1-g; SIBAL spreads at 2.1 mm/s in microgravity.

- Query: Silicone at 22.1% O2, 14.5 psia, concurrent flow
- Result: **Grade B** — test_needed; confidence 0.64; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: abstains — Unseen material class 'Silicone' for the BASS-II severity model.

Why:
- Retrieved 4 solid-material tests; 4 microgravity and 0 1-g rows carry a documented outcome.
- Closest evidence: PSI-99:2-2 (Silicone, 22.1% O2, outcome=no_spread).
- Matched documentation does not report pressure; A grade is capped at B.

Evidence:
- `PSI-99:2-2` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-3` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-1` — Silicone, 21.5% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `PSI-99:2-4` — Silicone, 22.1% O2, pressure n/r psia, outcome: no_spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)

Gaps:
- Pressure-resolved microgravity test data.

## Saffire-II SIBAL spread

A documented microgravity spread outcome at 22.1% O2; the PSI table omits pressure, so the A anchor comes from a pressure-reported BASS-II NTRS row.

- Query: SIBAL at 22.1% O2, 14.5 psia, concurrent flow
- Result: **Grade A** — high_risk; confidence 0.95; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: low (9%).

Why:
- Retrieved 12 solid-material tests; 4 microgravity and 0 1-g rows carry a documented outcome.
- Closest evidence: PSI-99:2-5 (Cotton-Fiberglass (SIBAL), 22.1% O2, outcome=spread).
- Grade A anchor: NTRS-BASS2:SIBAL-GMT96-T7 at 21.0% O2 and 14.696 psia, outcome=spread.

Evidence:
- `PSI-99:2-5` — Cotton-Fiberglass (SIBAL), 22.1% O2, pressure n/r psia, outcome: spread; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-99)
- `NTRS-BASS2:SIBAL-GMT96-T7` — SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide, 21.0% O2, 14.696 psia, outcome: spread; [source](https://ntrs.nasa.gov/citations/20210011385)
- `NTRS-BASS2:SIBAL-GMT216-T25` — SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide, 20.8% O2, 14.696 psia, outcome: ignited; [source](https://ntrs.nasa.gov/citations/20210011385)
- `PSI-98:S1` — SIBAL Fabric, 21.5% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-98)
- `NTRS-BASS2:SIBAL-GMT45-T4` — SIBAL fabric (75% cotton, 25% fiberglass), 2.2 cm wide, 18.7% O2, 14.696 psia, outcome: no_spread; [source](https://ntrs.nasa.gov/citations/20210011385)

Gaps:
- No missing evidence at this condition; a contradicting pressure-resolved microgravity outcome would change the verdict.

## Nomex at ISS internal atmosphere

Three BASS-II Nomex conditions; no documented spread outcome and no brand/weight metadata.

- Query: Nomex at 24.1% O2, 14.5 psia
- Result: **Grade B** — test_needed; confidence 0.51; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: abstains — Nomex has 2 BASS-II training rows; the minimum is 10.

Why:
- Retrieved 3 solid-material tests; 0 microgravity and 0 1-g rows carry a documented outcome.
- Closest evidence: PSI-25:F1 (Nomex natural (nomex III), 22.2% O2, outcome=None).
- No documented spread or extinction outcome; conditions support a test plan, not acceptance.

Evidence:
- `PSI-25:F1` — Nomex natural (nomex III), 22.2% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:F3` — Nomex natural (nomex III), 21.7% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)
- `PSI-25:F2` — Nomex natural (nomex III), 21.0% O2, pressure n/r psia, outcome: not reported; [source](https://psi.nasa.gov/physci/repo/data/investigations/PSI-25)

Gaps:
- Documented microgravity outcome (spread, extinction, or no ignition) at the query condition.
- Pressure-resolved microgravity test data.
- Flow direction (concurrent versus opposed).

## Kevlar/PBI webbing at lunar surface

TB 26-05 is now ingested as two explicitly labeled 1-g rows at 8.2 psia; no microgravity row exists, so R6 caps the result at C.

- Query: Kevlar/PBI at 37.0% O2, 8.2 psia
- Result: **Grade C** — test_needed; confidence 0.47; coverage in_distribution.
- Outside tested envelope: no.
- BASS-II CO2-rise screen: abstains — Unseen material class 'Kevlar/PBI' for the BASS-II severity model.

Why:
- Retrieved 2 solid-material tests; 0 microgravity and 2 1-g rows carry a documented outcome.
- Closest evidence: TB26-05:natural-37 (Kevlar/PBI webbing (60% Kevlar, 40% PBI), natural, 37.0% O2, outcome=no_spread).
- No microgravity outcome; 2 1-g test(s) provide an external anchor. R6 caps the grade at C.

Evidence:
- `TB26-05:natural-37` — Kevlar/PBI webbing (60% Kevlar, 40% PBI), natural, 37.0% O2, 8.2 psia, outcome: no_spread; [source](https://ntrs.nasa.gov/citations/20260006043)
- `TB26-05:black-35` — Kevlar/PBI webbing (60% Kevlar, 40% PBI), black, 35.0% O2, 8.2 psia, outcome: no_spread; [source](https://ntrs.nasa.gov/citations/20260006043)

Gaps:
- Documented microgravity outcome (spread, extinction, or no ignition) at the query condition.
- Microgravity test at or below 37.0% O2 with a documented outcome and pressure.
- Flow direction (concurrent versus opposed).
