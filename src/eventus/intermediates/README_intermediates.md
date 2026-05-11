# eventus.intermediates

Validated result objects produced by analyzers and consumed by visualizers.

Intermediates are the contract between the analytical and visualization layers of eventus. They are not passive containers — unlike data objects, which only validate and hold input data, intermediates carry computed results and expose methods that allow further enrichment and interrogation. An intermediate either exists and is complete, or it does not exist at all.

---

## What intermediates are

Every analyzer in eventus produces an intermediate. The intermediate holds the result of the computation in a typed, validated form — not a raw DataFrame, but an object that knows what it contains and enforces that knowledge at construction time.

This design serves two purposes. First, it makes the pipeline auditable: if an intermediate was constructed, its data is structurally sound. Second, it decouples visualizers from analyzers — a visualizer accepts an intermediate type, not a specific analyzer, so any analyzer that produces the right intermediate can feed any visualizer that consumes it.

---

## The intermediate family

```
CohortTimeline                          — the central per-entity table

EventActivityOverTime                   — event activity timeseries
EventCoverageSummary                    — structured coverage summary

OccurrenceResult (base)
    OccurrenceResultVolume              — per-entity occurrence counts
    OccurrenceResultTiming              — nth-occurrence timing
    OccurrenceResultShape               — behavioral fingerprint

SurvivalResult                          — Kaplan-Meier survival curve
```

---

## CohortTimeline

`CohortTimeline` is the central object in eventus. It is a per-entity table — one row per entity — that assembles observation periods, events, and occurrences into a single structured object. Multi-value columns (multiple events or occurrences per entity) are stored as pipe-delimited strings.

`CohortTimeline` is both a result object and an enrichment hub. Once assembled, it can be progressively enriched with computed analytical layers by calling enrichment methods that return new `CohortTimeline` instances.

### Construction

```python
from eventus.intermediates import CohortTimeline

timeline = CohortTimeline.build_from_components(
    obs_period  = obs,          # ObsPeriodPerEntity
    events      = hospitalizations,   # Events or list[Events]
    occurrences = ed_visits,    # Occurrences or list[Occurrences]
)
```

All arguments are optional but at least one must be provided. Entity alignment is enforced at construction — every entity in the spine must be uniquely identified.

### Structural invariants

- One row per entity — `entity_col` must be unique and non-null
- At most one observation period layer (`obs_start`, `obs_end`, `obs_duration_days`)
- Zero or more event layers, each with a unique identity (`evt_{identity}_starts`, `evt_{identity}_ends`)
- Zero or more occurrence layers, each with a unique identity (`occ_{identity}`)
- Zero or more computed layers (`occ_comp_{identity}_{stat}`)
- At least one layer must be present

### Column taxonomy

| Column pattern | Contents |
|---|---|
| `{entity_col}` | Entity spine |
| `obs_start`, `obs_end`, `obs_duration_days` | Observation period |
| `evt_{identity}_starts` | Pipe-delimited event start dates |
| `evt_{identity}_ends` | Pipe-delimited event end dates |
| `occ_{identity}` | Pipe-delimited occurrence dates |
| `occ_comp_{identity}_{stat}` | Computed occurrence statistics |

### Enrichment

Enrichment methods return a new `CohortTimeline` — the original is never mutated.

```python
# Enrich with event coverage analysis
timeline = timeline.enrich_with_event_analysis("inpatient_hospitalization")

# Enrich with occurrence volume (count per entity)
timeline = timeline.enrich_with_occurrence_volume_analysis("ed_visit")

# Enrich with occurrence timing (time to nth occurrence)
timeline = timeline.enrich_with_occurrence_timing_analysis("ed_visit", max_n=3)

# Enrich with occurrence shape (burstiness, memory, density, etc.)
timeline = timeline.enrich_with_occurrence_shape_analysis("ed_visit")
```

Each enrichment call adds `occ_comp_{identity}_{stat}` columns for the relevant statistics. Existing columns are always overwritten — enrichment is idempotent.

