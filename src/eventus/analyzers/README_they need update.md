# analyzers

Analyzers compute quantities from validated data objects.

---

## Why analyzers are separate

Data objects hold and validate data. Cleaners remove bad rows.
Analyzers compute. Visualizers draw. Each abstraction has one job
and one job only.

Keeping analyzers separate means the same validated `Events` object
can be fed to `EventDurationAnalyzer` for duration distributions, or
to `EventsWithinObsPeriodsAnalyzer` for coverage analysis, without
either analyzer knowing anything about the other. New analytical
questions produce new analyzers — nothing else changes.

---

## Classes

### `EventDurationAnalyzer`

> *"I compute the duration of each event in days, with optional stratification."*

Takes a validated `Events` object. Returns a DataFrame with one row
per event and a `duration_days` column. Optional stratification groups
events by any categorical column already present in the data.

```python
from eventus import EventDurationAnalyzer

# Plain durations
analyzer = EventDurationAnalyzer(events)
df       = analyzer.calc()

# Stratified by a categorical column
analyzer = EventDurationAnalyzer(events, stratify_by="hospital_id")
df       = analyzer.calc()
analyzer.summary()
```

**Constructor parameters**
| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `events` | Events | required | A validated Events object |
| `stratify_by` | str \| None | None | Column in events.data to stratify by |
| `max_categories` | int | 10 | Maximum unique categories allowed in stratify_by |

**Output columns**
| Column | Always present | Purpose |
|---|---|---|
| `entity_id_col` | yes | From semantics |
| `duration_days` | yes | End date minus start date in days |
| `identity` | if set | From EventSemantics.identity |
| `stratify_col` | if stratify_by set | Normalized category values |

**Key methods**
```python
df = analyzer.calc()      # → pd.DataFrame
analyzer.summary()        # prints summary to stdout — requires calc() first
```

---

### `EventsWithinObsPeriodsAnalyzer`

> *"I compute how much of each entity's observation period was covered by events, and how much was not."*

This is the core analyzer of the framework. Takes a validated `Events`
object and an `ObsPeriodPerEntity`. Merges overlapping events once at
construction time — all downstream analysis receives clean,
non-overlapping data. Produces a `PipeDelimitedFormatEvents` intermediate.

The `meaningful_gap` parameter controls episode definition — gaps
between consecutive events at or below this threshold are bridged and
treated as continuous active time. This is an analytical decision that
belongs in code, not in a cleaning step.

```python
from eventus import EventsWithinObsPeriodsAnalyzer

# Standard — no gap bridging
analyzer = EventsWithinObsPeriodsAnalyzer(
    events     = events,
    obs_period = obs,
)
result = analyzer.compute_event_coverage()

# With gap bridging — treat gaps ≤ 7 days as continuous
analyzer = EventsWithinObsPeriodsAnalyzer(
    events         = events,
    obs_period     = obs,
    meaningful_gap = 7,
)
result = analyzer.compute_event_coverage()
```

**Constructor parameters**
| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `events` | Events | required | A validated Events object |
| `obs_period` | ObsPeriodPerEntity | required | One observation window per entity |
| `entity_col` | str \| None | None | Defaults to events.semantics.entity_id_col |
| `meaningful_gap` | int | 0 | Gaps ≤ this many days are bridged |

**Key methods**
```python
result = analyzer.compute_event_coverage()  # → PipeDelimitedFormatEvents
```

**What the output contains**

`compute_event_coverage()` returns a `PipeDelimitedFormatEvents` with
one row per entity. Each row carries:
- `span_start`, `span_end` — observation period boundaries
- `span_duration_days` — total observation period length
- `event_starts`, `event_ends` — pipe-delimited event dates clipped
  to the observation period
- `active_days`, `inactive_days` — after calling `self_analyze()`
- `inactive_days_before_first_event`, `inactive_days_after_last_event`,
  `inactive_days_middle` — after calling `self_analyze()`

**Note on overlap merging**

Overlapping events are merged at construction time, before any
analysis. This is not configurable — it is always done. An entity
cannot be both active and inactive on the same day. The `meaningful_gap`
parameter controls whether near-adjacent events are also merged.

---

### `OccurrencesWithinObsPeriodsAnalyzer`

> *"I filter occurrences to within each entity's observation period and organize them for downstream analysis."*

Takes one or more `Occurrences` objects and an `ObsPeriodPerEntity`.
Each occurrence type produces its own pipe-delimited column in the
output, named `occ_{identity}`. Multiple occurrence types are handled
in a single pass — the output intermediate combines them all.

```python
from eventus import OccurrencesWithinObsPeriodsAnalyzer

# Single occurrence type
result = OccurrencesWithinObsPeriodsAnalyzer(
    occurrences = ed_visits,
    obs_period  = obs,
).calc()

# Multiple occurrence types — combined into one intermediate
result = OccurrencesWithinObsPeriodsAnalyzer(
    occurrences = [ed_visits, vaccinations, lab_results],
    obs_period  = obs,
).calc()
```

**Constructor parameters**
| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `occurrences` | Occurrences \| list[Occurrences] | required | One or more validated Occurrences objects. Each must have an identity set. |
| `obs_period` | ObsPeriodPerEntity | required | One observation window per entity |
| `entity_col` | str \| None | None | Defaults to obs_period.semantics.entity_id_col |

**Key methods**
```python
result = analyzer.calc()  # → PipeDelimitedFormatOccurrences
```

**What the output contains**

`calc()` returns a `PipeDelimitedFormatOccurrences` with one row per
entity. Each occurrence type gets its own column:
- `occ_{identity}` — pipe-delimited occurrence dates within the
  observation period, e.g. `"2022-03-15 | 2022-07-02 | 2022-11-18"`
- Entities with no occurrences in period get `NA`

After calling `self_analyze()` on the result, additional columns are
added per identity — see the pipe_delimited_format README for the
full list of temporal statistics.

**Identity requirement**

Every `Occurrences` object passed in must have `identity` set on its
`OccurrenceSemantics`. This is how the output column is named. Raises
`ValueError` if any identity is missing or if two objects share the
same identity.

---

## Internal utils

The `_utils.py` files contain the workhorse code. They are internal
and not part of the public API.

| File | Contains |
|---|---|
| `events_duration_utils.py` | Duration computation, stratification logic |
| `events_within_obs_period_analyzer_utils.py` | Activity/inactivity computation, event clipping |
| `validation_utils.py` | Shared validation helpers across analyzers |

---

## Design note

Analyzers are stateful — `calc()` or `compute_event_coverage()` must
be called before `summary()`. This is intentional: construction
validates inputs, computation is explicit. You always know whether
the analysis has been run.

Analyzers never modify their inputs. The `Events` and
`ObsPeriodPerEntity` objects passed in are unchanged after analysis.
