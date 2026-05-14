# eventus.analyzers

Analyzers compute quantities from validated data objects and intermediates
and produce typed result objects. They do not clean data, they do not
validate inputs beyond what is required to compute — that is the
responsibility of the cleaners and data objects upstream.

An analyzer either produces a result or raises. There are no partial
results, no silent failures, no silent NaN-filling of things that should
have been caught earlier.

---

## The analyzer family

```
CohortTimelineEventAnalyzer      — event coverage analytics
CohortTimelineOccurrenceAnalyzer — occurrence analytics
EventDurationAnalyzer            — event duration analytics
```

Each analyzer takes one or two validated inputs, computes quantities,
and produces one typed intermediate. The chain is always:

```
Validated input (CohortTimeline / Events)
    ↓
Analyzer
    ↓
Typed intermediate (result object or enriched CohortTimeline)
    ↓
Plotter / further analysis
```

---

## Two output patterns

Analyzers produce outputs in two forms depending on the use case.

**`compute_*` methods** return a typed intermediate — a self-contained
result object carrying the computed data, ready for visualization or
further analysis. The `CohortTimeline` is not modified.

```python
volume  = analyzer.compute_volume()   # → OccurrenceResultVolume
timing  = analyzer.compute_timing(3)  # → OccurrenceResultTiming
shape   = analyzer.compute_shape()    # → OccurrenceResultShape
```

**`enrich_with_*` methods** return a new `CohortTimeline` with
computed columns attached as `occ_comp_{identity}_{stat}` columns.
Use these when you want the computed stats baked into the central
table — for example, to sort entities in `StackedTimelinePlotter` by
a computed metric, or to pass enriched data to further analyses.

```python
ct = analyzer.enrich_with_volume()    # → CohortTimeline with occ_comp_{identity}_n
ct = analyzer.enrich_with_timing(3)   # → CohortTimeline with occ_comp_{identity}_time_to_*
ct = analyzer.enrich_with_shape()     # → CohortTimeline with occ_comp_{identity}_mean_gap, ...
```

The original `CohortTimeline` is never mutated. Both patterns produce
new objects.

---

## `CohortTimelineEventAnalyzer`

Computes event coverage analytics for one event identity within a
`CohortTimeline`.

```python
from eventus.analyzers import CohortTimelineEventAnalyzer

analyzer = CohortTimelineEventAnalyzer(cohort_timeline, identity="inpatient_hospitalization")
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `identity` is not in `cohort_timeline.event_identities`

### Methods

**`enrich_with_event_coverage()`** → `CohortTimeline`

Enriches with `evt_comp_{identity}_*` coverage columns. Always
overwrites existing columns. Returns a new `CohortTimeline`.

```python
ct = analyzer.enrich_with_event_coverage()
```

Coverage columns added:

| Column | Description |
|---|---|
| `evt_comp_{identity}_active_days` | Days covered by events within obs period |
| `evt_comp_{identity}_inactive_days` | Days not covered |
| `evt_comp_{identity}_inactive_days_before_first_event` | Gap before first event |
| `evt_comp_{identity}_inactive_days_after_last_event` | Gap after last event |
| `evt_comp_{identity}_inactive_days_middle` | Sum of gaps between events |
| `evt_comp_{identity}_first_start` | Date of first event start |
| `evt_comp_{identity}_last_end` | Date of last event end |

**`compute_activity_over_time(granularity, mode)`** → `EventActivityOverTime`

Per-timepoint activity statistics. Auto-enriches with coverage columns
internally if not already present — the caller does not need to call
`enrich_with_event_coverage()` first.

```python
activity = analyzer.compute_activity_over_time(
    granularity = "month",      # "day", "week", or "month"
    mode        = "normalized", # "normalized" or "calendar"
)
```

`normalized` — day 0 is each entity's own `obs_start`.
`calendar` — day 0 is the shared cohort `obs_start`. Raises if
`obs_start` is not uniform across entities.

**`get_summary(percentiles)`** → `EventCoverageSummary`

Tiered coverage summary. Auto-enriches internally if needed.

```python
summary = analyzer.get_summary(percentiles=[25, 50, 75])
print(summary)
```

The summary is organized into three tiers, each with its own
denominator:

| Tier | Denominator | Contents |
|---|---|---|
| Tier 1 | All entities | Coverage prevalence |
| Tier 2 | Entities with any coverage | Coverage patterns |
| Tier 3 | Entities with any coverage | Distributions |

### Full example

```python
from eventus.analyzers import CohortTimelineEventAnalyzer
from eventus.visualizers import ActivityOverTimePlotter
from eventus.visualizers.configs import ActivityOverTimeConfig

analyzer = CohortTimelineEventAnalyzer(ct, "inpatient_hospitalization")

