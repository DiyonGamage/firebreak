# Firebreak — Submission Package

NASA Space Apps Challenge 2026 · Kandy, Sri Lanka (virtual)
Challenge: **Flame in Freefall — AI-Powered Fire Safety Insights from Microgravity Combustion Data**
Deadline: **15 Nov 2026, 23:59 SLST**
Team: **LFR**

Use this file to fill the project page, record the video, and run the live demo.
Replace `{{VIDEO_URL}}` before publishing.

---

## 1. Project page copy

### Title

**Firebreak — evidence-graded fire safety screening for spaceflight materials**

### One-line pitch

Know what the evidence actually supports: source-linked A–D flammability evidence
grades, explicit gaps, and the next test to run — offline.

### Short description

Firebreak turns NASA microgravity combustion data, standards, and literature into
source-linked evidence grades. Given a material and cabin atmosphere, it shows the
closest tests, why the grade was assigned, what is missing, and what evidence would
change the answer. It is screening support, not certification.

### 20-second AI answer — place above the fold

> Firebreak uses AI where it can be checked. One model screens whether CO₂ rises more than
> 0.5 points in BASS-II, from oxygen, thickness, and material class. It is monotonic in
> oxygen, validated by material, and wrapped in 80% conformal sets that return “unresolved”
> when the data cannot decide — abstaining outside PMMA/SIBAL or 13.6–22.2% O₂, including
> the 24.1% ISS preset. Rules assign the grade, never the model.

### Long description

Spacecraft material flammability decisions are made under uncertainty. A material that
passes a 1-g test can behave differently in microgravity: NASA's BASS-II results show
PMMA blowing off at 16% O2 in 1-g while continuing to spread at 13.6% O2 in microgravity
— a negative oxygen margin of 2.4 percentage points. Engineers need to know what the
evidence covers, where it stops, and what test closes the gap.

For a materials engineer preparing a NASA-STD-6001 Test 1 campaign, Firebreak turns 501
pages across nine documents into one cited dossier: the grade, the nearest tests, and the
gap that would change it.

Firebreak answers four questions for any material and atmosphere:

1. What evidence exists, and where is it published?
2. What evidence grade does it support (A/B/C/D)?
3. What uncertainty remains?
4. What test should be run next?

The app ingests 637 curated PSI and page-cited NTRS experiment records and 501 pages of
NASA reports and standards into a local SQLite corpus. Retrieval, coverage, and severity
models run locally. A deterministic rule engine applies documented evidence rules, caps
grades when pressure is not reported, and never fabricates a condition or outcome. Every
result links to a PSI test row, NTRS page, or NASA standard clause. The whole demo runs
with Wi-Fi disabled.

### How it works

- **Harmonize** — PSI tables, NTRS PDFs, and NASA standards are normalized into one
  schema with provenance hashes. Missing values stay missing.
- **Retrieve** — a TF-IDF character n-gram matcher with a material-class gate finds
  analogous solid-material tests and abstains when no material evidence exists.
- **Cover** — a nearest-condition detector labels each query in, near, or outside the
  tested O2/pressure/flow envelope.
- **Grade** — a versioned rule engine (10 rules, each with a citation) assigns an
  evidence grade and verdict. A grade requires reported pressure; PSI solid-material
  rows lack it and cap at B, while page-cited BASS-II rows that report 1 atm enable A
  for PMMA and SIBAL at ISS-internal conditions.
- **Screen severity** — an optional, scoped random-forest model estimates BASS-II
  CO2-rise severity for material classes seen in training. It does not predict ignition
  or flame spread.
- **Explain** — the UI shows the closest tests, reasons, gaps, sensitivity variants,
  a ranked Gap Map, a printable dossier, and an offline evidence router with a visible
  tool trace.

### How we built it

