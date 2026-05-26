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
CohortTimelineEpisodeAnalyzer      — episode coverage analytics
CohortTimelineEventAnalyzer        — event analytics
EpisodeDurationAnalyzer            — episode duration analytics
EventEpisodeAnalyzer               — event-episode temporal relationships
```

Each analyzer takes one or two validated inputs, computes quantities,
and produces one typed intermediate. The chain is always:

```
Validated input (CohortTimeline / Episodes)
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
volume  = analyzer.compute_volume()   # → EventResultVolume
timing  = analyzer.compute_timing(3)  # → EventResultTiming
shape   = analyzer.compute_shape()    # → EventResultShape
```

**`enrich_with_*` methods** return a new `CohortTimeline` with
computed columns attached as `evt_comp_{identity}_{stat}` columns.
Use these when you want the computed stats baked into the central
table — for example, to sort entities in `StackedTimelinePlotter` by
a computed metric, or to pass enriched data to further analyses.

```python
ct = analyzer.enrich_with_volume()    # → CohortTimeline with evt_comp_{identity}_n
ct = analyzer.enrich_with_timing(3)   # → CohortTimeline with evt_comp_{identity}_time_to_*
ct = analyzer.enrich_with_shape()     # → CohortTimeline with evt_comp_{identity}_mean_gap, ...
```

The original `CohortTimeline` is never mutated. Both patterns produce
new objects.

---

## `CohortTimelineEpisodeAnalyzer`

Computes episode coverage analytics for one episode identity within a
`CohortTimeline`.

```python
from eventus.analyzers import CohortTimelineEpisodeAnalyzer

analyzer = CohortTimelineEpisodeAnalyzer(cohort_timeline, identity="inpatient_hospitalization")
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `identity` is not in `cohort_timeline.episode_identities`

### Methods

**`enrich_with_episode_coverage()`** → `CohortTimeline`

Enriches with `eps_comp_{identity}_*` coverage columns. Always
overwrites existing columns. Returns a new `CohortTimeline`.

```python
ct = analyzer.enrich_with_episode_coverage()
```

Coverage columns added:

| Column | Description |
|---|---|
| `eps_comp_{identity}_active_days` | Days covered by episodes within obs period |
| `eps_comp_{identity}_inactive_days` | Days not covered |
| `eps_comp_{identity}_inactive_days_before_first_episode` | Gap before first episode |
| `eps_comp_{identity}_inactive_days_after_last_episode` | Gap after last episode |
| `eps_comp_{identity}_inactive_days_middle` | Sum of gaps between episodes |
| `eps_comp_{identity}_first_start` | Date of first episode start |
| `eps_comp_{identity}_last_end` | Date of last episode end |

**`compute_activity_over_time(granularity, mode)`** → `EpisodeActivityOverTime`

Per-timepoint activity statistics. Auto-enriches with coverage columns
internally if not already present — the caller does not need to call
`enrich_with_episode_coverage()` first.

```python
activity = analyzer.compute_activity_over_time(
    granularity = "month",      # "day", "week", or "month"
    mode        = "normalized", # "normalized" or "calendar"
)
```

`normalized` — day 0 is each entity's own `obs_start`.
`calendar` — day 0 is the shared cohort `obs_start`. Raises if
`obs_start` is not uniform across entities.

**`get_summary(percentiles)`** → `EpisodeCoverageSummary`

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
from eventus.analyzers import CohortTimelineEpisodeAnalyzer
from eventus.visualizers import ActivityOverTimePlotter
from eventus.visualizers.configs import ActivityOverTimeConfig

analyzer = CohortTimelineEpisodeAnalyzer(ct, "inpatient_hospitalization")

# Enrich timeline for stacked plotter
ct_enriched = analyzer.enrich_with_episode_coverage()

# Compute timeseries for activity plot
activity = analyzer.compute_activity_over_time(granularity="month", mode="calendar")
config   = ActivityOverTimeConfig.build_from_yaml("activity.yaml")
ActivityOverTimePlotter(activity, config).plot("activity.png")

