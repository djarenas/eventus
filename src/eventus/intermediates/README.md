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

EpisodeActivityOverTime                 — episode activity timeseries
EpisodeCoverageSummary                  — structured coverage summary
EpisodeDurationResult                   — per-episode duration data

EventResult (base)
    EventResultVolume              — per-entity event counts
    EventResultTiming              — nth-event timing
    EventResultShape               — behavioral fingerprint

EpisodeEventInteractionResult           — events classified by position vs. episodes

EventCoOccurrenceResult (base)          — co-occurrence between two event identities
    EventCoOccurrencePresenceResult     — binary presence, Fisher's exact
    EventCoOccurrenceAssociation        — 2×2 table, prevalence ratio, CIs
    EventCoOccurrenceGapSummary         — per-entity absolute gap statistics
    EventCoOccurrenceGapTest            — KS test, permutation null, gap ratio
    EventCoOccurrenceDirectionalitySummary — per-entity mean signed gaps
    EventCoOccurrenceDirectionalityTest — Wilcoxon, permutation null, direction ratio

See event_cooccurrence/README.md for full documentation of all co-occurrence objects.
```

---

## CohortTimeline

`CohortTimeline` is the central object in eventus. It is a per-entity table — one row per entity — that assembles observation periods, episodes, and events into a single structured object. Multi-value columns (multiple episodes or events per entity) are stored as pipe-delimited strings.

`CohortTimeline` is both a result object and an enrichment hub. Once assembled, it can be progressively enriched with computed analytical layers by calling enrichment methods that return new `CohortTimeline` instances.

### Construction

```python
from eventus.intermediates import CohortTimeline

timeline = CohortTimeline.build_from_components(
    obs_period  = obs,          # ObsPeriodPerEntity
    episodes      = hospitalizations,   # Episodes or list[Episodes]
    events = ed_visits,    # Events or list[Events]
)
```

All arguments are optional but at least one must be provided. Entity alignment is enforced at construction — every entity in the spine must be uniquely identified.

### Structural invariants

- One row per entity — `entity_col` must be unique and non-null
- At most one observation period layer (`obs_start`, `obs_end`, `obs_duration_days`)
- Zero or more episode layers, each with a unique identity (`eps_{identity}_starts`, `eps_{identity}_ends`)
- Zero or more event layers, each with a unique identity (`evt_{identity}`)
- Zero or more computed layers (`evt_comp_{identity}_{stat}`)
- At least one layer must be present

### Column taxonomy

| Column pattern | Contents |
|---|---|
| `{entity_col}` | Entity spine |
| `obs_start`, `obs_end`, `obs_duration_days` | Observation period |
| `eps_{identity}_starts` | Pipe-delimited episode start dates |
| `eps_{identity}_ends` | Pipe-delimited episode end dates |
| `evt_{identity}` | Pipe-delimited event dates |
| `evt_comp_{identity}_{stat}` | Computed event statistics |

### Enrichment

Enrichment methods return a new `CohortTimeline` — the original is never mutated.

```python
# Enrich with episode coverage analysis
timeline = timeline.enrich_with_episode_analysis("inpatient_hospitalization")

# Enrich with event volume (count per entity)
timeline = timeline.enrich_with_event_volume_analysis("ed_visit")

# Enrich with event timing (time to nth event)
timeline = timeline.enrich_with_event_timing_analysis("ed_visit", max_n=3)

# Enrich with event shape (burstiness, memory, density, etc.)
timeline = timeline.enrich_with_event_shape_analysis("ed_visit")
```

Each enrichment call adds `evt_comp_{identity}_{stat}` columns for the relevant statistics. Existing columns are always overwritten — enrichment is idempotent.

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
| `episode_identities` | `list[str]` | Identities of all episode layers |
| `event_identities` | `list[str]` | Identities of all raw event layers |
| `computed_event_identities` | `list[str]` | Identities of all computed event layers |

---

## EventResult family

`EventResult` is an abstract base class. It is never instantiated directly. The three concrete subclasses represent three analytical lenses on event data — volume, timing, and shape — each produced by a dedicated method on `CohortTimelineEventAnalyzer`.

All three share these structural invariants:
- `entity_col` is present, non-null, and unique
- `obs_start` and `obs_end` columns are present
- `identity` is a non-empty string
- `data` is non-empty

### EventResultVolume

Per-entity event counts for one identity. Produced by `CohortTimelineEventAnalyzer.compute_volume()`.

```python
volume = analyzer.compute_volume()

