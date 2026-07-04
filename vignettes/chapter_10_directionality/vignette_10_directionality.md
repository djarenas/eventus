# Chapter 10 — Event Co-occurrence: Directionality Analysis

## Vignette: Does One Event Tend to Precede the Other?

Chapters 8 and 9 established that some event pairs co-occur above
chance and cluster near each other in time. Chapter 10 asks a
different question: *among patients who had both events, does one
tend to come before the other — or is the ordering essentially random?*

This is not a gap question. Two event pairs can have identical gap
distributions but completely different directionality patterns. A
symmetric ±60-day clustering window produces the same gap ratio as
a directed Exponential(30-day) clustering window — but only one of
them has a consistent ordering. Chapters 9 and 10 answer different
scientific questions.

Three simulation groups illustrate three distinct situations:
simul_5 (respiratory_infection → cardiovascular — directed, strong
signal), simul_4 (MI ↔ stroke — undirected, ~50/50 ordering), and
simul_1 (cirrhosis → ED — directed, one-time exposure). The
directionality analysis correctly characterizes all three.

> *This chapter uses synthetic data designed for the co-occurrence
> vignette series. See `ch8-12_simulation_design.md` for full
> simulation parameters and rationale.*

---

### The five problems

**Problem 1 — Directionality requires a principled per-patient
summary.** A patient with three respiratory infections and two
cardiovascular events has six possible (A, B) pairs. Some may have
A before B, others B before A. A script must make an explicit choice
about how to aggregate this into one observation per patient — or
silently pick the wrong one. `EventCoOccurrenceDirectionalitySummary`
uses the mean signed gap: for each A event, find the nearest B in
either direction, record the signed gap (positive = B after A,
negative = B before A), and take the mean across all A events for
that patient. One number per patient. The choice is documented and
reproducible.

**Problem 2 — The denominator cascade is the worst here.** There
are four distinct denominators in a directionality analysis:
the full cohort (5,000), patients with both events (n_with_both),
patients with a non-NaN signed gap (n_with_signed_gap), and patients
with unambiguous direction (n_a_first + n_b_first, excluding same-day
ties). A script invents column names on the spot and silently uses
the wrong denominator. `EventCoOccurrenceDirectionalityResult`
carries all four counts explicitly. Every percentage shown to the
researcher is computed from the right denominator.

**Problem 3 — The null is not simply 50/50.** For a patient with
one A and one B event placed randomly in a 365-day year, P(A before
B) = 0.50 exactly. But for patients with multiple events, the null
distribution of mean signed gaps depends on event counts and
observation window — it is not centered at zero in general. The
null models handle this correctly: `monte_carlo` draws A and B dates
uniformly, while `rotation` and `label_permutation` resample the
observed dates — all preserving each patient's individual event
counts and observation windows. The fraction A-first under
the null is computed empirically, not assumed.

**Problem 4 — Signed gaps and absolute gaps answer different
questions.** Chapter 9 used absolute (direction-agnostic) gaps
with median aggregation — the right choice for measuring temporal
proximity. Chapter 10 uses signed gaps with mean aggregation — the
right choice for measuring directional tendency. Mean signed gap
can be negative (B tends to precede A on average) in ways that
median absolute gap cannot capture. The two analyses are
complementary, not redundant.

**Problem 5 — Same-day ties are scientifically ambiguous.** A
patient whose nearest (A, B) pair occurred on the same day has
mean signed gap = 0. Their direction is genuinely unknown — not
a missing value, not an error. `EventCoOccurrenceDirectionalitySummary`
records `n_tied` as a first-class count alongside `n_a_first` and
`n_b_first`. The Wilcoxon test excludes ties from the denominator
and documents how many were excluded.

---

## The eventus solution

### Step 1 — Compute directionality summary

```python
analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "respiratory_infection",
    identity_b      = "cardiovascular_event",
)

directionality = analyzer.compute_directionality()
print(directionality)
```

```
EventCoOccurrenceDirectionalitySummary:
  identity_a               : respiratory_infection
  identity_b               : cardiovascular_event
  entities                 : 5,000
  ────────────────────────────────────────────
  n_with_both              : 868 (17.4%)
  n_with_signed_gap        : 868 (17.4%)
  ────────────────────────────────────────────
  n_a_first                : 529 (60.9%)  ← respiratory_infection before cardiovascular_event
  n_b_first                : 323 (37.2%)  ← cardiovascular_event before respiratory_infection
  n_tied                   : 16
  fraction_a_first         : 62.1%
  ────────────────────────────────────────────
  cohort_mean_signed_gap   : 8.2 days
```

`cohort_mean_signed_gap` is the mean of per-patient mean signed
gaps across co-occurring patients. Positive values indicate A tends
to precede B on average across the cohort.

### Step 2 — Compute the directionality test

