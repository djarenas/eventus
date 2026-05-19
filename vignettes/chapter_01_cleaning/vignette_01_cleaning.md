# Chapter 1 — The Data Problem

## Vignette: Cleaning Hospitalization Claims

You are a clinical researcher studying the relationship between
hospitalizations and subsequent emergency department visits in a
Medicaid population. Your institution's data warehouse gives you a
hospitalization file — one row per claim, not one row per
hospitalization.

Before you can ask any scientific question, you need to answer a more
mundane one: *"Do I know how many times each patient was hospitalized?"*
This sounds simple. It is not.

Your file has 11,500 rows and 499 unique patients.

---

### The six problems

**Problem 1 — Duplicate claims.** A single 5-day hospitalization
generates multiple rows — one per billing day, one per diagnosis code,
one per provider. You have 11,500 rows but far fewer actual visits.

**Problem 2 — Overlapping stays.** A patient transferred between units
generates two overlapping intervals. Counting rows overestimates their
hospitalization burden.

**Problem 3 — Missing dates and identifiers.** 3% of rows have a null
admit date. Another 1% have a null patient ID. These need to be removed
— and your IRB report will ask how many and why.

**Problem 4 — Implausible dates.** System errors produce admit dates in
1899 or 2090. A script that silently keeps these corrupts every
downstream analysis.

**Problem 5 — Same-day readmissions vs. continuous stays.** A patient
discharged Monday and readmitted Tuesday — one stay or two? The answer
depends on your research question and must be a deliberate, documented
choice.

**Problem 6 — Overlapping stays at different hospitals are not the same
event.** Patient P0023 has two overlapping records — one at Hospital A,
one at Hospital B. That is a transfer, not a duplicate. A cleaner that
merges all overlapping intervals regardless of hospital just destroyed
a clinically meaningful distinction. The hospital is part of what
defines a hospitalization episode.

---

> ### The script-based alternative
>
> To illustrate the limitations of the script-based paradigm, we asked
> a large language model to implement the same cleaning pipeline.
> The script is at
> `vignettes/without_eventus/clean_hospitalizations_no_eventus.py`.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~150 lines vs ~10 lines |
> | Per-row rejection tracking | ✓ | ✓ | Coded manually vs included at no cost |
> | Config is versioned | ✗ | ✓ | YAML file — the record of every decision |
> | Reusable on new dataset | ✗ | ✓ | Change semantics YAML — one place |
> | IRB-ready report | ✗ | ✓ | `cleaner.print_report()` — automatic |
> | Column names decoupled | ✗ | ✓ | Semantics YAML defined once, never referenced again |
> | Transfer-aware merging | ✓ | ✓ | Hardcoded groupby vs `also_defined_by` in semantics |
> | Adding a new grouping column | ✗ | ✓ | Rewrite the merge loop vs one line in semantics YAML |
> | Adding a new descriptor | ✗ | ✓ | Hardcoded logic in loop vs one line in cleaner YAML |
>
> **The structural problem is not the code quality — it is the
> paradigm.**

---

## The eventus solution

### Step 1 — Declare what the data means

The first step is not cleaning — it is declaring what your columns mean
and what defines a hospitalization episode. This lives in a YAML file.

```yaml
# configs/hospitalization_semantics.yaml

identity:        inpatient_hospitalization
entity_id_col:   patient_id
start_time_col:  admit_date
end_time_col:    discharge_date
also_defined_by:
  - hospital_id
descriptor_cols:
  icd10_condition:
    type: category
```

`also_defined_by: [hospital_id]` says: *"A hospitalization IS defined
by its hospital. Two overlapping records at different hospitals are a
transfer — different events. Two overlapping records at the same
hospital are the same episode recorded twice."*

```python
import eventus
import pandas as pd

raw_hosp_df = pd.read_csv("vignettes/data/hospitalization_claims.csv")

sem = eventus.EventSemantics.build_from_yaml("configs/hospitalization_semantics.yaml")
```

### Step 2 — Configure the cleaner

Every cleaning decision lives in a versioned YAML file.

```yaml
# configs/hospitalization_cleaner.yaml

normalize_dates:     true
coalesce_dates:      false
causality_check:     reject
parse_dates:         true
drop_duplicate_rows: true
date_floor:          "1920-01-01"
date_ceiling:        "2030-01-01"

merge:
  meaningful_gap_days: 1         # discharged Monday, readmitted Tuesday = one episode
  descriptor_cols:
    icd10_condition: unique      # collect unique conditions across merged rows
```

`meaningful_gap_days: 1` is the answer to Problem 5. `also_defined_by`
in semantics is the answer to Problem 6. Both are explicit, versioned,
and documented. A collaborator reading these files in six months knows
exactly what was decided and why.

