# Firebreak — 7-slide deck copy (final)

Team **LFR** · Diyon Gamage · NASA Space Apps 2026
Challenge: **Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data**

Links to place on slide 7 and in the submission form:

- Repository: https://github.com/DiyonGamage/firebreak
- Live report: https://diyongamage.github.io/firebreak/

One message per slide. No long paragraphs. Paper-and-ink palette: `#F7F4EC` paper,
`#1C1E22` ink, `#C2410C` ember accent. Serif headlines, sans body, mono labels.

---

## Slide 1 — Title & Team

**Kicker:** NASA SPACE APPS 2026 · FLAME IN FREEFALL

**Headline:** Firebreak

**Subhead:** An evidence-graded dashboard for microgravity fire safety — it ranks the
investigations, grades the materials, and says when the data runs out.

**Footer:** Team LFR · Diyon Gamage · Kandy, Sri Lanka (virtual)

**Visual:** the dashboard screenshot, cropped to the hero and the three findings.

---

## Slide 2 — Problem

**Kicker:** THE PROBLEM

**Headline:** Spacecraft fires start where the data ends.

**Three points only:**

- NASA has flown BASS-II, Saffire I–III, ACME and SPICE, but the findings are scattered
  across 637 rows, 9 reports and 501 pages.
- A materials engineer cannot tell, in one place, which investigation matters for the
  Moon — or whether a material is even supported at 37% oxygen.
- The most dangerous answer is a confident one built on 1-g data. In microgravity, PMMA
  spreads at **13.6% O₂**; in 1-g it blows off at **16% O₂**. A **2.4-point** negative margin.

**Visual:** the two-row contradiction figure (1-g vs microgravity).

---

## Slide 3 — Solution

**Kicker:** THE SOLUTION

**Headline:** Not a chatbot. An evidence court.

**Copy:**

Firebreak grades evidence, not opinions. Every answer carries a grade (A–D), the rows
behind it, and the test that would change it. Four roles then explain the grade —
Curator, Critic, Safety Officer, Experimentalist — and none of them is a language model,
so none of them can invent a fact.

**Three chips:** A–D evidence grade · 11 investigations · 3 fire-safety pillars

---

## Slide 4 — How It Works

**Kicker:** HOW IT WORKS

**Headline:** From 637 rows to one defensible answer.

**Pipeline, five steps:**

1. **Rank** — 11 investigations scored for ISS cabin, airlock, lunar surface and suit.
2. **Retrieve** — material aliasing and O₂ proximity over 148 solid-material tests.
3. **Screen** — one monotonic model estimates BASS-II CO₂ severity, and abstains outside
   PMMA/SIBAL or 13.6–22.2% O₂.
4. **Apply rules** — R1–R10 cap grades for missing pressure, 1-g-only data and layup risk.
5. **Explain** — the evidence court turns the matched rows into four plain statements.

**Visual:** `/investigations` screenshot. **Caption:** every investigation, ranked for the
environment you choose.

---

## Slide 5 — NASA Data

**Kicker:** NASA DATA

**Headline:** Six investigations extracted. Five catalogued honestly.

**Table:**

| Source | Rows | Role |
|---|---:|---|
| BASS-II + NTRS rows | 135 | Pressure-bearing microgravity solid fuels |
| SPICE | 469 | Gas-jet smoke point — context only |
| ACME-BRE | 18 | Gas fuel — excluded from solid grading |
| Saffire-II | 9 | Low-pressure spread at varied O₂ |
| Saffire-I / III | 4 | Metadata-only |
| 9 NTRS documents | 501 pp | Rules, limits, page-cited outcomes |

**Line:** Detection (SAME, SAME-R) and suppression (FLEX) are catalogued, linked, and
shown as **zero extracted rows**. We did not invent data to fill the pillars.

**Visual:** pillars strip — prevention covered, detection and suppression catalogued only.

---

## Slide 6 — Impact

**Kicker:** IMPACT

**Headline:** It tells you what the data cannot support.

**Copy:**

At the lunar-surface preset, **0 of 8 material classes** reach grade A. At ISS cabin,
**2 of 8** are anchored and 2 are provisional. The spacesuit atmosphere — 4.3 psia,
100% oxygen — is **not graded at all**, because no ingested row reports it.

That is the value: a materials engineer sees the gap before the test campaign, not after.

**Three stats:** 0/8 lunar · 2/8 ISS · 0 invented rows

**Boundary line, always spoken:** screening support only — not certification, not flight
approval, not a substitute for NASA-STD-6001 Test 1.

---

## Slide 7 — What's Next + Links

**Kicker:** WHAT'S NEXT

**Headline:** The honest limitation is the roadmap.

**Three next steps:**

1. Extract SAME/SAME-R (detection) and FLEX (suppression), so all three pillars carry rows.
2. Add LUCI and FM2 when NASA publishes partial-gravity data — the corpus has none today.
3. Put the court in front of two materials engineers and record where it is wrong.

**Closing line:** *We do not claim superintelligence. We claim the part that matters:
it ranks the evidence, shows its reasoning, and refuses to answer when the data runs out.*

**Links:** repository and live report, both typed out and clickable.

---

## Speaker notes (30 seconds per slide)

- **1:** Name, team, challenge. One sentence on what Firebreak is.
- **2:** Say the 2.4-point number. It is the whole problem in one figure.
- **3:** Say "none of them is a language model." Pause. It is the differentiator.
- **4:** Follow the five steps with your finger. Do not explain R1–R10 unless asked.
- **5:** Say the zero-rows line out loud. It proves you did not pad.
- **6:** Say 0/8 and 2/8. Then the boundary line.
- **7:** Read the closing line, then give both links.

## Likely questions

| Question | Answer |
|---|---|
| Why this challenge? | The data was already public and unused; the gap was interpretation, not collection. |
| Which NASA data? | PSI investigations PSI-25/98/99/100/20/107 plus nine NTRS documents, all linked in the app. |
| How is it different? | It ranks investigations, grades evidence, and abstains. Most dashboards always answer. |
| What works today? | Every screen in the demo, offline, with 63 passing tests. |
| How did you validate it? | Extraction audit 60/60 fields, retrieval recall@3 1.00, model AUC 0.811, court has unit tests. |
| How was AI used? | Three places: a validated severity model, a local router that never writes answers, rule-generated explanations. |
| Who uses it and what are the limits? | Materials engineers screening before Test 1. Limits: 8 material classes, no partial-gravity data, no suit coverage. |
