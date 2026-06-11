# Chapter 7 — Event Timing and Gap Analysis

## Vignette: When Did Members Have ED Visits Between Ages 18-21?

The event volume analysis found that 67.6% of members in the signal
cohort had at least one ED visit between ages 18 and 21, and that more
than half had multiple. Now the question is: *when* did those visits
happen — and does the gap between visits differ by diagnosis?

Two analytical steps:

1. **Timing** — how many days after turning 18 did members have their
   first, second, and third ED visit?
2. **Gap** — among members with multiple visits, how long between them?
   And does that gap differ by condition?

---

### The three problems

**Problem 1 — Each nth timing has a different denominator.** Time to
first visit is defined for members with at least 1 visit. Time to
second for members with at least 2. Time to third for members with at
least 3. A script must track three different denominators manually.
eventus tracks them automatically — `n_with_1th`, `n_with_2th`,
`n_with_3th` are validated properties of `EventResultTiming`.

**Problem 2 — Faceted histograms need a shared x-axis.** To compare
time-to-first, time-to-second, and time-to-third meaningfully, all
three facets must share the same scale. eventus computes shared limits
from the base bins config and applies them consistently across all
facets.

**Problem 3 — Stratified gap analysis requires condition labels to
survive the pipeline.** After consolidation, condition labels are
pipe-delimited strings per visit record. Joining them back per member
for stratification is non-trivial in a script. The `CohortTimeline`
carries `evt_ed_visit_icd10_condition` as a first-class column —
declared in `EventSemantics.descriptor_cols` with
`timeline: unique`. The stratified violin reads it directly.

---

## The eventus solution

This chapter reuses the pipeline from the previous chapter — same
semantics, same cleaner, same age window. Both a null cohort (uniform
visit rates across conditions) and a signal cohort (conditionB and
conditionC have higher rates) are run through the same code.

### Step 1 — Timing: when did visits happen?

```python
analyzer      = eventus.CohortTimelineEventAnalyzer(ct, "ed_visit")
timing_result = analyzer.compute_timing(max_n=3)
print(timing_result)
```

**Null cohort:**
```
EventResultTiming:
  identity   : ed_visit
  entity_col : patient_id
  entities   : 800
  max_n      : 3
  n_with_1th : 514 (64.2%)
  n_with_2th : 382 (47.8%)
  n_with_3th : 254 (31.8%)
```

**Signal cohort:**
```
EventResultTiming:
  identity   : ed_visit
  entity_col : patient_id
  entities   : 800
  max_n      : 3
  n_with_1th : 541 (67.6%)
  n_with_2th : 454 (56.8%)
  n_with_3th : 354 (44.2%)
```

The signal cohort has higher penetration at every nth event — 67.6%
vs 64.2% for first visit, 56.8% vs 47.8% for second, 44.2% vs 31.8%
for third — consistent with elevated visit rates in conditionB and
conditionC. The faceted histogram renders all three nths on the same
x-axis (0–1,095 days). Each subplot title shows the eligible
denominator automatically.

### Step 2 — Gap distribution

```python
shape_result = analyzer.compute_shape()
print(shape_result)
```

**Null cohort:**
```
EventResultShape:
  identity      : ed_visit
  entity_col    : patient_id
  entities      : 800
  n_with_gaps   : 382 (47.8%)
  n_with_shape  : 254 (31.8%)
  n_with_memory : 154 (19.2%)
```

**Signal cohort:**
```
EventResultShape:
  identity      : ed_visit
  entity_col    : patient_id
  entities      : 800
  n_with_gaps   : 454 (56.8%)
  n_with_shape  : 354 (44.2%)
  n_with_memory : 259 (32.4%)
```

### Step 3 — Stratified by condition

```python
plotter.plot_mean_gap_violin_stratified(
    path            = "output/ed_visit_gap_by_condition.png",
    cohort_timeline = ct,
    stratify_by     = "icd10_condition",
    violin_config   = stratified_config,
)
```

**Null cohort:**

| Group | n | Median mean gap |
|---|---|---|
| conditionA only | 29 | 186d |
| conditionB only | 27 | 243d |
| conditionC only | 32 | 300d |
| conditionA + conditionB | 70 | 230d |
| conditionA + conditionC | 61 | 182d |
| conditionB + conditionC | 70 | 180d |
| conditionA + conditionB + conditionC | 91 | 188d |

**Signal cohort:**

| Group | n | Median mean gap |
|---|---|---|
| conditionA only | 92 | 210d |
| conditionB only | 85 | 184d |
| conditionC only | 103 | 159d |
| conditionA + conditionB | 34 | 178d |
| conditionA + conditionC | 43 | 154d |
| conditionB + conditionC | 75 | 149d |
| conditionA + conditionB + conditionC | 18 | 159d |

In the signal cohort, conditionC alone has the shortest gaps (159d),
consistent with λ=2.0/year. Comorbid members have shorter gaps than
single-condition members in most combinations. The null cohort shows
no such systematic pattern.

---

## What this demonstrated

- **Shrinking denominators are validated** — `EventResultTiming`
  carries `n_with_nth` as a validated property for each nth. The right
  denominator appears in each subplot title automatically.

- **Shared x-axis is declared in config** — the base bins config drives
  the shared scale across all facets. All three nths are comparable
  without any manual limit computation.

- **Descriptor columns survive into the `CohortTimeline`** — declaring
  `icd10_condition` with `timeline: unique` causes the `CohortTimeline`
  to carry `evt_ed_visit_icd10_condition` per member. The stratified
  violin reads it via `ct.get_event_descriptor()`. No join needed.

- **The same code runs on null and signal** — the null and signal
  cohorts produce structurally identical result objects. The difference
  is in the numbers, not in the code or the pipeline.

- **The analyzers did not change** — adding descriptor carriage
  required changes to `DescriptorColConfig`, `cohort_timeline_utils`,
  and `CohortTimeline`. Every component in between — cleaners,
  analyzers, intermediates — required zero changes.

---

*The next chapter examines co-occurrence analysis — do cirrhosis
diagnoses and ED visits co-occur more than chance would predict?*
