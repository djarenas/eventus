# eventus.semantics

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

### `DescriptorColConfig`

Declares the type of one descriptor column. Lives in semantics because
it describes what a column *is* — not what to do with it. Cleaners and
analyzers decide how to aggregate.

```python
from eventus.semantics import DescriptorColConfig

DescriptorColConfig(type="category")   # discrete labels
DescriptorColConfig(type="numeric")    # numbers
```

| type | Examples |
|---|---|
| `"category"` | hospital_id, icd10_condition, triage_level |
| `"numeric"` | bmi_at_admission, wait_time_mins, length_of_stay |

---

### `EventSemantics`

> *"I am a description of what columns mean in event data. I hold no data and do no computation."*

```python
from eventus import EventSemantics
from eventus.semantics import DescriptorColConfig

sem = EventSemantics(
    identity        = "inpatient_hospitalization",
    entity_id_col   = "patient_id",
    start_time_col  = "admit_date",
    end_time_col    = "discharge_date",
    also_defined_by = ["hospital_id"],
    descriptor_cols = {
        "icd10_condition": DescriptorColConfig(type="category"),
        "bmi_at_admission": DescriptorColConfig(type="numeric"),
    },
)
```

**Fields — in declaration order**

| Field | Type | Required | Purpose |
|---|---|:---:|---|
| `identity` | str \| None | | What kind of events these are. Flows into intermediate column names and plot titles. Letters, numbers, underscores only. |
| `entity_id_col` | str | ✓ | Column identifying the entity |
| `start_time_col` | str | ✓ | Column for event start date |
| `end_time_col` | str | ✓ | Column for event end date |
| `also_defined_by` | list[str] \| None | | Columns that are part of the event's identity — see below |
| `descriptor_cols` | dict[str, DescriptorColConfig] \| None | | Columns that describe the event — see below |
| `event_id_col` | str \| None | | Column for a unique event identifier |
| `event_type_col` | str \| None | | Column for event type or category |

---

### `OccurrenceSemantics`

> *"I am a description of what columns mean in occurrence data. I hold no data and do no computation."*

```python
from eventus import OccurrenceSemantics
from eventus.semantics import DescriptorColConfig

sem = OccurrenceSemantics(
    identity          = "ed_visit",
    entity_id_col     = "patient_id",
    date_col          = "ed_visit_date",
    also_defined_by   = ["hospital_id"],
    descriptor_cols   = {
        "triage_level":   DescriptorColConfig(type="category"),
        "wait_time_mins": DescriptorColConfig(type="numeric"),
    },
)
```

**Fields — in declaration order**

| Field | Type | Required | Purpose |
|---|---|:---:|---|
| `identity` | str \| None | | What kind of occurrences these are |
| `entity_id_col` | str | ✓ | Column identifying the entity |
| `date_col` | str | ✓ | Column for the occurrence date |
| `also_defined_by` | list[str] \| None | | Columns that are part of the occurrence's identity — see below |
| `descriptor_cols` | dict[str, DescriptorColConfig] \| None | | Columns that describe the occurrence — see below |
| `occurrence_id_col` | str \| None | | Column for a unique occurrence identifier |

---

## `also_defined_by` — what makes this event unique

`also_defined_by` answers the question: *"Beyond entity and date, what
else defines whether two records are the same event?"*

This is one of the most important design decisions in any interval or
occurrence analysis. It determines what the cleaner treats as a
duplicate, and what it refuses to merge.

### Events example — hospitalizations

A hospitalization is defined by patient + admit date + discharge date.
But if your data has transfers between hospitals, a patient may have
two overlapping records at different hospitals. Are those the same
hospitalization?

**No.** A hospitalization at Hospital A and a hospitalization at
Hospital B are different events — even if they overlap in time. The
hospital is part of what defines the event.

```python
EventSemantics(
    identity        = "inpatient_hospitalization",
    entity_id_col   = "patient_id",
    start_time_col  = "admit_date",
    end_time_col    = "discharge_date",
    also_defined_by = ["hospital_id"],   # can't merge across hospitals
)
```

The cleaner reads `also_defined_by` and only merges overlapping
intervals where `hospital_id` matches. Two stays at different hospitals
are kept separate even if they overlap in time.

### Occurrences example — ED visits

An ED visit is defined by patient + visit date. But if your data
records visits across multiple hospitals, a patient could have two
records on the same date at different hospitals. Are those the same
visit?

**No.** A visit to Hospital A and a visit to Hospital B on the same
day are different events — the hospital defines the occurrence.

