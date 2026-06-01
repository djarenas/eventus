# Simulation Design — Co-occurrence Vignettes (Chapters 8–11)

## Purpose

This document describes the synthetic data used in the eventus
co-occurrence vignette series (Chapters 8–11). The data is generated
by `generate_vignette_data_ch8x.py` and is not derived from real
clinical records.

The simulation is designed to demonstrate `EventCoOccurrenceAnalyzer`
and its result objects across five scientifically distinct scenarios.
Each scenario isolates a different dimension of the co-occurrence
question — presence, timing, directionality — so that readers can see
precisely what each analytical method detects and what it misses.

---

## Patient pool

| Property | Value |
|---|---|
| Pool size | 5,000 patients |
| ID format | `D0001` – `D5000` |
| Distinct from | P pool (chapters 1–7) |
| Observation period | 2022-01-01 → 2022-12-31 |
| Seeds | 42–46 (one per simulation group) |

---

## File manifest

| File | Group | Used in |
|---|---|---|
| `ch08_11_simul1_cirrhosis_dx.csv` | simul_1 | Ch 08, 11 |
| `ch08_11_simul1_ed_visits.csv` | simul_1 | Ch 08, 11 |
| `ch08_09_simul2_event_x.csv` | simul_2 | Ch 08, 09 |
| `ch08_09_simul2_event_y.csv` | simul_2 | Ch 08, 09 |
| `ch08_09_simul3_event_x.csv` | simul_3 | Ch 08, 09 |
| `ch08_09_simul3_event_y.csv` | simul_3 | Ch 08, 09 |
| `ch09_10_simul4_mi_events.csv` | simul_4 | Ch 09, 10 |
| `ch09_10_simul4_stroke_events.csv` | simul_4 | Ch 09, 10 |
| `ch10_simul5_respiratory_infections.csv` | simul_5 | Ch 10 |
| `ch10_simul5_cardiovascular_events.csv` | simul_5 | Ch 10 |

---

## The five simulation groups

All five groups share the same 5,000-patient pool. The same patient
(say, D0042) has event streams generated under all five mechanisms.

---

### simul_1 — cirrhosis_diagnosis → ed_visit

**Scientific scenario:** A one-time exposure (cirrhosis diagnosis)
elevates the rate of a recurring outcome (ED visit) AND causes ED
visits to cluster within 90 days after diagnosis. A precedes B
consistently — full signal in all dimensions.

**Why one-time exposure:** Cirrhosis diagnosis is a one-time clinical
event — a patient either has been diagnosed or not. The simulation
generates at most one diagnosis per patient (null dates possible,
no duplicates). This makes simul_1 the canonical scenario for chapter
08's presence analysis, where binary has/hasn't is the right question.

**Why 2% prevalence:** Cirrhosis affects approximately 2% of general
Medicaid populations. This lower prevalence (vs the 7% previously used)
produces ~100 cirrhosis patients in a 5,000-patient cohort — realistic
for administrative claims data and sufficient for stable statistics
(Fisher p~7e-24, prevalence ratio ~2.4x).

| Parameter | Value | Rationale |
|---|---|---|
| Cirrhosis prevalence | 2% (~100 patients) | General Medicaid population |
| ED rate — cirrhosis | λ = 2.0/year | ~4–5× elevated |
| ED rate — no cirrhosis | λ = 0.4/year | Medicaid baseline |
| Noise (10% non-cirrhosis) | λ = 1.2/year | High utilizers |
| Temporal structure | Exponential(mean=45d) after dx, cap 90d | Post-diagnosis clustering |
| Directionality | Diagnosis always precedes clustered ED visits | A→B by construction |
| Duplicate rows | None for cirrhosis (one-time); 5% for ED visits | Realistic claims structure |

**Used in:** Chapters 08 (presence), 11 (survival).

---

### simul_2 — confounding, uniform timing

**Scientific scenario:** Two events that co-occur above chance
because both are independently elevated in the same high-utilizer
patients — not because one causes or precedes the other. Events are
uniformly distributed across the year with no temporal relationship.

