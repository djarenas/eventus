# eventus.cleaners

Transparent, auditable pipelines for preparing raw data and subsetting
validated data objects. The cleaners module contains two distinct
families of classes with different responsibilities:

**Cleaners** — transform raw DataFrames into validated data objects.
Every decision is recorded. Nothing is silent.

**Filters** — subset validated data objects by entity or date.
Chainable. The original object is never mutated.

---

## Why cleaners exist

An eventus data object will not construct from dirty data. This is by
design — a data object that exists is guaranteed to be structurally
sound. The cleaners are the required path from a raw DataFrame to that
guarantee.

Real data is messy. Dates are stored as strings. Start dates appear
after end dates. Entity IDs are missing. The cleaner's job is to handle
that messiness explicitly, record every decision it makes, and hand off
only what is structurally sound to the data object constructor.

The distinction between a cleaner and a data object is a distinction
between process and product. The cleaner is the process — configurable,
auditable, reproducible. The data object is the product — validated,
complete, ready for analysis.

---

## The pipeline

```
Raw DataFrame
    ↓
EpisodesCleaner / EventsCleaner    — configured cleaning pipeline
    ↓                                    records every rejected and
    ↓                                    modified row
Episodes / Events                  — validated, complete, ready
    ↓
EpisodesFilter / EventsFilter /    — optional subsetting
ObsPeriodFilter
    ↓
CohortTimeline / Analyzers
```

---

## Cleaners

### `EpisodesCleaner`

Cleans raw episode data and produces a validated `Episodes` object. Every
rejected row is recorded with an explicit reason. Rows that are kept
but modified — coalesced dates, swapped causality — are recorded
separately in a modified log.

```python
from eventus.cleaners import EpisodesCleaner, EpisodesCleanerConfig

config  = EpisodesCleanerConfig.build_from_yaml("episode_cleaner.yaml")
cleaner = EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()
cleaner.print_report()
```

**Cleaning pipeline (in order)**

| Step | Controlled by | Action |
|---|---|---|
| 1. Parse dates | `parse_dates` | Coerce string columns to datetime. Unparseable rows → rejected |
| 2. Normalize dates | `normalize_dates` | Strip time component — keep date only |
| 3. Null entity IDs | always | Rows with null entity ID → rejected |
| 4. Null start / end | `coalesce_dates` | If False: null start or end → rejected. If True: fill from the other date and record as modified |
| 5. Date floor / ceiling | `date_floor`, `date_ceiling` | Rows outside the window → rejected |
| 6. Causality check | `causality_check` | `"reject"`: end < start → rejected. `"swap"`: dates are swapped and row is kept, recorded as modified |
| 7. Drop duplicates | `drop_duplicates` | Exact duplicates on entity + start + end → rejected |
| 8. Merge overlapping | `merge_overlapping` | Adjacent or overlapping intervals merged into episodes |

**The modified log** is a key feature of `EpisodesCleaner`. Unlike a
simple reject/keep pipeline, the cleaner distinguishes between rows
that were removed and rows that were repaired. A coalesced date or
swapped causality is not a silent fix — it is recorded with an explicit
reason and accessible via `cleaner.modified`.

**Quality report**

```python
cleaner.print_report()       # prints structured summary to stdout
cleaner.calc_report()        # → dict, for programmatic access
cleaner.rejected             # → pd.DataFrame of rejected rows
cleaner.modified             # → pd.DataFrame of modified rows
```

Example output:
```
Cleaning report
────────────────────────────────────────────────────────
Total input rows:                              125,432
────────────────────────────────────────────────────────
  Rejected:
    null_entity_id:                              1,203   (1.0%)
    unparseable_start_date:                        441   (0.4%)
    end_before_start_rejected:                     218   (0.2%)
    duplicate_row:                                  97   (0.1%)
  Modified (kept):
    start_coalesced_from_end:                      312   (0.2%)
────────────────────────────────────────────────────────
Total rejected:                                1,959   (1.6%)
Total modified (kept):                           312   (0.2%)
Clean rows:                                  123,161   (98.2%)
```