volume.n_with_any       # entities with at least one event
volume.n_with_multiple  # entities with more than one event
```

**Additional column:** `n` — count of events within the observation period. Zero is valid.

### EventResultTiming

Per-entity nth-event timing for one identity. Produced by `CohortTimelineEventAnalyzer.compute_timing(max_n)`.

```python
timing = analyzer.compute_timing(max_n=3)

timing.max_n                # maximum nth event computed
timing.n_with_timing(nth=1) # entities with a valid time_to_1
timing.n_with_timing(nth=2) # entities with a valid time_to_2
```

**Additional columns:** `time_to_1` ... `time_to_{max_n}` — days from `obs_start` to the nth event. `NaN` where the entity has fewer than n events. `recency_days` — days from last event to `obs_end`. `NaN` for entities with zero events.

### EventResultShape

Per-entity behavioral fingerprint for one identity. Produced by `CohortTimelineEventAnalyzer.compute_shape()`.

```python
shape = analyzer.compute_shape()

shape.n_with_gaps    # entities with >= 2 events (gap stats defined)
shape.n_with_shape   # entities with >= 3 events (burstiness defined)
shape.n_with_memory  # entities with >= 4 events (memory defined)
```

**Additional columns:**

| Column | Minimum events required |
|---|---|
| `mean_gap`, `min_gap`, `max_gap` | 2 |
| `std_gap`, `cv_gap`, `burstiness` | 3 |
| `memory` | 4 |
| `density`, `center_of_mass` | 1, obs_duration > 0 |

All stats are `NaN` where the minimum threshold is not met. This is by design — the entity simply did not have enough data.

---


## EpisodeActivityOverTime

Timeseries result from `CohortTimelineEpisodeAnalyzer.compute_activity_over_time()`. Carries the activity DataFrame, the x-axis mode, and — when `mode='calendar'` — the cohort start date needed to reconstruct calendar dates from day offsets.

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
| `n_active` | `int` | Entities with active episode coverage at this day |
| `pct_active` | `float` | Percentage of cohort with active coverage |
| `n_entered` | `int | NA` | Entities whose coverage began at this day |
| `n_exited` | `int | NA` | Entities whose coverage ended at this day |

---

## EpisodeCoverageSummary

Structured summary of episode coverage analysis for one identity. Produced by `CohortTimelineEpisodeAnalyzer.get_summary()`.

Organized into three tiers, each with a different denominator:

| Tier | Denominator | Contents |
|---|---|---|
| Tier 1 | All entities | Coverage prevalence — how many had any coverage, how many had none |
| Tier 2 | Entities with any coverage | Coverage patterns — gaps, continuous coverage, fragmentation |
| Tier 3 | Entities with any coverage | Distributions — episode duration, gap length, episode counts |

This tiered structure enforces correct denominators at every level. The
percentage of members with gaps is computed over members with any coverage
— not over all members. Mixing denominators silently is one of the most
common errors in script-based coverage analysis; `EpisodeCoverageSummary`
makes it impossible.

### Properties

| Property | Type | Description |
|---|---|---|
| `identity` | `str` | Episode identity |
| `n_total` | `int` | Total entities in the cohort (tier 1 denominator) |
| `n_with_any_coverage` | `int` | Entities with at least one episode (tier 2 and 3 denominator) |

The full tier data is accessible via `__repr__()`, which formats all three
tiers with their denominators and percentage breakdowns.

---

## EpisodeDurationResult

Per-episode duration data. Produced by `EpisodeDurationAnalyzer.calc()`.

Note that `EpisodeDurationResult` is one row **per episode**, not one row
per entity — a single entity may have multiple episodes and therefore
multiple rows. This is intentional: duration is a property of individual
episodes, not of entities.

```python
result = analyzer.calc()