Python 3.11, FastAPI, Jinja2, SQLite, pandas, NumPy, scikit-learn, PyMuPDF, vanilla
JavaScript and CSS. The optional local assistant uses Cactus Needle as a router;
the default deterministic router is fast and always available. Playwright captures the
submission screenshots. All data is built once, cached, hashed, and then served offline.

### Challenges we ran into

- PSI solid-material tables do not report pressure. We refused to fill in a plausible
  value; instead we located the page-cited BASS-II summary passages that do report
  pressure and ingested them as a separate, clearly labeled dataset. Grades rise only
  where the source actually states the condition.
- Most BASS-II rows have no documented spread outcome, so "no evidence" must not become
  "safe." The engine returns test-needed, never acceptance, in that case.
- ACME-BRE rows are daily aggregates with inconsistent O2 text; they are retained but
  excluded from solid-material grading.
- Saffire-II has only nine samples and some outcomes are qualitative.
- Cactus routing on CPU is slow (12–36 s). We kept it optional, made the deterministic
  router the default, and ship a cached Cactus run in the UI for the demo rather than
  hiding the latency.

### Accomplishments we are proud of

- **100% extraction audit** — 30 stratified rows, 60/60 field checks, 30/30 raw rows
  preserved.
- **55/55 tests pass** across rules, dashboard insights, ML, and assistant behavior.
- **ML gates passed** — evidence matcher recall@3 1.0 with 0.0 false-match rate;
  coverage detector 5/5; severity AUC 0.811 versus 0.605 for an O2-only baseline,
  grouped by material description.
- **Pressure-resolved A grades** — PMMA and SIBAL reach Grade A from page-cited BASS-II
  rows, while materials without pressure-bearing evidence stay capped at B or C.
- **Six source-linked case studies**, including the PMMA negative margin and the
  Kevlar/PBI 1-g-only evidence gap.
- **Offline runtime** — no external API is needed during the demo.

### What we learned

Absence of evidence is not evidence of safety. The most useful output is often not a
grade but a defensible statement of what is missing and which test would change the
decision. Explicitly capping the grade when pressure is missing made the tool more
credible, not less.

### What is next

- Extend the pressure-resolved external layer to Saffire and Nomex evidence.
- Run a formal 25-query Cactus routing benchmark.
- Expand configuration-level evidence beyond the current R8 layup cap.
- Polish the printable dossier PDF for engineering handoff.

### Built with

`python` `fastapi` `jinja2` `sqlite` `pandas` `numpy` `scikit-learn` `pymupdf`
`cactus-3` `needle` `javascript` `css` `playwright`

### Try it out

- Project site: `https://diyongamage.github.io/firebreak/` (replace with the custom domain once claimed)
- Repo: `https://github.com/DiyonGamage/firebreak`
- Video: `{{VIDEO_URL}}`
- Run locally: `python -m uvicorn app.main:app --port 8010` then open
  `http://127.0.0.1:8010`
- Offline demo notes: section 4 below.

### Data and attribution

NASA PSI (BASS-II, Saffire-I/II/III, ACME-BRE, SPICE via the public PSI API), NASA NTRS
(7 reports, including the BASS-II summary report and TB 26-05), NASA Standards
(JSC 29353D, NASA-STD-6001B Change 3). Full citations and links: `docs/sources.md`.
MAPTIS and all authenticated sources are excluded.

### Limitations (state these on the project page)

Screening support only — not certification, flight approval, or a substitute for
NASA-STD-6001 Test 1. Grade A depends on page-cited pressure-bearing microgravity
evidence, which currently covers PMMA and SIBAL only; other materials remain capped at B
or C. The severity model is scoped to BASS-II material classes and CO2-rise, not
ignition or flame spread. Cactus is an optional local router, not a predictor.

---

## 2. 90-second video

Target length **88–90 s**. Narration is ~190 words; leave room for pauses and the title.

### Script