---

### `EpisodesCleanerConfig`

> *"I am a reproducible set of rules for what counts as a valid episode row. I can be built from a YAML file and saved back to one."*

All parameters have sensible defaults. Override via `build_from_yaml()`
to make cleaning choices explicit, versioned, and reproducible.

```python
config = EpisodesCleanerConfig.build_from_yaml("episode_cleaner.yaml")
config = EpisodesCleanerConfig.build_with_defaults()
config = EpisodesCleanerConfig()   # same as build_with_defaults()
config.to_yaml("episode_cleaner.yaml")
```

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `normalize_dates` | bool | `True` | Strip time component from date columns |
| `coalesce_dates` | bool | `False` | Fill missing start from end (or vice versa) and record as modified |
| `causality_check` | str | `"reject"` | `"reject"` or `"swap"` when end < start |
| `parse_dates` | bool | `True` | Auto-parse date columns from strings |
| `drop_duplicates` | bool | `True` | Remove rows identical on entity + start + end |
| `merge_overlapping` | bool | `False` | Merge overlapping or adjacent intervals |
| `meaningful_gap` | int | `0` | Gaps ≤ this many days are bridged when merging |
| `date_floor` | str | `"1920-01-01"` | Reject rows with start before this date |
| `date_ceiling` | str | `"2100-01-01"` | Reject rows with end after this date |

**YAML example**

```yaml
normalize_dates:   true
coalesce_dates:    false
causality_check:   reject
parse_dates:       true
drop_duplicates:   true
merge_overlapping: false
meaningful_gap:    0
date_floor:        "1920-01-01"
date_ceiling:      "2100-01-01"
```

---

### `EventsCleaner`

Cleans raw event data and produces a validated `Events`
object. Events are simpler than episodes — one date column, no
causality concept — so the pipeline is correspondingly leaner.

```python
from eventus.cleaners import EventsCleaner, EventsCleanerConfig

config  = EventsCleanerConfig.build_from_yaml("evt_cleaner.yaml")
cleaner = EventsCleaner(raw_df, sem, config)
occs    = cleaner.clean()
cleaner.print_report()
```

**Cleaning pipeline (in order)**

| Step | Controlled by | Action |
|---|---|---|
| 1. Parse dates | `parse_dates` | Coerce string column to datetime. Unparseable rows → rejected |
| 2. Normalize dates | `normalize_dates` | Strip time component — keep date only |
| 3. Null entity IDs | always | Rows with null entity ID → rejected |
| 4. Null dates | always | Rows with null date → rejected |
| 5. Date floor / ceiling | `date_floor`, `date_ceiling` | Rows outside the window → rejected |
| 6. Drop duplicates | `drop_duplicates` | Exact duplicates on entity + date → rejected |

**Quality report**

```python
cleaner.print_report()       # prints structured summary to stdout
cleaner.quality_report_df()  # → pd.DataFrame
cleaner.rejected             # → pd.DataFrame of rejected rows
```

---

### `EventsCleanerConfig`

> *"I am a reproducible set of rules for what counts as a valid event row. I can be built from a YAML file and saved back to one."*

```python
config = EventsCleanerConfig.build_from_yaml("evt_cleaner.yaml")
config = EventsCleanerConfig.build_with_defaults()
config.to_yaml("evt_cleaner.yaml")
```

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `normalize_dates` | bool | `True` | Strip time component from date column |
| `parse_dates` | bool | `True` | Auto-parse date column from strings |
| `drop_duplicates` | bool | `True` | Remove rows identical on entity + date |
| `date_floor` | str | `"1920-01-01"` | Reject rows with date before this value |
| `date_ceiling` | str | `"2100-01-01"` | Reject rows with date after this value |

**YAML example**

```yaml
normalize_dates: true
parse_dates:     true
drop_duplicates: true
date_floor:      "1920-01-01"
date_ceiling:    "2100-01-01"
```

