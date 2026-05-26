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

EventEpisodeResult                      — event-episode temporal relationships

SurvivalResult                          — Kaplan-Meier survival curve
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

## SurvivalResult

A validated Kaplan-Meier survival curve. `SurvivalResult` is standalone and reusable — it carries everything needed to plot and interpret a survival curve without any reference back to the object that produced it. It is not tied to event analysis specifically; any analysis that produces a KM-style curve produces a `SurvivalResult`.

Current producer: `CohortTimelineEventAnalyzer.compute_survival()`

### Structural invariants

- Survival values are in `[0, 1]`
- `ci_lower <= survival <= ci_upper` at every timepoint
- `n_at_risk` is monotonically non-increasing
- `n_episodes_total + n_censored_total == n_total`
- Empty data is valid only when `n_episodes_total == 0`

### Construction

`SurvivalResult` is produced by analyzers, not constructed directly. Its properties are read-only.

### Properties

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per unique episode timepoint |
| `label` | `str` | Human-readable label for the curve |
| `n_total` | `int` | Total cohort size |
| `n_episodes_total` | `int` | Entities who experienced the episode |
| `n_censored_total` | `int` | Entities censored |
| `episode_rate_pct` | `float` | Percentage of cohort that experienced the episode |
| `median_survival` | `float | None` | Smallest day where S(t) <= 0.5. `None` if never crossed |
| `max_day` | `int | None` | Last timepoint in the survival table |
| `ci_method` | `str` | Confidence interval method (`'greenwood'`) |

### Data columns

| Column | Type | Description |
|---|---|---|
| `day` | `int` | Timepoint in days from obs_start |
| `n_at_risk` | `int` | Entities still under observation |
| `n_episodes` | `int` | Episodes occurring at this timepoint |
| `n_censored` | `int` | Entities censored at this timepoint |
| `survival` | `float` | KM estimate S(t) |
| `ci_lower` | `float` | Lower 95% confidence bound |
| `ci_upper` | `float` | Upper 95% confidence bound |

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

## EventEpisodeResult

Per-entity temporal relationship statistics between one event identity
and one episode identity. Produced by `EventEpisodeAnalyzer.compute()`.

`EventEpisodeResult` has no configuration — there are no thresholds or
windows to declare. The computation is nearest-neighbor gaps within the
observation period. NaN values are scientifically meaningful absences
of signal, not missing data.

```python
result = analyzer.compute()

result.n_with_both              # entities with both events and episodes
result.n_evt_only               # entities with events but no episodes
result.n_episode_only           # entities with episodes but no events
result.n_neither                # entities with neither
result.n_with_evt_to_episode_gap  # entities with at least one occ → episode pair
result.n_with_episode_to_evt_gap  # entities with at least one episode → occ pair
```

**Properties**

| Property | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | One row per entity |
| `entity_col` | `str` | Entity identifier column |
| `identity_occ` | `str` | Event identity |
| `identity_episode` | `str` | Episode identity |
| `n_entities` | `int` | Total entities |
| `n_with_both` | `int` | Entities with ≥1 event and ≥1 episode |
| `n_evt_only` | `int` | Entities with events but no episodes |
| `n_episode_only` | `int` | Entities with episodes but no events |
| `n_neither` | `int` | Entities with neither |
| `n_with_evt_to_episode_gap` | `int` | Entities with ≥1 qualifying occ→episode pair |
| `n_with_episode_to_evt_gap` | `int` | Entities with ≥1 qualifying episode→occ pair |

**NaN semantics**

NaN in gap statistics may mean any of: entity had no events, entity had
no episodes, entity had both but no qualifying temporal pairs within the
observation period, or entity had only one qualifying pair (std only).
All are scientifically valid — absent signal, not missing data.

---

## Design notes

**Intermediates and data objects.** Both are validated, self-describing objects that refuse to construct from invalid data. The distinction is one of role and direction, not of capability.

Data objects are validated *input* containers. They sit at the entry point of the pipeline — they know what their columns mean, they enforce structural soundness at construction, and they carry their schema through every downstream step via semantics objects. They have multiple construction paths analogous to constructor overloading in C++, but they do not compute.

Intermediates are validated *result* containers. They sit at the output of an analyzer — they know what was computed, they enforce that the result is structurally sound, and they expose methods that allow further enrichment and interrogation. A `CohortTimeline` is not just a DataFrame with a schema — it is an analytical object that knows what it contains, can be progressively enriched with new computed layers, and carries that enrichment forward through the pipeline. An `EventResultShape` knows it is a behavioral fingerprint and enforces the minimum requirements for every stat it carries.

The pipeline flows from data objects through analyzers to intermediates — never in reverse.

**Immutability by convention.** Enrichment methods on `CohortTimeline` always return new instances. The original is never mutated. This makes pipelines explicit and reproducible — each enrichment step is a discrete, auditable operation.

**Standalone result objects.** `SurvivalResult` and `EpisodeActivityOverTime` carry everything needed for interpretation and visualization without any reference back to the object that produced them. This makes them safe to pass to visualizers, serialize, or hand off to downstream analyses.

**Specific errors, not silent failures.** Every constructor raises on invalid data with a message that identifies what went wrong and what to fix. A constructed intermediate is always structurally sound.