| Time | Visual | Narration |
|---|---|---|
| 0:00–0:08 | Title card over the hero screenshot. Text: **FIREBREAK** / *Know what the evidence actually supports.* | Fire in microgravity doesn't follow Earth rules. NASA's own data shows PMMA can keep spreading at 13.6% oxygen — below the 16% where it blows out in 1-g. |
| 0:08–0:20 | Split screen: `docs/screenshots/02-assessment.png` and a text card: **−2.4% O₂ margin**. | That negative margin is why engineers need evidence, not intuition. Firebreak turns NASA microgravity tests, standards, and literature into source-linked A-to-D evidence grades. |
| 0:20–0:38 | Live screen recording. Type `PMMA`, select **ISS Internal**, click **Assess evidence**. Hold on the Grade A card. | Ask for PMMA at ISS atmosphere. Firebreak returns Grade A and high risk: a documented microgravity spread outcome at 1 atm, anchored to a page-cited test. |
| 0:38–0:50 | Scroll the evidence ledger; highlight the NTRS/PSI links and the sensitivity panel. | Every row links to the original test or report. The sensitivity panel shows exactly what would change the grade. |
| 0:50–1:02 | Switch atmosphere to **Lunar/Mars Surface (HLS max)**; show Grade C and the out-of-envelope flag; cut to the Gap Map. | Ask the same material for the lunar surface: oxygen is outside the tested envelope, and the grade drops to C. The Gap Map ranks missing evidence across material classes. |
| 1:02–1:14 | Terminal: `python -m pytest -q` → `55 passed`. Then the validation table or `artifacts/ml_severity_metrics.json`. | 637 curated records, 501 pages of NASA documents, a 100% extraction audit, 55 passing tests, and a scoped CO2-rise screen at 0.811 AUC against a 0.605 baseline, with 80% conformal sets and explicit abstention outside support. |
| 1:14–1:24 | Footer boundary text and the **OFFLINE-READY** badge; toggle Wi-Fi off if recording live. | Firebreak does not fabricate. It refuses to fill missing pressure, labels every limitation, and runs offline. |
| 1:24–1:30 | End card: **FIREBREAK** / *Know what the evidence actually supports.* / repo URL. | Firebreak. Know what the evidence actually supports. |

### Assets

- `docs/video/title-card.png` — 1920×1080 title card
- `docs/video/end-card.png` — 1920×1080 end card with repo and site URLs
- `docs/video/narration.txt` — timecoded narration, ~175 words
- `docs/screenshots/01-overview.png` — evidence dashboard, full page (1440 px)
- `docs/screenshots/02-assessment.png` — Grade A card, reasons, gaps, sensitivity
- `docs/screenshots/03-gap-map.png` — Gap Map and verified anchors
- `docs/screenshots/04-library.png` — source-document search
- Live capture: PMMA ISS → lunar surface, ledger scroll, Gap Map
- Terminal capture: `python -m pytest -q`
- Title/end card text and repo URL
- Royalty-free background music at low volume; optional captions

### Recording notes

- Record at 1920×1080, browser zoom 100%, clean profile, bookmarks bar hidden.
- Pre-load the server and the PMMA result before recording; type only the material name.
- Keep the cursor movements deliberate and slow; pause 0.5 s on each grade.
- Do **not** run live Cactus in the timed video; the assistant panel's cached Cactus run is
  instant, and the deterministic router is the default.
- Record with Wi-Fi disabled so the offline badge claim is visibly true.
- Export H.264 MP4, ≤ 90 s, audio normalized to about −16 LUFS.
- Upload as **public** or **unlisted** (not private) and paste the URL above.

---

## 3. Submission checklist

### Blockers — resolve before submitting

- [x] **Create the public git repository.** Public repo:
  `https://github.com/DiyonGamage/firebreak`.
- [x] **Add an open-source LICENSE.** MIT, copyright 2026 LFR.
- [x] **Confirm the team name:** LFR.
- [ ] **Confirm virtual judging time and platform** for Kandy. Not announced as of
  2026-11-14; proceed with the offline screen-share plan.
