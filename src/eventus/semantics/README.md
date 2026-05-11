# semantics

Column mappings and identity labels. Semantics objects decouple all
analytical logic from specific data schemas — the rest of the framework
never references column names directly, only through a semantics object.

---

## Why semantics exist

Real datasets have idiosyncratic column names. One dataset calls it
`patient_id`, another calls it `member_id`, a third calls it
`enrollee_key`. Without a semantics layer, every class would need to
accept column names as constructor arguments, or worse, assume fixed
column names that break on any real dataset.

Semantics objects solve this once. Define them at the top of your
analysis, pass them into data objects, and everything downstream just
works — regardless of what your columns are named.

---

## Classes

### `EventSemantics`

> *"I am a description of what columns mean in event data. I hold no data and do no computation."*

```python
from eventus import EventSemantics

sem = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)
```

**Required fields**
| Field | Type | Purpose |
|---|---|---|
| `entity_id_col` | str | Column identifying the entity |
| `start_time_col` | str | Column for event start date |
| `end_time_col` | str | Column for event end date |

**Optional fields**
| Field | Type | Purpose |
|---|---|---|
| `identity` | str \| None | Human-readable label. Flows into intermediate column names and plot titles. No spaces — use underscores. Default None. |
| `event_id_col` | str \| None | Column for a unique event identifier |
| `event_type_col` | str \| None | Column for event type or category |
| `metadata_cols` | list[str] | Additional columns to carry through validation |

**Build from YAML**
```python
sem = EventSemantics.build_from_yaml("event_semantics.yaml")
```

```yaml
entity_id_col:  patient_id
start_time_col: admit_date
end_time_col:   discharge_date
identity:       inpatient_hospitalization
```

---

### `OccurrenceSemantics`

> *"I am a description of what columns mean in occurrence data. I hold no data and do no computation."*

```python
from eventus import OccurrenceSemantics

sem = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)
```

**Required fields**
| Field | Type | Purpose |
|---|---|---|
| `entity_id_col` | str | Column identifying the entity |
| `date_col` | str | Column for the occurrence date |

**Optional fields**
| Field | Type | Purpose |
|---|---|---|
| `identity` | str \| None | Human-readable label. Flows into intermediate column names (`occ_ed_visit`) and plot titles. No spaces — use underscores. Default None. |
| `occurrence_id_col` | str \| None | Column for a unique occurrence identifier |
| `metadata_cols` | list[str] | Additional columns to carry through validation |

**Build from YAML**
```python
sem = OccurrenceSemantics.build_from_yaml("occurrence_semantics.yaml")
```

```yaml
entity_id_col: patient_id
date_col:      ed_visit_date
identity:      ed_visit
```

---

## Identity rules

The `identity` attribute must contain only letters, numbers, and
underscores (`^[a-zA-Z0-9_]+$`). The constructor raises if this
is violated.

```python
# Valid
EventSemantics(..., identity="inpatient_hospitalization")
OccurrenceSemantics(..., identity="ed_visit")

# Raises ValueError
EventSemantics(..., identity="inpatient hospitalization")  # spaces
OccurrenceSemantics(..., identity="ed-visit")              # hyphens
```

Identity flows into intermediate column names — `occ_ed_visit`,
`occ_hepatitis_b` — so it must be safe to use as part of a column name.

---

## Where semantics flow

Once defined, a semantics object is passed into every downstream object
that needs it:

```python
from eventus import EventSemantics, OccurrenceSemantics, Events, Occurrences
from eventus.cleaners import EventsCleaner, EventsCleanerConfig
from eventus.intermediates import CohortTimeline

event_sem = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)

occ_sem = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)

# Semantics flow into data objects and cleaners
events    = EventsCleaner(raw_df, event_sem, config).clean()
ed_visits = Events(df, event_sem)

# And from there into CohortTimeline
timeline = CohortTimeline.build_from_components(
    obs_period  = obs,
    events      = events,
    occurrences = ed_visits,
)
```

The semantics object travels with the data. Filter methods and copy
methods preserve it automatically — you never need to reattach it.

```python
filtered = events.filter_by_entities(some_ids)
filtered.semantics  # same EventSemantics object, unchanged
```

---

## Design note

Semantics objects are plain dataclasses — no methods beyond
`build_from_yaml()` and `__repr__()`. They hold no data and do no
computation. Their only job is to carry column name mappings and an
identity label from construction through to visualization.

This is intentional. Keeping semantics objects thin means they can be
defined once at the top of an analysis script, saved to YAML for
reproducibility, and shared across multiple data objects without any
risk of side effects.