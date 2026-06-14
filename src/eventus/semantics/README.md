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

Any object that receives a semantics attribute can use it during
construction to verify that the expected column names exist in the
DataFrame and are the right type — catching schema mismatches early
with a clear error message.

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

**`timeline`** — how values are carried into `CohortTimeline`

| type | valid `timeline` values | default |
|---|---|---|
| `"category"` | `"sequence"`, `"unique"`, `"none"` | `"sequence"` |
| `"numeric"` | `"average"`, `"sequence"`, `"none"` | `"average"` |

- **`"sequence"`** — pipe-delimit values in visit order, preserving repetition. Use when order or frequency matters (e.g. a mobility decline pattern: `"independent | assisted | dependent"`).
- **`"unique"`** — collect all values, deduplicate, sort alphabetically. Use when you only care what categories appeared, not how many times or in what order (e.g. stratifying by condition: `"conditionA | conditionB"`).
- **`"average"`** — compute the mean across visits and carry a single float. Use when you want a per-member summary value (e.g. mean systolic BP).
- **`"none"`** — do not carry into `CohortTimeline`.

`"unique"` is not valid for numeric columns. `"average"` is not valid for category columns.

```python
DescriptorColConfig(type="category")                      # sequence (default)
DescriptorColConfig(type="category", timeline="unique")   # e.g. for ICD-10 stratification
DescriptorColConfig(type="numeric")                       # average (default)
DescriptorColConfig(type="numeric", timeline="sequence")  # e.g. to track BP trend over visits
```

---

### `EpisodeSemantics`

> *"I am a description of what columns mean in episode data. I hold no data and do no computation."*

```python
from eventus import EpisodeSemantics
from eventus.semantics import DescriptorColConfig

sem = EpisodeSemantics(
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
| `identity` | str \| None | | What kind of episodes these are. Flows into intermediate column names and plot titles. Letters, numbers, underscores only. |
| `entity_id_col` | str | ✓ | Column identifying the entity |
| `start_time_col` | str | ✓ | Column for episode start date |
| `end_time_col` | str | ✓ | Column for episode end date |
| `also_defined_by` | list[str] \| None | | Columns that are part of the episode's identity — see below |
| `descriptor_cols` | dict[str, DescriptorColConfig] \| None | | Columns that describe the episode — see below |
| `episode_id_col` | str \| None | | Column for a unique episode identifier |
| `episode_type_col` | str \| None | | Column for episode type or category |

---

### `EventSemantics`

> *"I am a description of what columns mean in event data. I hold no data and do no computation."*

```python
from eventus import EventSemantics
from eventus.semantics import DescriptorColConfig

sem = EventSemantics(
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
| `identity` | str \| None | | What kind of events these are |
| `entity_id_col` | str | ✓ | Column identifying the entity |
| `date_col` | str | ✓ | Column for the event date |
| `also_defined_by` | list[str] \| None | | Columns that are part of the event's identity — see below |
| `descriptor_cols` | dict[str, DescriptorColConfig] \| None | | Columns that describe the event — see below |
| `event_id_col` | str \| None | | Column for a unique event identifier |

---

## `also_defined_by` — what makes this episode unique

`also_defined_by` answers the question: *"Beyond entity and date, what
else defines whether two records are the same episode?"*

This is one of the most important design decisions in any interval or
event analysis. It determines what the cleaner treats as a
duplicate, and what it refuses to merge.

### Episodes example — hospitalizations

A hospitalization is defined by patient + admit date + discharge date.
But if your data has transfers between hospitals, a patient may have
two overlapping records at different hospitals. Are those the same
hospitalization?

**No.** A hospitalization at Hospital A and a hospitalization at
Hospital B are different episodes — even if they overlap in time. The
hospital is part of what defines the episode.

```python
EpisodeSemantics(
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

### Events example — ED visits

An ED visit is defined by patient + visit date. But if your data
records visits across multiple hospitals, a patient could have two
records on the same date at different hospitals. Are those the same
visit?

**No.** A visit to Hospital A and a visit to Hospital B on the same
day are different episodes — the hospital defines the event.

```python
EventSemantics(
    identity        = "ed_visit",
    entity_id_col   = "patient_id",
    date_col        = "ed_visit_date",
    also_defined_by = ["hospital_id"],   # can't dedup across hospitals
)
```

The cleaner reads `also_defined_by` and only deduplicates records
where `hospital_id` also matches. Two visits to different hospitals
on the same date are kept as separate events.

### What `also_defined_by` is NOT

`also_defined_by` is not for columns that merely *describe* the episode.
A patient's BMI at admission describes the hospitalization — it doesn't
define it. Two records with the same patient, same admit date, same
discharge date, same hospital, but different BMI values are the same
episode recorded with different values — not two different episodes.

```python
EpisodeSemantics(
    ...
    also_defined_by = ["hospital_id"],        # ✓ defines the episode
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

## `descriptor_cols` — what describes this episode

`descriptor_cols` declares columns that carry analytical information
about the episode but are not part of its identity. They survive the
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
`EpisodesCleanerConfig.merge`, not here.

**`also_defined_by` and `descriptor_cols` must be disjoint.** A column
is either part of the episode's identity or a descriptor — never both.
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
EpisodeSemantics(..., identity="inpatient_hospitalization")
EventSemantics(..., identity="ed_visit")

# Raises ValueError
EpisodeSemantics(..., identity="inpatient hospitalization")  # spaces
EventSemantics(..., identity="ed-visit")              # hyphens
```

Identity flows into intermediate column names — `evt_ed_visit`,
`eps_comp_inpatient_hospitalization_active_days` — so it must be safe
to use as part of a column name.

---

## Build from YAML

```python
sem = EpisodeSemantics.build_from_yaml("episode_semantics.yaml")
sem = EventSemantics.build_from_yaml("event_semantics.yaml")
```

```yaml
# episode_semantics.yaml
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
# event_semantics.yaml
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
sem     = EpisodeSemantics(identity="inpatient_hospitalization", ...)
episodes  = EpisodesCleaner(raw_df, sem, config).clean()
result  = EpisodeDurationAnalyzer(episodes).calc()
```

The semantics object is preserved through filtering and copying:

```python
filtered = EpisodesFilter(episodes).by_entities(some_ids).result
filtered.semantics   # same EpisodeSemantics, unchanged
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