```python
dir_analyzer = eventus.EventCoOccurrenceDirectionalityAnalyzer(directionality)
dir_test     = dir_analyzer.compute_test(n_permutations=500)
print(dir_test)
```

```
EventCoOccurrenceDirectionalityTest:
  identity_a             : respiratory_infection
  identity_b             : cardiovascular_event
  entities               : 5,000
  n_co_occurring         : 868 (17.4%)
  null_method            : permutation (n_permutations=500)
  ──────────────────────────────────────────────────
  fraction_a_first       : 62.1%
  null_fraction_a_first  : 50.0%
  direction_ratio        : 1.243  (observed/null)
  ──────────────────────────────────────────────────
  cohort_mean_signed_gap : 8.2 days
  null_mean_signed_gap   : -0.1 days
  wilcoxon_statistic     : 154583.0000
  wilcoxon_p             : 1.62e-04
```

### Step 3 — Visualize

```python
plotter = EventCoOccurrenceDirectionalityPlotter(
    dir_test,
    EventCoOccurrenceDirectionalityPlotConfig(),
)
plotter.plot("output/directionality_simul5.png")
```

The figure shows the distribution of per-patient mean signed gaps —
observed vs permutation null. For simul_5 the observed distribution
is right-shifted (positive values dominate — A tends to precede B).
For simul_4 the observed distribution overlaps the null — no
consistent ordering.

---

## Three scenarios, same code

| | simul_5 (resp → cardiac) | simul_4 (MI ↔ stroke) | simul_1 (cirrhosis → ED) |
|---|---|---|---|
| n_with_both | 868 (17.4%) | 385 (7.7%) | 56 (1.1%) |
| fraction_a_first | 62.1% | 52.6% | 74.5% |
| direction_ratio | 1.243 | 1.055 | 1.498 |
| cohort_mean_signed_gap | 8.2 days | 2.4 days | 6.1 days |
| Wilcoxon p | 1.62e-04 | 0.28 (n.s.) | 0.049 |

**simul_4** is the negative control — the symmetric ±60-day window
produces fraction_a_first=52.6%, direction_ratio=1.055, Wilcoxon
p=0.28 — not significant. No consistent ordering detected.

**simul_5** shows a clear directed signal — fraction_a_first=62.1%,
direction_ratio=1.243, Wilcoxon p=1.62e-04. Respiratory infections
precede cardiovascular events more than chance predicts.

**simul_1** shows the strongest direction_ratio (1.498) — cirrhosis
diagnosis precedes ED visits in 74.5% of co-occurring patients.
The Wilcoxon p=0.049 is significant despite only 56 co-occurring
patients. This illustrates an important distinction: simul_1 has a
higher direction_ratio than simul_5 (1.498 vs 1.243) but a weaker
p-value (0.049 vs 1.62e-04) because n=56 vs n=868. Effect size and
statistical power answer different questions.

---

## What this demonstrated

- **Directionality is a distinct analytical dimension** — chapter 9
  showed temporal clustering; chapter 10 shows consistent ordering.
  Two event pairs can have identical gap ratios but completely different
  directionality patterns. The analyses are complementary.

- **The denominator cascade is explicit** — `n_with_both`,
  `n_with_signed_gap`, `n_a_first`, `n_b_first`, `n_tied` are all
  first-class properties. The researcher always knows what fraction
  of the cohort is contributing to the test and why others are excluded.

- **Mean signed gap is the right aggregation for direction** —
  chapter 9 used absolute median gaps for proximity; chapter 10 uses
  mean signed gaps for direction. Different questions, different
  aggregation strategies. The distinction is documented in both chapters.

- **`EventCoOccurrenceDirectionalityAnalyzer` is a second-level
  analyzer** — takes `EventCoOccurrenceDirectionalitySummary` as
  input, not a `CohortTimeline`. The summary is already validated.
  The analyzer adds the statistical layer without re-reading raw data.

- **The permutation null handles the multi-event case correctly** —
  shuffling both A and B dates for each patient independently
  preserves event counts and observation windows. The null fraction
  A-first is computed empirically, not assumed to be 0.50.

- **The open/closed principle holds** — all new classes consume
  existing validated objects. The `CohortTimeline`, cleaners, and
  chapters 8–9 objects required zero changes.

---

### A note on statistical validation

The Wilcoxon signed-rank test and permutation null demonstrated here
are illustrative of the eventus analytical architecture. They have
not been formally evaluated for Type I error control or statistical
power under real administrative claims data conditions. See
`ch8-12_simulation_design.md` for the full statistical disclaimer.

---

*Chapters 8–10 demonstrate a complete co-occurrence analysis
pipeline: presence (chapter 8), temporal proximity (chapter 9), and
directional ordering (chapter 10). Each chapter adds one analytical
dimension. Each uses the same `CohortTimeline` and the same event
streams. No chapter required changes to any previous chapter's code.*
