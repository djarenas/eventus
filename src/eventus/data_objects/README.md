# data_objects

Validated containers for event and occurrence data. The core design
principle applies here most directly: **if it exists, it is complete.**
Every constructor validates its input and raises a specific error rather
than producing a partial or broken object. Row-level cleaning is always
the responsibility of the cleaners — data objects assume the data is
already structurally sound.

---

## The hierarchy

```
Events                    Occurrences
    ↓                         ↓
EventsPerEntity           OccurrencesPerEntity
    ↓
ObsPeriodPerEntity
```

`Events` and `Occurrences` are siblings — parallel tracks for interval
data and point-in-time data respectively. Both validate at construction.
Both have cleaners. Both feed analyzers.

`EventsPerEntity` and `OccurrencesPerEntity` are subclasses that add one
constraint: the entity column must be unique across all rows.

`ObsPeriodPerEntity` subclasses `EventsPerEntity` and adds semantic
meaning — each row is an observation window for that entity, not just
any interval.

---

## Classes

### `Events`

A validated collection of interval events.
Enforces the event concept. For each row to be an event, it must have
an entity, a start, and an end — that is it. All downstream use of this
object does not need to know if it was a hospitalization, insurance
coverage, or anything else.

A pandas DataFrame does not know what data it holds, it just knows how
to hold it. The semantics attribute tells the object how to handle the
data. Furthermore, the events object may still carry other data like
"BMI during the event". All the object cares about is that the DataFrame
has sufficient information to be called an event.

**Construction**
```python
from eventus import EventSemantics, Events

sem    = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)
events = Events(df, sem)
```

Raises on: missing columns, null entity IDs, null or unparseable dates.
Why? Because an event cannot exist if there is no entity, start, or end.

Does not raise on: causality violations, overlaps, duplicates — those
are cleaner responsibilities.

**Key methods**
```python
events.filter_by_entities(entity_ids)   # → Events
events.filter_by_dates(start, end)      # → Events
events.copy()                           # → Events
events.print_summary()                  # prints to stdout
events.build_summary()                  # → dict
```

---

### `EventsPerEntity`

Subclass of `Events`. Adds one constraint: `entity_id_col` must be
unique across all rows. Raises `ValueError` if any entity appears
more than once.

Useful for membership tables, enrollment records, or any dataset where
one row per entity is a structural requirement.

```python
from eventus import EventsPerEntity

epe = EventsPerEntity(df, sem)
```

**Additional method**
```python
epe.return_as_obs_period(identity="my_obs_period")  # → ObsPeriodPerEntity
```

Use `return_as_obs_period()` when you already have an `EventsPerEntity`
and need to pass it to an analyzer that requires an `ObsPeriodPerEntity`.

---

### `ObsPeriodPerEntity`

Subclass of `EventsPerEntity`. Each row defines the observation window
for one entity — the period within which that entity's events and
occurrences are analyzed.

**Four construction paths:**

**Direct** — full control over column names:
```python
from eventus import ObsPeriodPerEntity

obs = ObsPeriodPerEntity(df, sem, identity="medicaid_2022")
```

**Calendar** — same dates for every entity:
```python
obs = ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = events.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "medicaid_2022",
)
# Output columns: patient_id, obs_start, obs_end
```

**Age window** — per-entity dates derived from date of birth:
```python
obs = ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demographics_df,
    dob_col    = "date_of_birth",
    age_start  = 65,
    age_end    = 70,
    entity_col = "patient_id",
    age_unit   = "years",           # "years" or "months"
    identity   = "age_65_to_70",
)
# age_unit="months" for pediatric cohorts e.g. age_start=6, age_end=18
# Output columns: patient_id, obs_start, obs_end
```

**From events** — first event start to last event end per entity:
```python
obs = ObsPeriodPerEntity.construct_from_events(
    events   = events,
    identity = "full_activity_window",
)
# Broadest possible window. Reuses events column names.
```

**Key methods**
```python
obs.filter_by_entities(entity_ids)  # → ObsPeriodPerEntity
obs.copy()                          # → ObsPeriodPerEntity
obs.summary()                       # prints to stdout
```

**Notes**
- Classmethods output standard column names: `obs_start`, `obs_end`
- Direct construction accepts any column names via `EventSemantics`
- Feb 29 birthdays shifted to Feb 28 in non-leap years with a warning
- Future dates trigger a warning, not an error

---

### `Occurrences`

A validated collection of point-in-time occurrences. Each row has an
entity ID and a date — no end date, no duration.

An occurrence has no duration — it happened, at a point in time, to an
entity. The semantics attribute tells the object which columns carry
those concepts. Everything else in the DataFrame is carried through
untouched. All downstream use of this object does not need to know if
it was an ED visit, a vaccination, or a diagnosis date.

```python
from eventus import OccurrenceSemantics, Occurrences

sem  = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)
occs = Occurrences(df, sem)
```

Raises on: null entity IDs, null or unparseable dates.

**Key methods**
```python
occs.filter_by_entities(entity_ids)         # → Occurrences
occs.filter_by_dates(start=None, end=None)  # → Occurrences
occs.count_per_entity()                     # → pd.Series
occs.copy()                                 # → Occurrences
occs.print_summary()                        # prints to stdout
occs.build_summary()                        # → dict
```

---

### `OccurrencesPerEntity`

Subclass of `Occurrences`. Adds one constraint: `entity_id_col` must
be unique across all rows.

Useful for landmark events — index diagnoses, enrollment dates, first
known occurrences — where one occurrence per entity is a structural
requirement.

```python
from eventus import OccurrencesPerEntity

ope = OccurrencesPerEntity(df, sem)
```

**Additional method**
```python
ope.build_obs_period(
    window         = (365, 365),   # (days_before, days_after)
    span_semantics = span_sem,
    identity       = "post_diagnosis_window",
)
# → ObsPeriodPerEntity
# span_start = occurrence_date - 365
# span_end   = occurrence_date + 365
```

Use `build_obs_period()` when your observation window is anchored to
a per-entity event date rather than a fixed calendar period.

---

## Internal utils

The `_utils.py` files contain the workhorse code — overlap merging,
span construction, age window arithmetic, and clipping logic. They
are internal and not part of the public API.

| File | Contains |
|---|---|
| `events_utils.py` | Overlap merging, date clipping |
| `obs_period_per_entity_utils.py` | Calendar and age window span builders, identity validation |
| `occurrences_utils.py` | Span construction from occurrence dates |

---

## What data objects do NOT do

- They do not clean data — use `EventsCleaner` or `OccurrencesCleaner`
- They do not compute durations or coverage — use analyzers
- They do not merge overlapping events on construction — that is an
  explicit step in `EventsWithinObsPeriodsAnalyzer`
