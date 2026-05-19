# Chapter 7 — Occurrence Timing and Gap Analysis

## Vignette: When Did Members Have ED Visits Between Ages 18-21?

You know from Chapter 6 that 67.4% of members had at least one ED
visit between ages 18 and 21, and that nearly half had multiple visits.
Now the question is: *when* did those visits happen — and does the
gap between visits differ by diagnosis?

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
`n_with_3th` are validated properties of `OccurrenceResultTiming`.

**Problem 2 — Faceted histograms need a shared x-axis.** To compare
time-to-first, time-to-second, and time-to-third meaningfully, all
three facets must share the same scale. eventus computes shared limits
from the base bins config and applies them consistently across all
facets.

**Problem 3 — Stratified gap analysis requires condition labels to
survive the pipeline.** After consolidation, condition labels are
pipe-delimited strings per visit record. Joining them back per member
for stratification is non-trivial in a script. The `CohortTimeline`
now carries `occ_ed_visit_icd10_condition` as a first-class column —
declared in `OccurrenceSemantics.descriptor_cols` with
`timeline: unique`. The stratified violin reads it directly.

---

## The eventus solution

Chapter 7 reuses the full pipeline from Chapter 6 Bonus B — same
semantics, same cleaner, same age window. Two new analyzer calls answer
new questions.

### Step 1 — Timing: when did visits happen?

```python
analyzer      = eventus.CohortTimelineOccurrenceAnalyzer(ct, "ed_visit")
timing_result = analyzer.compute_timing(max_n=3)
print(timing_result)
```

```
OccurrenceResultTiming:
  identity   : ed_visit
  entity_col : patient_id
  entities   : 500
  max_n      : 3
  n_with_1th : 337 (67.4%)
  n_with_2th : 243 (48.6%)
  n_with_3th : 147 (29.4%)
```

The faceted histogram shows time-to-first in teal, time-to-second in
orange, time-to-third in purple — all on the same x-axis (0–1,095
days, the full 18-21 window). Each subplot shows the eligible
denominator in the title automatically.

### Step 2 — Gap distribution

```python
shape_result = analyzer.compute_shape()
print(shape_result)
```

```
OccurrenceResultShape:
  identity      : ed_visit
  entity_col    : patient_id
  entities      : 500
  n_with_gaps   : 243 (48.6%)
  n_with_shape  : 147 (29.4%)
  n_with_memory : 76  (15.2%)
```

```python
plotter = eventus.OccurrenceResultShapePlotter(shape_result, shape_config)

plotter.plot_mean_gap_violin(
    path          = "output/ed_visit_gap_violin.png",
    violin_config = gap_violin_config,
)
```

### Bonus — Stratified by condition

```python
plotter.plot_mean_gap_violin_stratified(
    path            = "output/ed_visit_gap_by_condition.png",
    cohort_timeline = ct,
    stratify_by     = "icd10_condition",
    violin_config   = stratified_config,
)
```

The method reads `occ_ed_visit_icd10_condition` directly from the
`CohortTimeline` — no manual join required. The plotter raises if
more than `max_groups` unique condition combinations are found without
explicit categories declared in the config.

The signal simulation — where conditionA has λ=1.0/year, conditionB
λ=1.5/year, and conditionC λ=2.0/year — produces a clear pattern:

| Group | Median mean gap |
|---|---|
| conditionA only | ~220 days |
| conditionB only | ~207 days |
| conditionA + conditionB | ~148 days |
| conditionA + conditionC | ~143 days |
| conditionB + conditionC | ~141 days |
| conditionA + conditionB + conditionC | ~140 days |

Members with comorbid conditions have shorter gaps between ED visits
than single-condition members — consistent with the higher visit rates
assigned to conditionB and conditionC. Statistical tests can be applied
directly to `shape_result.data["mean_gap"]` grouped by condition. The
plotting shows the pattern is there to find.

---

## What this demonstrated

- **Shrinking denominators are validated** — `OccurrenceResultTiming`
  carries `n_with_nth` as a validated property for each nth. The right
  denominator appears in each subplot title automatically.

- **Shared x-axis is declared in config** — the base bins config drives
  the shared scale across all facets. All three are comparable without
  any manual limit computation.

- **Descriptor columns survive into the `CohortTimeline`** — declaring
  `icd10_condition` with `timeline: unique` causes the `CohortTimeline`
  to carry `occ_ed_visit_icd10_condition` per member. The stratified
  violin reads it via `ct.get_occurrence_descriptor()`. No join needed.

- **The analyzers did not change** — adding descriptor carriage
  required changes to `DescriptorColConfig`, `cohort_timeline_utils`,
  and `CohortTimeline`. Every component in between — cleaners,
  analyzers, intermediates — required zero changes. The layer
  boundaries are load-bearing walls.

- **`primary_condition` is a property of the member, not the visit** —
  stored in `simulated_member_demographics.csv`, it declares the
  scientific ground truth. The condition labels on individual visits
  reflect this 80% of the time, with 20% noise — realistic for
  administrative claims data.

---

> *Claude estimated a script-based equivalent of this analysis would
> require on the order of 240 lines — before accounting for the
> per-entity age window observation period (~75 additional lines) and
> the condition stratification join (~30 additional lines). The
> comparison argument was made in full across Chapters 1-6. The
> remaining chapters demonstrate the analytical depth of the package.*

---

*Chapter 8 — Co-occurrence analysis. See `vignette_08_cooccurrence.md`.*