- [ ] **Record and upload the 90 s video**; add the public URL.
- [ ] **Publish the project page** with the copy in section 1.
- [x] **Publish the showcase site** — `https://diyongamage.github.io/firebreak/`.
- [ ] **Claim the free domain** (`spaceapps.earth`) and attach it to Pages — section 5.

### Project page fields

- [ ] Title, tagline, challenge selected
- [ ] Short and long descriptions
- [ ] How it works / How we built it / Challenges / Accomplishments / What we learned /
      What is next / Built with
- [ ] Repo URL, video URL, try-it-out instructions
- [ ] Gallery: screenshots 01–04
- [ ] Team members listed
- [ ] Data attribution and limitations included

### Eligibility and integrity

- [x] Repo is public and contains code, tests, build scripts, and attribution
- [x] Open license present (MIT)
- [ ] No MAPTIS or authenticated data redistributed
- [ ] No fabricated measurements, outcomes, or pressure values
- [ ] Claims match `docs/validation.md` (100% audit, 55 tests, ML metrics)
- [ ] Video ≤ 90 s and publicly viewable
- [ ] Submission completed before **15 Nov 2026 23:59 SLST**

### Final pre-submit verification

```powershell
python -m pytest -q                 # 55 passed
python scripts\smoke_e2e.py --cactus # PASS: API, UI, assistant, Cactus
python scripts\audit_extraction.py  # 100%
python scripts\eval_ml.py           # gates passed
curl http://127.0.0.1:8010/healthz  # {"status":"ok","experiments":637,"documents":9}
```

---

## 4. Offline demo notes

### One-time build (with network)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\build_data.py
python scripts\build_docs.py
python scripts\eval_ml.py
python scripts\audit_extraction.py
python scripts\build_case_studies.py
```

### Preflight (before judging)

```powershell
python -m pytest -q
python -m uvicorn app.main:app --port 8010
```

Open `http://127.0.0.1:8010`. Confirm the header shows **EVIDENCE GRADED /
OFFLINE-READY** and the footer shows 637 records, 148 solid-material tests, 9 documents,
and AUC 0.811. Disable Wi-Fi and reload once; the page must render identically.

### 3-minute demo path

1. **Home (0:00)** — one sentence on the negative O2 margin; do not tour the UI.
2. **PMMA / ISS Internal (0:20)** — assess. Point to Grade A / high risk, the page-cited
   microgravity spread at 20.7% O2 and 1 atm, the 12 matched tests, and the sensitivity
   panel. Emphasize: pressure is reported, so the A anchor is legitimate.
3. **PMMA / Lunar surface (1:00)** — assess. Grade C, outside tested envelope. This is
   the honesty feature: a well-studied material still downgrades.
4. **Gap Map (1:30)** — Kevlar/PBI Grade C (two 1-g anchors, no microgravity) vs PMMA
   and SIBAL A; explain ranked gaps.
5. **Evidence ledger (1:50)** — click the NTRS source link; show the page-cited row.
6. **Library search (2:10)** — search `PMMA margin` or `Test 1`; show NTRS/standard hits.
7. **Offline assistant (2:30)** — ask `Assess SIBAL at ISS internal` with the deterministic
   router; show the tool trace. Optionally click **See a cached Cactus Needle run** to show
   the local-model route without waiting.
8. **Close (2:50)** — screening support, not certification; repo and video links.

### 60-second version

PMMA ISS → Grade A → lunar surface → Grade C → Gap Map → one source link → close.

### Contingencies

- **Server fails:** restart `python -m uvicorn app.main:app --port 8010`; data is local.
- **Port busy:** use `--port 8011` and open the matching URL.
- **Totally offline machine:** run from the built `data/processed/firebreak.sqlite` and
  cached document text; no network calls are made at runtime.