# Enrich timeline for stacked plotter
ct_enriched = analyzer.enrich_with_event_coverage()

# Compute timeseries for activity plot
activity = analyzer.compute_activity_over_time(granularity="month", mode="calendar")
config   = ActivityOverTimeConfig.build_from_yaml("activity.yaml")
ActivityOverTimePlotter(activity, config).plot("activity.png")

# Print summary
print(analyzer.get_summary())
```

---

## `CohortTimelineOccurrenceAnalyzer`

Computes occurrence statistics for one occurrence identity within a
`CohortTimeline`.

```python
from eventus.analyzers import CohortTimelineOccurrenceAnalyzer

analyzer = CohortTimelineOccurrenceAnalyzer(cohort_timeline, identity="ed_visit")
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `identity` is not in `cohort_timeline.occurrence_identities`

### `compute_*` methods — typed result objects

**`compute_volume()`** → `OccurrenceResultVolume`

Per-entity occurrence counts within the observation period. Zero is valid.

```python
volume = analyzer.compute_volume()
print(volume)
# → OccurrenceResultVolume with n_with_any, n_with_multiple
```

**`compute_timing(max_n)`** → `OccurrenceResultTiming`

Per-entity timing of the nth occurrence relative to `obs_start`, up to
`max_n`. NaN where the entity has fewer than nth occurrences.

```python
timing = analyzer.compute_timing(max_n=3)
# → OccurrenceResultTiming with time_to_1, time_to_2, time_to_3, recency_days
```

**`compute_shape()`** → `OccurrenceResultShape`

Per-entity behavioral fingerprint — gap statistics, burstiness, memory,
density, center of mass. NaN where the minimum occurrence threshold is
not met.

```python
shape = analyzer.compute_shape()
# → OccurrenceResultShape with mean_gap, burstiness, memory, density, ...
```

Minimum occurrence thresholds:

| Stat | Minimum n |
|---|---|
| `mean_gap`, `min_gap`, `max_gap` | 2 |
| `std_gap`, `cv_gap`, `burstiness` | 3 |
| `memory` | 4 |
| `density`, `center_of_mass` | 1, obs_duration > 0 |

**`compute_survival(ci_method)`** → `SurvivalResult`

Kaplan-Meier survival curve for time to first occurrence. Entities with
no occurrence are right-censored at their `obs_duration_days`. Excluding
them would silently bias the curve.

```python
survival = analyzer.compute_survival(ci_method="greenwood")
print(f"Median survival: {survival.median_survival} days")
print(f"Event rate: {survival.event_rate_pct}%")
```

### `enrich_with_*` methods — enriched CohortTimeline

**`enrich_with_volume()`** → `CohortTimeline`

Adds `occ_comp_{identity}_n` column.

**`enrich_with_timing(max_n)`** → `CohortTimeline`

Adds `occ_comp_{identity}_time_to_1` ... `occ_comp_{identity}_time_to_{max_n}`
and `occ_comp_{identity}_recency_days`.

**`enrich_with_shape()`** → `CohortTimeline`

Adds `occ_comp_{identity}_mean_gap`, `std_gap`, `cv_gap`, `min_gap`,
`max_gap`, `burstiness`, `memory`, `density`, `center_of_mass`.

### Full example

```python
from eventus.analyzers import CohortTimelineOccurrenceAnalyzer
from eventus.visualizers.occurrences import (
    OccurrenceResultVolumePlotter,
    OccurrenceResultTimingPlotter,
    OccurrenceResultShapePlotter,
)
from eventus.visualizers.configs import (
    OccurrenceResultVolumeConfig,
    OccurrenceResultTimingConfig,
    OccurrenceResultShapeConfig,
)

analyzer = CohortTimelineOccurrenceAnalyzer(ct, "ed_visit")

# Volume
volume = analyzer.compute_volume()
OccurrenceResultVolumePlotter(
    volume,
    OccurrenceResultVolumeConfig.build_from_yaml("volume.yaml"),
).plot_prevalence_bar("prevalence.png")

# Timing
timing = analyzer.compute_timing(max_n=3)
OccurrenceResultTimingPlotter(
    timing,
    OccurrenceResultTimingConfig.build_from_yaml("timing.yaml"),
).plot_histogram("timing.png")

# Shape
shape = analyzer.compute_shape()
OccurrenceResultShapePlotter(
    shape,
    OccurrenceResultShapeConfig.build_from_yaml("shape.yaml"),
).plot_fingerprint("fingerprint.png")

# Survival
survival = analyzer.compute_survival()
print(survival)

# Enrich timeline for stacked plotter
ct = analyzer.enrich_with_volume()
ct = CohortTimelineOccurrenceAnalyzer(ct, "ed_visit").enrich_with_timing(3)
```

---