---

## Filters

Filters subset validated data objects. They are chainable — each method
returns a new filter wrapping the result, so calls compose naturally.
The original object is never mutated. Call `.result` to retrieve the
final filtered object.

```python
from eventus.cleaners import EpisodesFilter
from eventus.types import DateBoundary

filtered = (
    EpisodesFilter(episodes)
    .by_entities(my_entity_ids)
    .by_dates(start="2022-01-01", end="2022-12-31")
    .result
)
```

### `DateBoundary`

Controls whether a date boundary is inclusive or exclusive. Imported
from `eventus.types`.

```python
from eventus.types import DateBoundary

DateBoundary.INCLUSIVE   # >= or <=
DateBoundary.EXCLUSIVE   # >  or <
```

All filter `by_dates()` and `to_obs_period()` methods accept
`start_bound` and `end_bound` parameters of type `DateBoundary`.
Default is `DateBoundary.INCLUSIVE` for both.

---

### `EpisodesFilter`

```python
from eventus.cleaners import EpisodesFilter

EpisodesFilter(episodes).by_entities(entity_ids).result         # → Episodes
EpisodesFilter(episodes).by_dates(start, end).result            # → Episodes
EpisodesFilter(episodes).to_obs_period(obs, clip=True).result   # → Episodes
```

**Methods**

`by_entities(entity_ids)` — keep only episodes belonging to the
specified entities.

`by_dates(start, end, start_bound, end_bound)` — keep only episodes
whose start is within the start bound and end is within the end bound.
At least one of `start` or `end` must be provided.

`to_obs_period(obs_period, clip, start_bound, end_bound)` — filter
episodes to each entity's observation window. Only entities present in
`obs_period` are kept. The `clip` parameter controls what happens to
episodes that partially overlap the window:
- `clip=True` (default) — episodes are clipped to the obs boundary
- `clip=False` — episodes that partially overlap are dropped entirely

---

### `EventsFilter`

```python
from eventus.cleaners import EventsFilter

EventsFilter(occs).by_entities(entity_ids).result          # → Events
EventsFilter(occs).by_dates(start, end).result             # → Events
EventsFilter(occs).to_obs_period(obs).result               # → Events
```

Events are point-in-time — there is no clipping. An event
either falls inside the observation window or it does not.

---

### `ObsPeriodFilter`

```python
from eventus.cleaners import ObsPeriodFilter

ObsPeriodFilter(obs).by_entities(entity_ids).result             # → ObsPeriodPerEntity
ObsPeriodFilter(obs).by_dates(start, end).result                # → ObsPeriodPerEntity
```

`ObsPeriodPerEntity` defines one observation window per entity — it
*is* the time window. Filtering by date keeps only entities whose
entire observation window falls within the given range. It does not
clip the windows themselves. To clip episodes to obs windows, use
`EpisodesFilter.to_obs_period()`.

The `construction_path` property on the filtered result is updated to
record that a filter was applied.

---

## Design notes

**Config is the methods section.** Every analytical and cleaning
decision lives in a versioned YAML file, not in code. A config can be
built from YAML, inspected, modified, and saved back to YAML. The
config file is the record of what was done — reproducible and auditable
by design.

**Rejected and modified are first-class outputs.** A cleaner that only
tells you how many rows it dropped is not auditable. `EpisodesCleaner`
records every rejected row with an explicit reason and every modified
row with an explicit description of what changed. These are accessible
as DataFrames and can be inspected, saved, or reported on.

**Filters are chainable and non-mutating.** Each filter call returns a
new filter wrapping the result. The original object is never changed.
This makes filter pipelines explicit and composable without side
effects.

**The cleaner and the data object enforce the same rules, at different
stages.** The cleaner handles the messy reality of raw data — it
repairs what can be repaired and rejects what cannot. The data object
enforces that what it receives is already sound. The two layers are
complementary, not redundant.