- **Projection too small:** increase browser zoom to 125%; the layout is responsive.
- **Judges ask for Cactus:** open the cached Cactus Needle run in the assistant panel. Live
  Cactus is available through `/api/assistant?engine=cactus`; explain the 12–36 s CPU cost.
- **No microphone:** use the video; the demo path above is the live backup.
- **Backup assets:** screenshots 01–04, `artifacts/*.json`, the recorded video, and a
  printed dossier PDF.

---

## 5. Global Offers — domain and hosted project site

The 2026 Global Offers are optional and are not scored directly. Use only the ones that
produce something a judge can click. For Firebreak that is **one domain** and **free
static hosting**; the other offers add nothing to a microgravity flammability screener.

### 5.1 Claim the free domain (5 minutes, one per team)

1. Open `https://www.spaceapps.earth/`.
2. Enter the project name and contact email, then **Get it Now**. You are sent to the
   Porkbun cart.
3. Search a non-premium name. Suggested: `firebreak.space`, `firebreak.xyz`,
   `firebreakscreen.space`. Premium names are not covered by the offer.
4. Complete the Porkbun account and checkout at $0. Verify the email so the domain
   activates.
5. Record the exact domain. Do not claim a second offer unless it is actually used.

### 5.2 Publish the project site on GitHub Pages

`docs/index.html` is a self-contained showcase page. It uses the screenshots in
`docs/screenshots/` and no external assets, so Pages can serve it directly.

```powershell
gh api -X POST repos/DiyonGamage/firebreak/pages `
  -f "source[branch]=main" -f "source[path]=/docs"
```

The site is live at `https://diyongamage.github.io/firebreak/` (Pages is enabled,
source `main` / `docs`). The custom domain replaces that URL once DNS resolves.

### 5.3 Point the domain at Pages

At Porkbun → DNS for the claimed domain:

| Type | Host | Value |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `diyongamage.github.io` |

Then attach the domain to the site and turn on HTTPS:

```powershell
gh api -X PUT repos/DiyonGamage/firebreak/pages -f cname="YOUR-DOMAIN"
gh api -X PUT repos/DiyonGamage/firebreak/pages -F https_enforced=true
```

DNS and the certificate can take up to an hour. If the deadline is close, submit the
`github.io` URL and add the domain when it resolves.

Once the domain is live, add one honest credit line to the footer of `docs/index.html`:

```html
<p class="colophon">Domain provided by GoDaddy Registry through the NASA Space Apps 2026 Global Offers.</p>
```

### 5.4 Offers to skip

| Offer | Why not |
|---|---|
| Meteomatics Weather API | Firebreak has no weather or Earth-observation data. Adding it would be decoration. |
| Microsoft Planetary Computer | Same: EO data is unrelated to microgravity flammability. |
| Azure / Google Cloud | Only worth it if you deploy the live app; `Dockerfile` is ready for either. A live URL needs your account and card verification, so do it only with time to test. |
| GitHub Copilot / Microsoft Copilot / Teams | Claim only if the team actually uses them; no artifact ends up in the submission. |
| Miro Business Plan / templates | Planning only. A screenshot of a storyboard is not project evidence. |

### 5.5 Optional live deploy

`Dockerfile` serves the app with the 0.5 MB processed database and no raw PDFs:

```powershell
docker build -t firebreak .
docker run -p 8080:8080 firebreak
```

- Azure App Service (Web App for Containers): set `WEBSITES_PORT=8080`, then deploy the
  image. Requires an Azure account with the $200 trial credit.
- Google Cloud Run: push the image to Artifact Registry and deploy with
  `--allow-unauthenticated --port 8080`. Requires the free-trial billing account.

If either deploy is tested, add the matching credit line to the site footer
(`Hosted on Microsoft Azure` or `Hosted on Google Cloud`, plus `through the NASA Space
Apps 2026 Global Offers`). If neither is tested by 15 Nov, do not list a live URL. The
offline screen-share demo is the reliable path.