result.n_episodes   # total number of episodes
result.n_entities   # number of unique entities
```

**Properties**

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per episode, including `duration_days` and any descriptor columns |
| `entity_col` | `str` | Name of the entity identifier column |
| `identity` | `str | None` | Episode identity from `EpisodeSemantics` |
| `descriptor_cols` | `list[str]` | Names of descriptor columns present in data |
| `n_episodes` | `int` | Total number of episodes |
| `n_entities` | `int` | Number of unique entities |

**`build_arrays(stratify_by=None)`**

Prepares duration arrays for `ArraysViolinPlotter`. Always returns
`"all_data"` as the first key. If `stratify_by` is provided, one
additional key per unique category value is added.

```python
# Unstratified
arrays = result.build_arrays()
# → {"all_data": np.ndarray}

# Stratified by facility
arrays = result.build_arrays(stratify_by="facility_id")
# → {"all_data": np.ndarray, "Facility_A": np.ndarray, "Facility_B": np.ndarray}
```

---

## EpisodeEventInteractionResult

Per-entity event counts classified by position relative to one episode
identity. Produced by `EpisodeEventInteractionAnalyzer.compute_interaction()`.

`EpisodeEventInteractionResult` has no configuration — there are no
thresholds or windows to declare. `NaN` values are scientifically
meaningful absences of signal, not missing data: an entity with no episodes
has no position to classify.

```python
result = analyzer.compute_interaction()

result.n_entities          # total entities in the cohort
result.n_with_episodes     # entities that have at least one episode
result.n_without_episodes  # entities with no episodes at all
```

**Per-entity columns** are in `result.data` (one row per entity):
`n_before`, `n_during`, `n_gaps`, `n_after`, `n_no_episodes`, alongside the
entity column and `obs_start` / `obs_end`.

**Properties**

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per entity |
| `entity_col` | `str` | Entity identifier column |
| `episode_identity` | `str` | Episode identity |
| `event_identity` | `str` | Event identity |
| `n_entities` | `int` | Total entities |
| `n_with_episodes` | `int` | Entities with at least one episode |
| `n_without_episodes` | `int` | Entities with no episodes |

---

## EventCoOccurrenceResult family

The co-occurrence result objects form a six-member family covering three
analytical dimensions: presence (chapter 8), gap timing (chapter 9), and
directionality (chapter 10). Each is produced by a dedicated method on
`EventCoOccurrenceAnalyzer` and consumed by a matching visualizer.

For full documentation — attributes, properties, NaN semantics, column
descriptions, and usage examples — see
`src/eventus/intermediates/event_cooccurrence/README.md`.


## Design notes

**Intermediates and data objects.** Both are validated, self-describing objects that refuse to construct from invalid data. The distinction is one of role and direction, not of capability.

Data objects are validated *input* containers. They sit at the entry point of the pipeline — they know what their columns mean, they enforce structural soundness at construction, and they carry their schema through every downstream step via semantics objects. They have multiple construction paths analogous to constructor overloading in C++, but they do not compute.

Intermediates are validated *result* containers. They sit at the output of an analyzer — they know what was computed, they enforce that the result is structurally sound, and they expose methods that allow further enrichment and interrogation. A `CohortTimeline` is not just a DataFrame with a schema — it is an analytical object that knows what it contains, can be progressively enriched with new computed layers, and carries that enrichment forward through the pipeline. An `EventResultShape` knows it is a behavioral fingerprint and enforces the minimum requirements for every stat it carries.

The pipeline flows from data objects through analyzers to intermediates — never in reverse.

**Immutability by convention.** Enrichment methods on `CohortTimeline` always return new instances. The original is never mutated. This makes pipelines explicit and reproducible — each enrichment step is a discrete, auditable operation.

**Standalone result objects.** `EpisodeActivityOverTime` carries everything needed for interpretation and visualization without any reference back to the object that produced it. This makes it safe to pass to visualizers, serialize, or hand off to downstream analyses.

**Specific errors, not silent failures.** Every constructor raises on invalid data with a message that identifies what went wrong and what to fix. A constructed intermediate is always structurally sound.