# Print summary
print(analyzer.get_summary())
```

---

## `CohortTimelineEventAnalyzer`

Computes event statistics for one event identity within a
`CohortTimeline`.

```python
from eventus.analyzers import CohortTimelineEventAnalyzer

analyzer = CohortTimelineEventAnalyzer(cohort_timeline, identity="ed_visit")
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `identity` is not in `cohort_timeline.event_identities`

### `compute_*` methods — typed result objects

**`compute_volume()`** → `EventResultVolume`

Per-entity event counts within the observation period. Zero is valid.

```python
volume = analyzer.compute_volume()
print(volume)
# → EventResultVolume with n_with_any, n_with_multiple
```

**`compute_timing(max_n)`** → `EventResultTiming`

Per-entity timing of the nth event relative to `obs_start`, up to
`max_n`. NaN where the entity has fewer than nth events.

```python
timing = analyzer.compute_timing(max_n=3)
# → EventResultTiming with time_to_1, time_to_2, time_to_3, recency_days
```

**`compute_shape()`** → `EventResultShape`

Per-entity behavioral fingerprint — gap statistics, burstiness, memory,
density, center of mass. NaN where the minimum event threshold is
not met.

```python
shape = analyzer.compute_shape()
# → EventResultShape with mean_gap, burstiness, memory, density, ...
```

Minimum event thresholds:

| Stat | Minimum n |
|---|---|
| `mean_gap`, `min_gap`, `max_gap` | 2 |
| `std_gap`, `cv_gap`, `burstiness` | 3 |
| `memory` | 4 |
| `density`, `center_of_mass` | 1, obs_duration > 0 |

**`compute_survival(ci_method)`** → `SurvivalResult`

Kaplan-Meier survival curve for time to first event. Entities with
no event are right-censored at their `obs_duration_days`. Excluding
them would silently bias the curve.

```python
survival = analyzer.compute_survival(ci_method="greenwood")
print(f"Median survival: {survival.median_survival} days")
print(f"Episode rate: {survival.episode_rate_pct}%")
```

### `enrich_with_*` methods — enriched CohortTimeline

**`enrich_with_volume()`** → `CohortTimeline`

Adds `evt_comp_{identity}_n` column.

**`enrich_with_timing(max_n)`** → `CohortTimeline`

Adds `evt_comp_{identity}_time_to_1` ... `evt_comp_{identity}_time_to_{max_n}`
and `evt_comp_{identity}_recency_days`.

**`enrich_with_shape()`** → `CohortTimeline`

Adds `evt_comp_{identity}_mean_gap`, `std_gap`, `cv_gap`, `min_gap`,
`max_gap`, `burstiness`, `memory`, `density`, `center_of_mass`.

### Full example

```python
from eventus.analyzers import CohortTimelineEventAnalyzer
from eventus.visualizers.events import (
    EventResultVolumePlotter,
    EventResultTimingPlotter,
    EventResultShapePlotter,
)
from eventus.visualizers.configs import (
    EventResultVolumeConfig,
    EventResultTimingConfig,
    EventResultShapeConfig,
)

analyzer = CohortTimelineEventAnalyzer(ct, "ed_visit")

# Volume
volume = analyzer.compute_volume()
EventResultVolumePlotter(
    volume,
    EventResultVolumeConfig.build_from_yaml("volume.yaml"),
).plot_prevalence_bar("prevalence.png")

# Timing
timing = analyzer.compute_timing(max_n=3)
EventResultTimingPlotter(
    timing,
    EventResultTimingConfig.build_from_yaml("timing.yaml"),
).plot_histogram("timing.png")

# Shape
shape = analyzer.compute_shape()
EventResultShapePlotter(
    shape,
    EventResultShapeConfig.build_from_yaml("shape.yaml"),
).plot_fingerprint("fingerprint.png")

# Survival
survival = analyzer.compute_survival()
print(survival)

# Enrich timeline for stacked plotter
ct = analyzer.enrich_with_volume()
ct = CohortTimelineEventAnalyzer(ct, "ed_visit").enrich_with_timing(3)
```

