# Chapter 8 — Occurrence-Event Co-occurrence Analysis

## Vignette: ED Visits and Hospitalizations in 2022

You have two event streams for the same cohort: emergency department
visits (point-in-time occurrences) and inpatient hospitalizations
(interval events). The scientific question is not just whether members
had both — it is *how they relate in time*.

Do ED visits tend to precede hospitalizations? Do members return to
the ED shortly after discharge? How many ED visits happen during a
hospitalization stay itself?

These questions require a new analytical layer — one that reads both
streams from the same `CohortTimeline` and computes temporal
relationships between them.

---

### The three problems

**Problem 1 — Two streams, one timeline.** ED visits and
hospitalizations are different data types with different structures
— point-in-time vs interval. They need to be cleaned, validated, and
filtered separately, then assembled into a single object that
preserves both. The `CohortTimeline` holds both. The analyzer reads
both.

**Problem 2 — The visual before the statistics.** Before computing
any numbers, the stacked timeline shows the raw pattern — red
hospitalization bars and teal ED visit dots on the same per-member
axis. The reader sees co-occurrence visually before the statistics
quantify it.

**Problem 3 — Nearest-neighbor gaps across two streams.** For each
member, find the nearest hospitalization after each ED visit, and the
nearest ED visit after each discharge. Report the gap. Average across
all qualifying pairs for that member. This is not a standard pandas
groupby — it requires parsing two pipe-delimited date streams and
computing pairwise temporal distances.

---

## The eventus solution

### Step 1 — Clean both streams independently

```python
hosp_cleaner = eventus.EventsCleaner(hosp_raw, hosp_sem, hosp_config)
hospitalizations = hosp_cleaner.clean()

ed_cleaner = eventus.OccurrencesCleaner(ed_raw, ed_sem, ed_config)
ed_visits  = ed_cleaner.clean()
```

Each stream is cleaned and validated independently — separate
semantics, separate cleaner, separate report. The obs period is built
from the union of all entity IDs across both streams.

### Step 2 — Assemble the CohortTimeline

```python
ct = eventus.CohortTimeline.build_from_components(
    obs_period  = obs,
    events      = hospitalizations,
    occurrences = ed_visits,
)
```

```
CohortTimeline(
  entities             : 775
  has_obs_period       : True
  event_identities     : ['inpatient_hospitalization']
  occurrence_identities: ['ed_visit']
)
```

### Step 3 — Stacked timeline

Before computing any statistics, sample 50 members and visualize
both streams together.

```python
ct_sample = ct.sample_subset(n=50, random_seed=42)
eventus.StackedTimelinePlotter(ct_sample, timeline_config).plot(
    "output/stacked_timeline_ch08.png"
)
```

The stacked timeline shows red hospitalization bars and teal ED visit
dots on the same per-member calendar axis. Members with ED visits
clustered around hospitalization bars are immediately visible.

### Step 4 — Co-occurrence analysis

```python
analyzer = eventus.OccurrenceEventAnalyzer(ct, "ed_visit", "inpatient_hospitalization")
result   = analyzer.compute()
print(result)
```

```
OccurrenceEventResult:
  identity_occ           : ed_visit
  identity_event         : inpatient_hospitalization
  entity_col             : patient_id
  entities               : 775
  ────────────────────────────────────────────────
  n_with_both            : 509 (65.7%)
  n_occ_only             : 249 (32.1%)
  n_event_only           :  17 (2.2%)
  n_neither              :   0 (0.0%)
  ────────────────────────────────────────────────
  n_occ_total            : 2,379 (across all entities)
  n_occ_within           : 392
  ────────────────────────────────────────────────
  n_with_occ_to_event    : 436 (56.3%)
  median_occ_to_event    : 54.8 days
  n_with_event_to_occ    : 395 (51.0%)
  median_event_to_occ    : 60.0 days
```

### Step 5 — Plot gap distributions

```python
arrays = {
    "ED → next\nhospitalization": result.data["mean_days_occ_to_event"].dropna().values,
    "Discharge → next\nED visit":  result.data["mean_days_event_to_occ"].dropna().values,
}
eventus.ArraysViolinPlotter(arrays, violin_config).plot(
    "output/cooccurrence_gaps_violin.png"
)
```

---

## What the results show

**16.5% of ED visits happened during or on the day of a
hospitalization** (392 of 2,379). This reflects two real-world
phenomena: billing artifacts where an ED visit that became an
inpatient admission generates both an ED claim and an inpatient
claim on the same date, and ED-triggered admissions where the ED
visit date and admission date coincide. eventus surfaces this
automatically as `n_occ_within` — a signal that warrants clinical
review.

**Median 54.8 days from ED visit to next hospitalization.** Among
the 56.3% of members with at least one qualifying pair, the median
gap is 54.8 days. The distribution is right-skewed — some members
are hospitalized within days of an ED visit, others wait months.
This is the pre-admission pipeline: ED visits that eventually lead
to inpatient care.

**Median 60.0 days from discharge to next ED visit.** The
post-discharge gap is slightly longer than the pre-admission gap
in this cohort — reflecting that post-discharge ED visits were
generated for only 20% of admissions, while many event→occ pairs
come from elective admissions followed by unrelated ED visits.
In real data, high-risk patients often return to the ED within
days of discharge — this gap distribution is a readmission risk
signal.

These are not just statistics — they are hypotheses. With real data,
statistical tests can be applied directly to
`result.data["mean_days_occ_to_event"]` and
`result.data["mean_days_event_to_occ"]`.

---

## What this demonstrated

- **Two streams, one timeline** — events and occurrences are cleaned
  independently then assembled into a single validated `CohortTimeline`.
  The analyzer reads both streams without knowing how they were
  constructed.

- **The stacked timeline is the opening argument** — before any
  statistics, the visual shows the co-occurrence pattern. This is
  the Sistine Chapel of the vignette series: events, occurrences,
  and observation periods on the same per-member axis.

- **`OccurrenceEventAnalyzer` has no config** — there are no
  thresholds to declare, no windows to set. The computation is
  nearest-neighbor gaps within the observation period. The researcher
  interprets the distribution after seeing it — not before.

- **NaN is honest** — entities with no hospitalizations have NaN in
  all event-related gap statistics. Entities with only one qualifying
  pair have NaN for std. These are scientifically valid absences of
  signal, not missing data. The repr reports them explicitly.

- **The asymmetry is the finding** — 50 days vs 34 days. The
  post-discharge gap is shorter. A script computing this would require
  custom pairwise date logic across two pipe-delimited columns. eventus
  computes it in one method call.

---

> *Claude estimated a script-based equivalent of this analysis —
> cleaning two streams, building a shared obs period, computing
> nearest-neighbor gaps across pipe-delimited date columns, and
> producing a stacked timeline with two layers — would require on
> the order of 300 lines. The comparison argument was made in full
> across Chapters 1-6.*

---

*Chapter 9 — Survey of additional features: activity timing,
survival analysis, and combined event-occurrence visualizations.
See `vignette_09_survey.md`.*