**The confounding trap:** Fisher's exact test fires on simul_2 —
the co-occurrence is real. But the gap timing test (chapter 09)
correctly shows no temporal clustering. This teaches the researcher
that elevated presence alone does not imply temporal structure.

| Parameter | Value | Rationale |
|---|---|---|
| High utilizer prevalence | 20% (~1,000 patients) | Common in claims data |
| Event X/Y rate — high utilizer | λ = 3.0/year each | Both elevated independently |
| Event X/Y rate — regular | λ = 0.3/year each | Low baseline |
| Temporal structure | Uniform across year | No mechanism linking X to Y |
| Directionality | Random | Uniform dates, ~50/50 ordering |

**Used in:** Chapters 08 (presence — confounding trap), 09 (gap timing
— no temporal signal despite elevated presence).

---

### simul_3 — pure null

**Scientific scenario:** Two completely independent event streams
with identical rates for all patients. No relationship in prevalence,
timing, or directionality. All statistical tests should return
non-significant results.

**Why λ=0.3:** At λ=0.5 with N=5,000, expected co-occurrence by
chance (~760 patients) makes Fisher's exact non-trivially significant.
At λ=0.3, P(X>0) ≈ 26% and expected co-occurrence by chance (~336
patients) produces a clean Fisher p≈1.00.

| Parameter | Value | Rationale |
|---|---|---|
| Event X/Y rate — all patients | λ = 0.3/year each | Same for everyone |
| Temporal structure | Uniform across year | No clustering |
| Directionality | Random | By construction |

**Used in:** Chapters 08 (presence — negative control), 09 (gap
timing — negative control).

---

### simul_4 — MI ↔ stroke (clustered, undirected)

**Scientific scenario:** Two recurring clinical events (myocardial
infarction and stroke) that cluster near each other in time due to
shared cardiovascular risk, but with no consistent ordering — either
can precede the other.

**Clinical basis:** Patients with elevated cardiovascular risk have
both elevated MI and stroke rates. Post-MI stroke risk and post-stroke
MI risk are both elevated within 90 days (shared pathophysiology:
atrial fibrillation, thromboembolism, hemodynamic instability).
The ordering is genuinely bidirectional.

| Parameter | Value | Rationale |
|---|---|---|
| CV risk prevalence | 10% (~500 patients) | High-risk subgroup |
| MI rate — high CV risk | λ = 1.5/year | Elevated |
| Stroke rate — high CV risk | λ = 1.5/year | Symmetric |
| MI/stroke rate — general | λ = 0.05/0.04/year | Population baseline |
| Temporal structure | Symmetric Uniform(−60, +60) days | Bidirectional clustering |
| Directionality | 50/50 — MI before stroke or stroke before MI | Symmetric window |

**Used in:** Chapters 09 (gap timing — clustering without direction),
10 (directionality — contrast with simul_5).

---

### simul_5 — respiratory_infection → cardiovascular_event (directed)

**Scientific scenario:** Respiratory infections trigger cardiovascular
events within ~30 days — directed A→B temporal relationship. Based on
published literature showing elevated short-term cardiac risk following
respiratory infections.

**Clinical basis:** Kwong et al. (2018) found a 6-fold increase in
myocardial infarction risk in the week following influenza diagnosis.
The simulation uses an 8% trigger probability with Exponential(mean=15
days) — consistent with the short-term risk window observed clinically.

| Parameter | Value | Rationale |
|---|---|---|
| Respiratory infection rate | λ = 1.5/year (all patients) | Moderate-high (includes minor infections) |
| CV trigger probability | 8% per respiratory infection | Based on literature estimates |
| CV trigger timing | Exponential(mean=15 days) after infection | Post-infection risk window |
| Background CV rate | λ = 0.1/year (all patients) | Independent baseline |
| Directionality | Respiratory infection precedes CV event | A→B by construction |

