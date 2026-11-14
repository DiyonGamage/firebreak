# Sources

All sources were accessed on 2026-11-14. Cached copies live under `data/raw/`.
Firebreak does not redistribute MAPTIS content; MAPTIS requires authenticated access.

## NASA Physical Sciences Informatics (PSI)

| Dataset | PSI investigation | Records used |
|---|---|---:|
| BASS-II | https://psi.nasa.gov/physci/repo/data/investigations/PSI-25 | 129 |
| Saffire-I | https://psi.nasa.gov/physci/repo/data/investigations/PSI-98 | 2 |
| Saffire-II | https://psi.nasa.gov/physci/repo/data/investigations/PSI-99 | 9 |
| Saffire-III | https://psi.nasa.gov/physci/repo/data/investigations/PSI-100 | 2 |
| ACME-BRE | https://psi.nasa.gov/physci/repo/data/investigations/PSI-20 | 18 |
| SPICE | https://psi.nasa.gov/physci/repo/data/investigations/PSI-107 | 469 |

The experimental tables were retrieved through the public PSI API:

- Metadata: `https://psi.nasa.gov/geode-py/ws/repo/investigations/{ACC}`
- File download: `https://psi.nasa.gov/geode-py/ws/studies/{ACC}/download?file={FILE_ID}&version=1&redirect=false`

The returned presigned S3 URL is used once to download the CSV. The cached CSV SHA-256
is recorded in the `raw_files` table. See the PSI site for terms of use and attribution.

## NTRS documents

| Citation | Title | Pages | URL |
|---|---|---:|---|
| 20160000593 | Combustion of Solids in Microgravity: Results from the BASS-II Experiment | 21 | https://ntrs.nasa.gov/citations/20160000593 |
| 20200000557 | Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA | 25 | https://ntrs.nasa.gov/citations/20200000557 |
| 20180004258 | Spacecraft Fire Safety: Protecting Vehicles and Crews on Long-Duration Exploration Missions | 29 | https://ntrs.nasa.gov/citations/20180004258 |
| 20170000230 | Operation and Development Status of the Spacecraft Fire Experiments (Saffire) | 9 | https://ntrs.nasa.gov/citations/20170000230 |
| 20150020937 | Flammability Configuration Analysis for Spacecraft Applications | 54 | https://ntrs.nasa.gov/citations/20150020937 |
| 20210011385 | Burning and Suppression of Solids-II (BASS-II) Summary Report | 144 | https://ntrs.nasa.gov/citations/20210011385 |
| 20260006043 | Webbings for Use in Elevated Oxygen Environments (TB 26-05) | 1 | https://ntrs.nasa.gov/citations/20260006043 |

Note: 20150020937 is **JSC 29353B**, a historical revision, not JSC 29353D.

PDFs are resolved through `https://ntrs.nasa.gov/api/citations/{id}` download links,
cached under `data/raw/ntrs/`, and validated to start with `%PDF` before use. Text and
per-page JSON are cached alongside.

## External curated datasets

Two small, page-cited datasets are ingested separately from PSI and clearly labeled:

| Dataset | Rows | Source | What the source states |
|---|---:|---|---|
| BASS-II (NTRS) | 6 | NASA/TM-20210011385 | PMMA 100 µm at 20.7% O2 spread 2.2 mm/s and extinguished near 16% O2 (§2.2.4–2.2.5); monitored total pressure 99.2–99.5 kPa (§2.3.5); SIBAL tests 16–21% O2 at 1 atm with Table 7.1 outcomes (§7.1.3) |
| TB 26-05 (1-g) | 2 | NTRS 20260006043 | Natural and black Kevlar/PBI webbing, 37%/35% MOC at 8.2 psia, NASA-STD-6001B Test 1 unshielded J, 1-g |

Each row stores the quoted source text, page/section note, and a provenance hash.
These rows are not presented as PSI measurements. The 1-g TB rows cannot satisfy the
microgravity requirement and are used only as an external anchor capped at Grade C.

## NASA standards

| Standard | Revision | Pages | URL |
|---|---|---:|---|
| JSC 29353D | 2024 | 60 | https://standards.nasa.gov/system/files/tmp/JSC%2029353D%20Flammability%20Configuration%20Analysis%20for%20Spacecraft%20Applications.pdf |
| NASA-STD-6001B | Change 3, 2025 | 158 | https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/2025_06_25_NASA-STD-6001B_w_Change_3_FINAL_Admin-Change-FINAL.pdf |

Key clauses used:

- NASA-STD-6001B Test 1 acceptance: maximum burn length 15 cm; no debris propagation;
  five specimens; worst-case atmosphere; MOC is the maximum O2 at which at least five
  specimens pass.
- JSC 29353D Table 1: cabin atmosphere presets used in `firebreak/rules/rules.yaml`.

## Excluded sources

- MAPTIS: gated behind NASA Launchpad authentication; not used.
- AWS PSI mirror: contains DSI/OASIS/pk4 artifacts, not the combustion tables used here.
- Kaggle mirrors: not used; primary PSI/NTRS/standards sources were available.
- NTRS Saffire payload papers that returned 404 during retrieval: not used.