---

## `EpisodeDurationAnalyzer`

Computes episode durations from a validated `Episodes` object. Works
directly on `Episodes` — does not require a `CohortTimeline`.

```python
from eventus.analyzers import EpisodeDurationAnalyzer

analyzer = EpisodeDurationAnalyzer(episodes)
result   = analyzer.calc()   # → EpisodeDurationResult
```

### `descriptor_cols`

Optional columns from `Episodes.data` to carry through to the result.
These become available for stratification at the visualizer level.
Nulls in descriptor columns are allowed — they are per-episode attributes
that may not be present for every row.

```python
# Lean — duration_days only
analyzer = EpisodeDurationAnalyzer(episodes)

# Explicit descriptor columns
analyzer = EpisodeDurationAnalyzer(
    episodes,
    descriptor_cols = ["hospital_id", "bmi_at_admission"],
)

# Carry everything
analyzer = EpisodeDurationAnalyzer(episodes, descriptor_cols="all")
```

### `calc()` → `EpisodeDurationResult`

Returns an `EpisodeDurationResult` — one row per episode with `duration_days`
and any descriptor columns. Zero-duration episodes (same-day start and
end) are valid and are not filtered.

```python
result = analyzer.calc()
print(result)
# → EpisodeDurationResult with n_episodes, n_entities, mean/median duration

# Build arrays for violin plotting
arrays = result.build_arrays()
# → {"all_data": np.ndarray}

# Build arrays stratified by hospital
arrays = result.build_arrays(stratify_by="hospital_id")
# → {"all_data": np.ndarray, "Hospital_A": np.ndarray, "Hospital_B": np.ndarray}
```

### Full example

```python
from eventus.analyzers import EpisodeDurationAnalyzer
from eventus.visualizers import EpisodeDurationHistogramPlotter
from eventus.visualizers.violins import EpisodeDurationViolinPlotter
from eventus.visualizers.configs import EpisodeDurationPlotConfig, ArraysViolinConfig

# With descriptors for stratification
result = EpisodeDurationAnalyzer(
    episodes,
    descriptor_cols = ["hospital_id"],
).calc()

# Histogram and KDE
hist_config = EpisodeDurationPlotConfig.build_from_yaml("duration.yaml")
plotter     = EpisodeDurationHistogramPlotter(result, hist_config)
plotter.plot_histogram("duration_histogram.png")
plotter.plot_kde("duration_kde.png")

# Violin stratified by hospital
violin_config = ArraysViolinConfig.build_from_yaml("duration_violin.yaml")
EpisodeDurationViolinPlotter(
    result, violin_config, stratify_by="hospital_id"
).plot("durations_by_hospital.png")
```

---

## `EventEpisodeAnalyzer`

Computes per-entity temporal relationship statistics between one event
identity and one episode identity within a `CohortTimeline`. Works on
both streams simultaneously — no configuration required. There are no
thresholds or windows to declare; the computation is nearest-neighbor
gaps within the observation period.

```python
from eventus.analyzers import EventEpisodeAnalyzer

analyzer = EventEpisodeAnalyzer(
    cohort_timeline  = ct,
    event_identity   = "ed_visit",
    episode_identity = "inpatient_hospitalization",
)
```

**Raises at construction if:**
- `cohort_timeline` has no observation period
- `event_identity` is not in `cohort_timeline.event_identities`
- `episode_identity` is not in `cohort_timeline.episode_identities`

### `compute()` → `EventEpisodeResult`

Returns an `EventEpisodeResult` — one row per entity with within counts
and nearest-neighbor gap statistics in both directions.

```python
result = analyzer.compute()
print(result)
```

**Statistics computed per entity:**

