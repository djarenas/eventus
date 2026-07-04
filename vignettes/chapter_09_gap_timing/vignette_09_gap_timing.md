# Chapter 9 — Event Co-occurrence: Gap Timing Analysis

## Vignette: Are Co-occurring Events Closer in Time Than Chance Predicts?

Chapter 8 established that some event pairs co-occur above chance —
a presence question. Chapter 9 asks a different question: *among
patients who had both events, how close in time were they — and is
that proximity shorter than what independence would predict?*

This is not a directionality question. Chapter 9 does not ask whether
A came before B. It asks whether A and B cluster near each other in
time, in either direction, more than chance alone would produce.

Three simulation groups answer three different scientific situations:
simul_4 (MI ↔ stroke — clustered, undirected), simul_1 (cirrhosis →
ED — clustered, directed), and simul_3 (pure null — no temporal
structure). The gap analysis correctly distinguishes all three from
the same permutation null.

> *This chapter uses synthetic data designed for the co-occurrence
> vignette series. See `ch8-12_simulation_design.md` for full
> simulation parameters and rationale.*

---

### The five problems

**Problem 1 — Gap measurement is not a simple date difference.** A
patient with one MI and five stroke records has five possible distances
from the MI to a stroke, and five distances from each stroke back to
the MI. A script must make this choice explicitly or silently pick the
wrong one. `EventCoOccurrenceGapSummary` uses a principled definition:
for each A event, find the nearest B in either direction, take the
median across all A events for that patient. One number per patient,
per direction. The choice is documented, reproducible, and consistent
across all analyses.

**Problem 2 — The null is patient-specific, not universal.** A
patient with five strokes will have a shorter expected nearest gap to
any MI date purely by chance — the more events, the smaller the
expected nearest gap. A single uniform null ignores this.
`EventCoOccurrenceGapAnalyzer` offers three null models via
`null_method`, all preserving each patient's event counts and
observation window: `uniform_monte_carlo` (default) draws A and B dates
uniformly (assumes no burstiness); `rotation` shifts the observed B
sequence by a random within-window offset, preserving each type's own
clustering; `label_permutation` reassigns A/B labels over the pooled
observed dates. The null is honest
about what each patient contributes.

**Problem 3 — Per-patient summary vs all-pairs.** Pooling all
individual gaps across patients lets patients with many events
dominate the cohort distribution. A patient with 10 MI events
contributes 10 gap observations; a patient with 1 contributes 1.
`EventCoOccurrenceGapSummary` summarizes to one median per patient
first. Every patient contributes equally to the cohort distribution.

**Problem 4 — The KS p-value is unreliable at large N.** With
5,000 patients and 500 permutations, even trivially small
distributional differences can produce significant p-values. The
gap ratio — observed median divided by null median — is the primary
effect size. A ratio of 0.45 means observed gaps are about half of
what independence would predict. A ratio of 1.0 means no temporal
signal. The p-value confirms the direction; the ratio conveys the
magnitude.

**Problem 5 — Visual decisions belong in a config.** KDE bandwidth,
colors, whether to show median lines — these are scientific choices
that affect what the reader sees. `EventCoOccurrenceGapPlotConfig`
versions every visual decision. The default config produces a
publication-ready figure; changing one parameter and rerunning
produces a different figure while the original config remains intact.

---

### A note on script complexity

A script implementing this analysis for a single event pair would
require on the order of 300+ lines: date parsing, deduplication with
audit trail, per-entity nearest-gap computation in both directions,
vectorized permutation null (500 permutations × N entities), KS test,
and a two-panel KDE figure with median annotations. Chapter 9 runs
three complete analyses — simul_4, simul_1, and simul_3 — in 159
total lines including comments, blank lines, and docstring. Each
analysis produces a cleaning report, a gap summary, a statistical
test, and a publication-quality figure.

---

## The eventus solution

### Step 1 — Compute gaps

`compute_gaps()` reuses the same `CohortTimeline` pipeline from
chapter 8. No new cleaning logic — just a new analyzer call.

```python
analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "mi_event",
    identity_b      = "stroke_event",
)

gaps = analyzer.compute_gaps()
print(gaps)
```

```
EventCoOccurrenceGapSummary:
  identity_a               : mi_event
  identity_b               : stroke_event
  entities                 : 5,000
  ────────────────────────────────────────────
  n_co_occurring           : 385 (7.7%)
  n_with_gap_a_to_b        : 385 (7.7%)
  n_with_gap_b_to_a        : 385 (7.7%)
  ────────────────────────────────────────────
  cohort_median_a_to_b     : 26.0 days
  cohort_median_b_to_a     : 30.5 days
```

385 co-occurring patients. Cohort median gap: 26 days from MI to
nearest stroke, 30.5 days from stroke to nearest MI. Both directions
computed, both reported.

### Step 2 — Compute the gap test

```python
gap_analyzer = eventus.EventCoOccurrenceGapAnalyzer(gaps)
gap_test     = gap_analyzer.compute_test(n_iterations=500)
print(gap_test)
```