## `EventDurationAnalyzer`

Computes event durations from a validated `Events` object. Works
directly on `Events` — does not require a `CohortTimeline`.

```python
from eventus.analyzers import EventDurationAnalyzer

analyzer = EventDurationAnalyzer(events)
result   = analyzer.calc()   # → EventDurationResult
```

### `descriptor_cols`

Optional columns from `Events.data` to carry through to the result.
These become available for stratification at the visualizer level.
Nulls in descriptor columns are allowed — they are per-event attributes
that may not be present for every row.

```python
# Lean — duration_days only
analyzer = EventDurationAnalyzer(events)

# Explicit descriptor columns
analyzer = EventDurationAnalyzer(
    events,
    descriptor_cols = ["hospital_id", "bmi_at_admission"],
)

# Carry everything
analyzer = EventDurationAnalyzer(events, descriptor_cols="all")
```

### `calc()` → `EventDurationResult`

Returns an `EventDurationResult` — one row per event with `duration_days`
and any descriptor columns. Zero-duration events (same-day start and
end) are valid and are not filtered.

```python
result = analyzer.calc()
print(result)
# → EventDurationResult with n_events, n_entities, mean/median duration

# Build arrays for violin plotting
arrays = result.build_arrays()
# → {"all_data": np.ndarray}

# Build arrays stratified by hospital
arrays = result.build_arrays(stratify_by="hospital_id")
# → {"all_data": np.ndarray, "Hospital_A": np.ndarray, "Hospital_B": np.ndarray}
```

### Full example

```python
from eventus.analyzers import EventDurationAnalyzer
from eventus.visualizers import EventDurationHistogramPlotter
from eventus.visualizers.violins import EventDurationViolinPlotter
from eventus.visualizers.configs import EventDurationPlotConfig, ArraysViolinConfig

# With descriptors for stratification
result = EventDurationAnalyzer(
    events,
    descriptor_cols = ["hospital_id"],
).calc()

# Histogram and KDE
hist_config = EventDurationPlotConfig.build_from_yaml("duration.yaml")
plotter     = EventDurationHistogramPlotter(result, hist_config)
plotter.plot_histogram("duration_histogram.png")
plotter.plot_kde("duration_kde.png")

# Violin stratified by hospital
violin_config = ArraysViolinConfig.build_from_yaml("duration_violin.yaml")
EventDurationViolinPlotter(
    result, violin_config, stratify_by="hospital_id"
).plot("durations_by_hospital.png")
```

---

## Internal utils

The `_utils.py` files contain the computational workhorse code. They
are internal and not part of the public API.

| File | Contains |
|---|---|
| `cohort_timeline_event_analyzer_utils.py` | Coverage computation, activity timeseries, summary tiers |
| `cohort_timeline_occurrence_analyzer_utils.py` | Guards, per-entity stat helpers, cohort summary |
| `occurrence_primitives_utils.py` | `parse_dates()`, `compute_gaps()` — shared across all occurrence computation |
| `occurrence_stats_utils.py` | `compute_volume_stats()`, `compute_timing_stats()`, `compute_shape_stats()` |
| `events_duration_utils.py` | `compute_durations()` |

`occurrence_primitives_utils.py` deserves special mention. `parse_dates()`
parses pipe-delimited occurrence date strings into sorted lists of
timestamps filtered to the observation window. `compute_gaps()` computes
consecutive inter-occurrence gap lengths. Every occurrence stat —
volume, timing, shape — builds on these two primitives.

---

## Design notes

**Analyzers do not clean.** A data object that exists is already
structurally sound. The analyzer trusts it and computes. Cleaning is
the responsibility of the cleaners and filters upstream.

**Analyzers do not mutate.** Every method returns a new object. The
input `CohortTimeline` or `Events` is never changed.

**`compute_*` vs `enrich_with_*`** is a deliberate design choice, not
a duplication. `compute_*` is for analysis and visualization —
the result travels to a plotter. `enrich_with_*` is for pipeline
composition — the result bakes into the `CohortTimeline` for further
enrichment or display in the stacked timeline.

**Lazy enrichment in `CohortTimelineEventAnalyzer`.** `compute_activity_over_time()`
and `get_summary()` call `_ensure_coverage()` internally. If coverage
columns are not yet present they are computed on the fly. This means
the caller does not need to manually call `enrich_with_event_coverage()`
before calling these methods — the analyzer handles it. Calling
`enrich_with_event_coverage()` explicitly is still useful when you want
the enriched `CohortTimeline` for downstream use.

**`EventDurationAnalyzer` works on `Events`, not `CohortTimeline`.**
Duration is a property of an event, not of an entity's observation
period. It does not require an obs period to be meaningful. This is
why it operates at the `Events` level rather than the `CohortTimeline`
level.