| Column | Description |
|---|---|
| `n_evt_total` | Total events within obs period |
| `n_episodes_total` | Total episodes within obs period |
| `n_evt_within` | Events that fell inside any episode interval |
| `pct_evt_within` | `n_evt_within / n_evt_total`. NaN if no events |
| `mean_days_evt_to_episode` | Mean gap: event → nearest episode start after it |
| `median_days_evt_to_episode` | Median gap: event → nearest episode start after it |
| `std_days_evt_to_episode` | Std gap (NaN if < 2 qualifying pairs) |
| `mean_days_episode_to_occ` | Mean gap: episode discharge → nearest event after it |
| `median_days_episode_to_occ` | Median gap: episode discharge → nearest event after it |
| `std_days_episode_to_occ` | Std gap (NaN if < 2 qualifying pairs) |

**NaN semantics**

NaN in gap statistics is scientifically meaningful — absent signal, not
missing data. NaN may mean: entity had no events, entity had no episodes,
entity had both but no qualifying temporal pairs in the observation period,
or entity had only one qualifying pair (std only). All are valid outcomes.

### Full example

```python
from eventus.analyzers import EventEpisodeAnalyzer
from eventus.visualizers.violins import ArraysViolinPlotter
from eventus.visualizers.configs import ArraysViolinConfig

analyzer = EventEpisodeAnalyzer(ct, "ed_visit", "inpatient_hospitalization")
result   = analyzer.compute()

print(result)
# EventEpisodeResult:
#   identity_occ     : ed_visit
#   identity_episode : inpatient_hospitalization
#   entities         : 800
#   n_with_both      : 436 (54.5%)
#   ...

# Visualize gap distributions as violin plots
config  = ArraysViolinConfig.build_from_yaml("coevent_violin.yaml")
arrays  = {
    "evt → episode": result.data["median_days_evt_to_episode"].dropna().values,
    "episode → evt": result.data["median_days_episode_to_occ"].dropna().values,
}
ArraysViolinPlotter(arrays, config).plot("coevent_gaps.png")
```

---

## Internal utils

The `_utils.py` files contain the computational workhorse code. They
are internal and not part of the public API.

| File | Contains |
|---|---|
| `cohort_timeline_episode_analyzer_utils.py` | Coverage computation, activity timeseries, summary tiers |
| `event_primitives_utils.py` | `parse_dates()`, `compute_gaps()` — shared across all event computation |
| `event_stats_utils.py` | `compute_volume_stats()`, `compute_timing_stats()`, `compute_shape_stats()` |
| `event_episode_analyzer_utils.py` | Per-entity event-episode gap computation, within proportion |
| `episodes_duration_utils.py` | `compute_durations()` |

`event_primitives_utils.py` deserves special mention. `parse_dates()`
parses pipe-delimited event date strings into sorted lists of
timestamps filtered to the observation window. `compute_gaps()` computes
consecutive inter-event gap lengths. Every event stat —
volume, timing, shape — builds on these two primitives.

---

## Design notes

**Analyzers do not clean.** A data object that exists is already
structurally sound. The analyzer trusts it and computes. Cleaning is
the responsibility of the cleaners and filters upstream.

**Analyzers do not mutate.** Every method returns a new object. The
input `CohortTimeline` or `Episodes` is never changed.

**`compute_*` vs `enrich_with_*`** is a deliberate design choice, not
a duplication. `compute_*` is for analysis and visualization —
the result travels to a plotter. `enrich_with_*` is for pipeline
composition — the result bakes into the `CohortTimeline` for further
enrichment or display in the stacked timeline.

**Lazy enrichment in `CohortTimelineEpisodeAnalyzer`.** `compute_activity_over_time()`
and `get_summary()` call `_ensure_coverage()` internally. If coverage
columns are not yet present they are computed on the fly. This means
the caller does not need to manually call `enrich_with_episode_coverage()`
before calling these methods — the analyzer handles it. Calling
`enrich_with_episode_coverage()` explicitly is still useful when you want
the enriched `CohortTimeline` for downstream use.

**`EpisodeDurationAnalyzer` works on `Episodes`, not `CohortTimeline`.**
Duration is a property of an episode, not of an entity's observation
period. It does not require an obs period to be meaningful. This is
why it operates at the `Episodes` level rather than the `CohortTimeline`
level.