```
EventCoOccurrenceGapTest:
  identity_a             : mi_event
  identity_b             : stroke_event
  entities               : 5,000
  n_co_occurring         : 385 (7.7%)
  null_method            : uniform_monte_carlo (n_iterations=500)
  ──────────────────────────────────────────────────
  mi_event → nearest stroke_event
  ──────────────────────────────────────────────────
  observed median gap    : 26.0 days
  null median gap        : 57.3 days
  ks_statistic           : 0.4514
  ks_p                   : 5.80e-72
  gap_ratio              : 0.454  (observed/null median)
  ──────────────────────────────────────────────────
  stroke_event → nearest mi_event
  ──────────────────────────────────────────────────
  observed median gap    : 30.5 days
  null median gap        : 68.1 days
  ks_statistic           : 0.4282
  ks_p                   : 1.98e-64
  gap_ratio              : 0.448  (observed/null median)
```

Gap ratio 0.45 in both directions — MI and stroke events are about
half as far apart as independence would predict. The near-identical
ratios in both directions (0.454 vs 0.448) reflect the symmetric
simulation design: the ±60-day clustering window is bidirectional.

### Step 3 — Visualize

```python
plotter = EventCoOccurrenceGapPlotter(
    gap_test,
    EventCoOccurrenceGapPlotConfig(),
)
plotter.plot("output/gap_distributions_simul4.png")
```

The figure shows two panels — one per direction. In each panel, the
teal observed distribution is clearly left-shifted relative to the
coral permutation null. The median lines at 26d and 57d are visually
separated. The clustering is visible at a glance.

---

## Three scenarios, same code

The same pipeline runs on simul_1 (cirrhosis → ED, directed signal)
and simul_3 (pure null). The gap test correctly characterizes all three:

```
EventCoOccurrenceGapTest — simul_1 (cirrhosis → ED):
  cirrhosis_diagnosis → nearest ed_visit
  observed median gap    : 29.5 days
  null median gap        : 79.9 days
  gap_ratio              : 0.369  (observed/null median)
  ks_p                   : 1.84e-05

EventCoOccurrenceGapTest — simul_3 (pure null):
  simul3_event_x → nearest simul3_event_y
  observed median gap    : 99.0 days
  null median gap        : 97.2 days
  gap_ratio              : 1.019  (observed/null median)
  ks_p                   : 0.9535
```

**The contrast:**

| | simul_4 (MI ↔ stroke) | simul_1 (cirrhosis → ED) | simul_3 (null) |
|---|---|---|---|
| n_co_occurring | 385 (7.7%) | 56 (1.1%) | 335 (6.7%) |
| Observed median (A→B) | 26.0 days | 29.5 days | 99.0 days |
| Null median (A→B) | 57.3 days | 79.9 days | 97.2 days |
| Gap ratio | 0.454 | 0.369 | 1.019 |
| KS p | 5.80e-72 | 1.84e-05 | 0.95 (n.s.) |

Three scientifically distinct situations — all correctly identified
by the same two method calls: `compute_gaps()` and `compute_test()`.

**simul_3 gap ratio = 1.019** — essentially exactly 1.0. The
permutation null correctly identifies no temporal structure.

**simul_1 gap ratio = 0.369** — tighter than simul_4. The directed
Exponential(45 days) clustering in simul_1 produces shorter observed
gaps relative to the null than the symmetric ±60-day window in simul_4.

**simul_4 gap ratios are symmetric (0.454 vs 0.448)** — nearly
identical in both directions, confirming the undirected simulation
design worked correctly.

---

## What this demonstrated

- **Gap measurement is a design decision** — nearest neighbor in
  either direction, median per patient. `EventCoOccurrenceGapSummary`
  makes this choice explicit. The researcher knows exactly what they
  are comparing.

- **The null is patient-specific** — `EventCoOccurrenceGapAnalyzer`
  shuffles both A and B dates independently for each patient,
  preserving event counts and observation windows. A universal null
  would be wrong.

- **The gap ratio is the primary effect size** — observed median
  divided by null median. Values below 1 indicate temporal clustering;
  values near 1 indicate no temporal signal. At large N the KS
  p-value detects trivially small differences; the gap ratio conveys
  magnitude.

- **`EventCoOccurrenceGapAnalyzer` is a second-level analyzer** —
  it takes an `EventCoOccurrenceGapSummary` as input, not a
  `CohortTimeline`. The gap summary is already validated. The analyzer
  adds the statistical layer without re-reading any raw data.

- **Visual decisions are versioned** — `EventCoOccurrenceGapPlotConfig`
  holds every visual decision. The default config produces a
  publication-ready figure.

- **The open/closed principle holds** — `EventCoOccurrenceGapAnalyzer`
  and `EventCoOccurrenceGapPlotter` are new classes consuming existing
  validated objects. The `CohortTimeline`, cleaners, and chapter 8
  objects required zero changes.

---

---

### A note on statistical validation

The permutation null and KS test demonstrated here are illustrative of
the eventus analytical architecture. They have not been formally
evaluated for Type I error control or statistical power under the range
of conditions encountered in real administrative claims data —
irregular observation periods, informative censoring, correlated event
streams, and seasonal variation may all affect test behavior.

The architecture is designed to make such validation straightforward:
the permutation mechanism, test statistic, and per-patient aggregation
strategy can each be replaced independently without changing any other
component. See `ch8-12_simulation_design.md` for the full statistical
disclaimer.

---

*The next chapter asks whether one event tends to precede the other —
among co-occurring pairs, is the ordering consistent or random?*