### Sampling

```python
# Reproducible random subset of 500 entities
subset = timeline.sample_subset(n=500, random_seed=42)
```

### Properties

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | Copy of the underlying table |
| `entity_col` | `str` | Name of the entity identifier column |
| `has_obs_period` | `bool` | Whether an observation period layer is present |
| `event_identities` | `list[str]` | Identities of all event layers |
| `occurrence_identities` | `list[str]` | Identities of all raw occurrence layers |
| `computed_occurrence_identities` | `list[str]` | Identities of all computed occurrence layers |

---

## OccurrenceResult family

`OccurrenceResult` is an abstract base class. It is never instantiated directly. The three concrete subclasses represent three analytical lenses on occurrence data — volume, timing, and shape — each produced by a dedicated method on `CohortTimelineOccurrenceAnalyzer`.

All three share these structural invariants:
- `entity_col` is present, non-null, and unique
- `obs_start` and `obs_end` columns are present
- `identity` is a non-empty string
- `data` is non-empty

### OccurrenceResultVolume

Per-entity occurrence counts for one identity. Produced by `CohortTimelineOccurrenceAnalyzer.compute_volume()`.

```python
volume = analyzer.compute_volume()

volume.n_with_any       # entities with at least one occurrence
volume.n_with_multiple  # entities with more than one occurrence
```

**Additional column:** `n` — count of occurrences within the observation period. Zero is valid.

### OccurrenceResultTiming

Per-entity nth-occurrence timing for one identity. Produced by `CohortTimelineOccurrenceAnalyzer.compute_timing(max_n)`.

```python
timing = analyzer.compute_timing(max_n=3)

timing.max_n                # maximum nth occurrence computed
timing.n_with_timing(nth=1) # entities with a valid time_to_1
timing.n_with_timing(nth=2) # entities with a valid time_to_2
```

**Additional columns:** `time_to_1` ... `time_to_{max_n}` — days from `obs_start` to the nth occurrence. `NaN` where the entity has fewer than n occurrences. `recency_days` — days from last occurrence to `obs_end`. `NaN` for entities with zero occurrences.

### OccurrenceResultShape

Per-entity behavioral fingerprint for one identity. Produced by `CohortTimelineOccurrenceAnalyzer.compute_shape()`.

```python
shape = analyzer.compute_shape()

shape.n_with_gaps    # entities with >= 2 occurrences (gap stats defined)
shape.n_with_shape   # entities with >= 3 occurrences (burstiness defined)
shape.n_with_memory  # entities with >= 4 occurrences (memory defined)
```

**Additional columns:**

| Column | Minimum occurrences required |
|---|---|
| `mean_gap`, `min_gap`, `max_gap` | 2 |
| `std_gap`, `cv_gap`, `burstiness` | 3 |
| `memory` | 4 |
| `density`, `center_of_mass` | 1, obs_duration > 0 |

All stats are `NaN` where the minimum threshold is not met. This is by design — the entity simply did not have enough data.

---

## SurvivalResult

A validated Kaplan-Meier survival curve. `SurvivalResult` is standalone and reusable — it carries everything needed to plot and interpret a survival curve without any reference back to the object that produced it. It is not tied to occurrence analysis specifically; any analysis that produces a KM-style curve produces a `SurvivalResult`.

Current producer: `CohortTimelineOccurrenceAnalyzer.compute_survival()`

### Structural invariants

- Survival values are in `[0, 1]`
- `ci_lower <= survival <= ci_upper` at every timepoint
- `n_at_risk` is monotonically non-increasing
- `n_events_total + n_censored_total == n_total`
- Empty data is valid only when `n_events_total == 0`

### Construction

`SurvivalResult` is produced by analyzers, not constructed directly. Its properties are read-only.