### Step 3 — Clean

```python
config  = eventus.EventsCleanerConfig.build_from_yaml("configs/hospitalization_cleaner.yaml")
cleaner = eventus.EventsCleaner(raw_hosp_df, sem, config)
events  = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report
────────────────────────────────────────────────────────
Total input rows:                               11,500
────────────────────────────────────────────────────────
  Rejected:
    duplicate_row:                               9,434   (82.0%)
    null_start_date:                               341   (3.0%)
    null_entity_id:                                115   (1.0%)
    end_before_start_rejected:                      57   (0.5%)
    before_date_floor:                               1   (0.0%)
    after_date_ceiling:                              1   (0.0%)
────────────────────────────────────────────────────────
Total rejected:                                9,949   (86.5%)
Clean rows:                                    1,486   (12.9%)
```

Every rejected row is accounted for with an explicit reason.
To inspect them directly:

```python
cleaner.rejected   # → pd.DataFrame, one row per rejected input row
```

### Step 4 — Inspect the result

```python
print(events)
```

```
Events(
  rows             : 1,486
  unique entities  : 498
  entity_col       : 'patient_id'
  start_col        : 'admit_date'
  end_col          : 'discharge_date'
)
```

The `Events` object is validated and structurally sound. Transfers
are preserved — overlapping stays at different hospitals were never
merged. Same-hospital overlaps within a 1-day gap were merged into
single episodes. `icd10_condition` values were aggregated as unique
pipe-delimited strings across merged rows.

---

## What this demonstrated

- **Domain agnosticism** — column names defined once in
  `EventSemantics`, never referenced again.

- **Config is the methods section** — every cleaning decision in a
  versioned YAML file. The file is the reproducible record of what
  was done.

- **Auditable by design** — the rejection report is automatic. No
  manual bookkeeping. No silent failures.

- **`also_defined_by` makes merging clinically honest** — two
  overlapping records at different hospitals are a transfer, not a
  duplicate. This distinction is declared once in semantics and
  respected by the cleaner automatically.

- **~10 lines of analysis code vs ~70 without eventus** — and the
  ~70 lines still lack a versioned config, easy extensibility, and
  transfer-aware merging requires a hardcoded groupby loop.

---

*Chapter 1B — Descriptor aggregation in a nursing facility setting
shows how numeric and categorical metadata are handled during merging.
See `vignette_02_descriptor_aggregation.md`.*

*Chapter 3 — "How long were these hospitalizations?" introduces event
duration analysis. See `vignette_03_event_duration.md`.*

---

## Bonus A — Cleaning Occurrence Data

ED visit data is simpler than hospitalization data — a patient, a date,
no duration. But the same design decisions apply. An ED visit is also
defined by its hospital — a patient who visits Hospital A and Hospital B
on the same day had two visits, not one.

### The semantics

```yaml
# configs/ed_semantics.yaml

identity:        ed_visit
entity_id_col:   patient_id
date_col:        ed_visit_date
also_defined_by:
  - hospital_id
descriptor_cols:
  icd10_condition:
    type: category
  systolic_bp:
    type: numeric
```

`also_defined_by: [hospital_id]` means two records on the same date
for the same patient are only duplicates if they are at the same
hospital. Two visits to different hospitals on the same day are kept
as separate occurrences. `descriptor_cols` declares the clinical
columns — available for aggregation in Chapter 6.

### The code

```python
raw_ed_df = pd.read_csv("vignettes/data/simulated_ed_visits.csv")

sem       = eventus.OccurrenceSemantics.build_from_yaml("configs/ed_semantics.yaml")
config    = eventus.OccurrencesCleanerConfig.build_from_yaml("configs/ed_cleaner.yaml")
cleaner   = eventus.OccurrencesCleaner(raw_ed_df, sem, config)
ed_visits = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report — occurrences
────────────────────────────────────────────────────────
Total input rows:                                5,442
────────────────────────────────────────────────────────
  Rejected:
    null_entity_id:                                 54   (1.0%)
    null_date:                                     107   (2.0%)
    duplicate_row:                               3,195   (58.7%)
────────────────────────────────────────────────────────
Total rejected:                                3,356   (61.7%)
Clean rows:                                    2,086   (38.3%)
```

```python
print(ed_visits)
```

```
Occurrences(
  identity        : 'ed_visit'
  rows            : 2,086
  unique entities : 448
  entity_col      : 'patient_id'
  date_col        : 'ed_visit_date'
)
```

The without-eventus equivalent is at
`vignettes/without_eventus/without_eventus_clean_ed_visits.py`.