```python
OccurrenceSemantics(
    identity        = "ed_visit",
    entity_id_col   = "patient_id",
    date_col        = "ed_visit_date",
    also_defined_by = ["hospital_id"],   # can't dedup across hospitals
)
```

The cleaner reads `also_defined_by` and only deduplicates records
where `hospital_id` also matches. Two visits to different hospitals
on the same date are kept separate.

### What `also_defined_by` is NOT

`also_defined_by` is not for columns that merely *describe* the event.
A patient's BMI at admission describes the hospitalization — it doesn't
define it. Two records with the same patient, same admit date, same
discharge date, same hospital, but different BMI values are the same
event recorded with different values — not two different events.

```python
EventSemantics(
    ...
    also_defined_by = ["hospital_id"],        # ✓ defines the event
    descriptor_cols = {
        "bmi_at_admission": DescriptorColConfig(type="numeric"),  # ✓ describes it
        "icd10_condition":  DescriptorColConfig(type="category"),
    },
)
```

The cleaner aggregates descriptor columns across merged rows — e.g.
taking the median BMI, or collecting unique ICD-10 codes. It never
aggregates `also_defined_by` columns — those are identity columns.

---

## `descriptor_cols` — what describes this event

`descriptor_cols` declares columns that carry analytical information
about the event but are not part of its identity. They survive the
cleaning pipeline and are available for downstream analysis and
stratification.

Two things are declared per column: a name and a type.

```python
descriptor_cols = {
    "icd10_condition":  DescriptorColConfig(type="category"),
    "bmi_at_admission": DescriptorColConfig(type="numeric"),
}
```

The type declaration tells downstream code what kind of values to
expect — cleaners use it to choose valid aggregation strategies,
analyzers use it for stratification logic. The actual aggregation rule
(mean? median? unique?) is a cleaning decision declared in
`EventsCleanerConfig.merge`, not here.

**`also_defined_by` and `descriptor_cols` must be disjoint.** A column
is either part of the event's identity or a descriptor — never both.
The constructor raises if they overlap.

---

## `metadata_cols` — convenience property

Both semantics classes expose `metadata_cols` as a computed property:

```python
sem.metadata_cols
# → also_defined_by + descriptor_cols.keys()
# → ["hospital_id", "icd10_condition", "bmi_at_admission"]
```

This is the list of all extra columns that should survive the cleaning
pipeline. Downstream code uses this instead of accessing
`also_defined_by` and `descriptor_cols` separately.

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
`evt_comp_inpatient_hospitalization_active_days` — so it must be safe
to use as part of a column name.

---

## Build from YAML

```python
sem = EventSemantics.build_from_yaml("event_semantics.yaml")
sem = OccurrenceSemantics.build_from_yaml("occurrence_semantics.yaml")
```

```yaml
# event_semantics.yaml
identity:        inpatient_hospitalization
entity_id_col:   patient_id
start_time_col:  admit_date
end_time_col:    discharge_date
also_defined_by:
  - hospital_id
descriptor_cols:
  icd10_condition:
    type: category
  bmi_at_admission:
    type: numeric
```

```yaml
# occurrence_semantics.yaml
identity:        ed_visit
entity_id_col:   patient_id
date_col:        ed_visit_date
also_defined_by:
  - hospital_id
descriptor_cols:
  triage_level:
    type: category
  wait_time_mins:
    type: numeric
```

---

## Where semantics flow

Once defined, a semantics object is passed into every downstream object
that needs it — data objects, cleaners, analyzers. It travels with the
data automatically.

```python
sem     = EventSemantics(identity="inpatient_hospitalization", ...)
events  = EventsCleaner(raw_df, sem, config).clean()
result  = EventDurationAnalyzer(events, descriptor_cols=["icd10_condition"]).calc()
```

The semantics object is preserved through filtering and copying:

```python
filtered = events.filter_by_entities(some_ids)
filtered.semantics   # same EventSemantics, unchanged
```

---

## Design note

Semantics objects declare structure — what columns exist and what they
mean. They do not declare behavior — what to do with those columns.
That separation is intentional.

`also_defined_by` says *"a hospitalization IS defined by its hospital."*
That is a fact about the data. The cleaner config says *"when merging,
use a gap of 1 day."* That is an analytical decision. These are
different concerns and live in different places.

Keeping semantics thin means they can be defined once, saved to YAML,
versioned with the analysis, and shared across multiple data objects
without any risk of side effects.