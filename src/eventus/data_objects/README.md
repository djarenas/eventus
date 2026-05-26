# eventus.data_objects

Validated, self-describing containers for longitudinal data. A data
object that exists is guaranteed to be structurally sound — constructors
raise on invalid inputs, so nothing downstream needs to check.

Row-level cleaning is the responsibility of the cleaners module. Data
objects are the product of that process, not the process itself.

---

## Why data objects exist

A pandas DataFrame does not know what its columns mean or whether its
data is clean. An eventus data object knows both. It holds a DataFrame
as an attribute — not the other way around — and carries the semantics
object that declares what every column means.

The guarantee is binary: either a data object exists and is complete,
or it does not exist at all. There are no partial objects and no silent
failures. A function that receives an `Episodes` object can trust that
every row has a valid entity identifier, a start date, and an end date,
and that start precedes or equals end. That trust was earned at
construction and does not need to be re-earned downstream.

---

## Class hierarchy

```
Episodes
    ↓  one row per entity enforced
EpisodesPerEntity
    ↓  semantic meaning: observation window
ObsPeriodPerEntity

Events
    ↓  one row per entity enforced
EventsPerEntity
```

---

## Classes

### `Episodes`

A validated container for interval episode data. Every row has a valid
entity identifier, a start date, and an end date. Causality is
enforced — start must precede or equal end.

```python
from eventus.data_objects import Episodes

episodes = Episodes(df, sem)
```

The constructor validates in order: semantics type, required columns
present, dates parseable, no nulls in entity/start/end, causality.
Any violation raises immediately with a specific message pointing to
`EpisodesCleaner` for resolution.

**Attributes**

| Attribute | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | Validated episode rows, index reset |
| `semantics` | `EpisodeSemantics` | Column mappings and identity label |

**Construction from clean data**

The normal path is through `EpisodesCleaner`, which handles messy raw
data and hands off only what is structurally sound:

```python
from eventus.cleaners import EpisodesCleaner, EpisodesCleanerConfig

config   = EpisodesCleanerConfig.build_from_yaml("cleaner.yaml")
episodes = EpisodesCleaner(raw_df, sem, config).clean()
```

Direct construction is available when data is already clean:

```python
episodes = Episodes(clean_df, sem)
```

---

### `Events`

A validated collection of point-in-time events. Each row has a valid
entity identifier and a date. Unlike `Episodes`, there is no end date —
events are instantaneous. No causality check, no overlap merging.

```python
from eventus.data_objects import Events

events = Events(df, sem)
```

Dates are normalized on construction — the time component is stripped,
keeping date only. The constructor raises on null entity IDs or null /
unparseable dates.

**Attributes**

| Attribute | Type | Description |
|---|---|---|
| `data` | `pd.DataFrame` | Validated event rows, dates normalized, index reset |
| `semantics` | `EventSemantics` | Column mappings and identity label |

```python
from eventus.cleaners import EventsCleaner, EventsCleanerConfig

config = EventsCleanerConfig.build_from_yaml("cleaner.yaml")
events = EventsCleaner(raw_df, sem, config).clean()
```

---

### `EpisodesPerEntity`

An `Episodes` subclass that enforces one row per entity. Inherits all
`Episodes` validation and adds one constraint: `entity_id_col` must be
unique across all rows.

```python
from eventus.data_objects import EpisodesPerEntity

eps_per = EpisodesPerEntity(df, sem)   # raises if any entity appears twice
```

Useful for membership tables, enrollment records, or any dataset where
one interval per entity is a structural requirement.

Can be promoted to an `ObsPeriodPerEntity` when needed:

```python
obs = eps_per.return_as_obs_period(identity="enrollment_window")
```

---

### `EventsPerEntity`

An `Events` subclass that enforces one row per entity. Inherits all
`Events` validation and adds the same uniqueness constraint.

```python
from eventus.data_objects import EventsPerEntity

evt_per = EventsPerEntity(df, sem)   # raises if any entity appears twice
```

Useful for landmark events — index dates, first diagnoses, enrollment
dates — where one event per entity is a structural requirement.

Can build an observation period centered on the event date:

```python
obs = evt_per.build_obs_period(
    window         = (365, 365),   # 365 days before and after the event
    span_semantics = span_sem,
    identity       = "post_diagnosis_window",
)
```

---

### `ObsPeriodPerEntity`

One observation window per entity. The top of the episode hierarchy —
each row defines the period within which that entity's episodes and
events are analyzed.

```python
from eventus.data_objects import ObsPeriodPerEntity
```

Inherits all validation from `EpisodesPerEntity`. Adds two properties:

| Property | Type | Description |
|---|---|---|
| `identity` | `str` | Name for this observation period. Default `"general_entity"` |
| `construction_path` | `str` | Records how this object was built — inspectable by downstream code |

**Construction paths**

Four named constructors cover the common cases. All produce output with
standard column names `obs_start` and `obs_end`. Direct construction
accepts any column names via `EpisodeSemantics`.

**Direct construction** — full control over column names:

```python
obs = ObsPeriodPerEntity(periods_df, sem, identity="medicaid_2022")
# construction_path → "direct"
```

**`construct_from_calendar()`** — same dates for every entity:

```python
obs = ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = episodes.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "medicaid_2022",
)
# construction_path → "construct_from_calendar"
```

**`construct_from_age_window()`** — per-entity dates derived from date
of birth. Supports `"years"` (default) or `"months"` for pediatric
cohorts. Feb 29 birthdays shift to Feb 28 in non-leap years, with a
warning.

```python
obs = ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demographics_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 25,
    entity_col = "patient_id",
    identity   = "age_18_to_25",
)
# construction_path → "construct_from_age_window(age 18→25 years)"
```

```python
# Pediatric cohort — months
obs = ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demographics_df,
    dob_col    = "date_of_birth",
    age_start  = 6,
    age_end    = 18,
    entity_col = "patient_id",
    age_unit   = "months",
    identity   = "age_6_to_18_months",
)
```

**`construct_from_episodes()`** — first episode start to last episode
end per entity. The broadest possible window. Reuses the column names
from the `Episodes` object.

```python
obs = ObsPeriodPerEntity.construct_from_episodes(
    episodes,
    identity = "hospitalization_window",
)
# construction_path → "construct_from_episodes"
```

**The `construction_path` property** is a first-class attribute.
Downstream code can inspect it to know how the observation period was
built — the same downstream pipeline accepts any `ObsPeriodPerEntity`
regardless of which path produced it.

```python
print(obs.construction_path)
# → "construct_from_age_window(age 18→25 years)"
```

---

## Shared behavior

**`copy()`** — all data object classes implement `copy()`, returning a
new instance of the same type wrapping a copy of the data. The
`construction_path` on `ObsPeriodPerEntity` is preserved through copy.

**`__len__()`** — returns the number of rows in `.data`.

**`__repr__()`** — all classes print a structured summary. For
`ObsPeriodPerEntity` this includes `identity`, `construction_path`,
column names, entity count, and period length statistics.

---

## Design note

Data objects enforce their own validity at construction. This means a
valid object is a guarantee rather than a hope. The cost of establishing
that guarantee is paid once — at the boundary where raw data becomes a
data object — and everything downstream inherits it for free.

This is why data objects do not accept raw DataFrames from arbitrary
sources and silently ignore problems. The constructor is the gate. Once
you are past it, you are on solid ground.