**Used in:** Chapter 10 (directionality — contrast with simul_4).

---

## What each chapter demonstrates

| Chapter | Question | Groups used | Key distinction |
|---|---|---|---|
| Ch 08 | Do A and B co-occur above chance? | simul_1 vs simul_2 vs simul_3 | simul_1/2 show elevated presence; simul_3 does not |
| Ch 09 | Are gaps shorter than independence predicts? | simul_4 vs simul_2 vs simul_3 | simul_4 shows clustering; simul_2/3 do not |
| Ch 10 | Does A consistently precede B? | simul_5 vs simul_4 | simul_5 directed; simul_4 undirected |
| Ch 11 | Time to first event after exposure | simul_1 vs simul_3 | simul_1 has signal; simul_3 is null |

**The pedagogical progression:** Chapter 08 cannot distinguish
simul_1 from simul_2 — both show elevated presence. Chapter 09
distinguishes simul_4 (clustered gaps) from simul_2 (uniform gaps
despite elevated presence). Chapter 10 distinguishes simul_5
(directed) from simul_4 (undirected). Each chapter adds one dimension
the previous chapter could not see.

---

## Reproducibility

All simulations use `numpy.random.default_rng` with fixed seeds:

| Group | Seed |
|---|---|
| simul_1 | 42 |
| simul_2 | 43 |
| simul_3 | 44 |
| simul_4 | 45 |
| simul_5 | 46 |

Running `generate_vignette_data_ch8x.py` twice produces identical files.

---

## Statistical disclaimer

The statistical tests demonstrated in the co-occurrence vignette series
— the permutation-based KS test (chapter 9), the Wilcoxon signed-rank
test against a permutation null (chapter 10), and the Fisher's exact
test (chapter 8) — are designed to demonstrate the analytical
architecture of eventus, not to serve as formally validated inferential
procedures.

**These methods have not been evaluated for:**

- Type I error control under the range of conditions encountered in
  real administrative claims data
- Statistical power under realistic effect sizes and sample sizes
- Robustness to irregular observation periods, informative censoring,
  correlated event streams, or seasonal variation in event rates

The synthetic simulations used here are designed to produce clear,
interpretable signals and nulls. Real administrative claims data is
considerably more complex — event rates vary by season, observation
windows are irregular, and event streams are correlated in ways not
captured by independent Poisson processes.

**The architecture is the contribution.** eventus is deliberately
designed to make formal validation straightforward. A researcher can:

- Replace the permutation mechanism with a parametric or analytical null
- Substitute a different test statistic (e.g. Mann-Whitney, log-rank)
- Change the per-patient aggregation strategy (median → mean, nearest
  pair → all pairs) without modifying any other component

Each of these substitutions requires changing one method in one
analyzer class. The intermediate result objects, the CohortTimeline,
the cleaners, and the visualizers require no changes. This is the
open/closed principle applied to statistical methodology.

Formal validation of the statistical properties of these methods under
realistic administrative claims data is left to future work and is
explicitly outside the scope of this software paper.

---

## Limitations

**Independence assumptions within groups.** Event streams are
generated independently per patient within each group. Real clinical
data has complex temporal dependencies not captured here.

**simul_5 respiratory infection rate.** λ=1.5/year includes minor
respiratory infections (colds, flu-like illness) not just confirmed
influenza. The trigger probability (8%) is calibrated to the more
severe infections most likely to elevate cardiac risk.

**No censoring in chapters 08–10.** All patients have a full 2022
observation period. Chapter 11 introduces right-censoring for
patients who never experienced the outcome event.

**Synthetic clinical labels.** simul_2 and simul_3 use generic event
names (`simul2_event_x`, etc.) rather than clinical labels. This is
intentional — the simulation parameters are not calibrated to any
specific clinical relationship.

**One-time exposure design (simul_1).** Cirrhosis diagnosis is
generated as a one-time event per patient (at most one row, null
dates possible but no duplicates). This correctly models the clinical
reality and is the right design for chapter 08's presence analysis.