### Properties

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per unique event timepoint |
| `label` | `str` | Human-readable label for the curve |
| `n_total` | `int` | Total cohort size |
| `n_events_total` | `int` | Entities who experienced the event |
| `n_censored_total` | `int` | Entities censored |
| `event_rate_pct` | `float` | Percentage of cohort that experienced the event |
| `median_survival` | `float | None` | Smallest day where S(t) <= 0.5. `None` if never crossed |
| `max_day` | `int | None` | Last timepoint in the survival table |
| `ci_method` | `str` | Confidence interval method (`'greenwood'`) |

### Data columns

| Column | Type | Description |
|---|---|---|
| `day` | `int` | Timepoint in days from obs_start |
| `n_at_risk` | `int` | Entities still under observation |
| `n_events` | `int` | Events occurring at this timepoint |
| `n_censored` | `int` | Entities censored at this timepoint |
| `survival` | `float` | KM estimate S(t) |
| `ci_lower` | `float` | Lower 95% confidence bound |
| `ci_upper` | `float` | Upper 95% confidence bound |

---

## EventActivityOverTime

Timeseries result from `CohortTimelineEventAnalyzer.compute_activity_over_time()`. Carries the activity DataFrame, the x-axis mode, and — when `mode='calendar'` — the cohort start date needed to reconstruct calendar dates from day offsets.

### Modes

| Mode | Description |
|---|---|
| `'normalized'` | Day 0 is each entity's own `obs_start` |
| `'calendar'` | Day 0 is a shared `cohort_start` across all entities |

`cohort_start` is required when `mode='calendar'` and must be `None` when `mode='normalized'`.

### Properties

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per timepoint bucket |
| `mode` | `str` | `'normalized'` or `'calendar'` |
| `cohort_start` | `pd.Timestamp | None` | Shared start date when `mode='calendar'` |
| `max_days` | `int` | Maximum day value in the timeseries |
| `n_entities` | `int` | Total cohort size |

### Data columns

| Column | Type | Description |
|---|---|---|
| `day` | `int` | Timepoint bucket |
| `n_total` | `int` | Total entities in cohort |
| `n_active` | `int` | Entities with active event coverage at this day |
| `pct_active` | `float` | Percentage of cohort with active coverage |
| `n_entered` | `int | NA` | Entities whose coverage began at this day |
| `n_exited` | `int | NA` | Entities whose coverage ended at this day |

---

## EventCoverageSummary

Structured summary of event coverage analysis for one identity. Produced by `CohortTimelineEventAnalyzer.get_summary()`.

Organized into three tiers:

| Tier | Denominator | Contents |
|---|---|---|
| Tier 1 | All entities | Coverage prevalence — how many had any coverage |
| Tier 2 | Entities with any coverage | Coverage patterns — gaps, continuity, fragmentation |
| Tier 3 | Entities with any coverage | Distributions — duration, gap length, event counts |

### Properties

| Property | Type | Description |
|---|---|---|
| `identity` | `str` | Event identity |
| `n_total` | `int` | Total entities in the cohort |
| `n_with_any_coverage` | `int` | Entities with at least one event in the observation period |

---

## Design notes

**Intermediates and data objects.** *(*** revisit once data_objects README is written — the distinction between the two layers needs to be stated accurately here.)* Intermediates hold computed results and can enrich themselves, expose analytical properties, and produce derived results. A `CohortTimeline` is not just a DataFrame with a schema — it is an analytical object that knows what it contains and what can be done with it.

**Immutability by convention.** Enrichment methods on `CohortTimeline` always return new instances. The original is never mutated. This makes pipelines explicit and reproducible — each enrichment step is a discrete, auditable operation.

**Standalone result objects.** `SurvivalResult` and `EventActivityOverTime` carry everything needed for interpretation and visualization without any reference back to the object that produced them. This makes them safe to pass to visualizers, serialize, or hand off to downstream analyses.

**Specific errors, not silent failures.** Every constructor raises on invalid data with a message that identifies what went wrong and what to fix. A constructed intermediate is always structurally sound.
