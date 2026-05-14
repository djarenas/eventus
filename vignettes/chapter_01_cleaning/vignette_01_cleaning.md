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

### The five problems

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

---

> ### The script-based alternative
>
> To illustrate the limitations of the script-based paradigm, we asked
> a large language model to implement the same cleaning pipeline — drop
> nulls, enforce date bounds, enforce causality, drop duplicates, merge
> overlapping stays with a gap of 0 days. The result is representative
> of well-written ad-hoc analysis code, not a criticism of the tool
> used to generate it.
>
> **What the script produced:**
> - 61 total lines, 42 lines of actual code
> - Column names hardcoded 33 times — rename one column and it breaks
>   in multiple places
> - The `gap=0` choice buried as a `<=` inside a loop on line 40 —
>   undocumented, not configurable, invisible to a future reader
> - No count of rows dropped at each step
> - No named reason per dropped row — no audit trail
> - No errors raised on bad input — silent failures throughout
>
> Refactoring to use global constants required ~59 lines. Still no
> audit trail. Adding error transparency was estimated at ~90
> additional lines.
>
> **The structural problem is not the code quality — it is the
> paradigm.** A script couples data-cleaning logic, analytical choices,
> and column name conventions in a way that is fundamentally difficult
> to audit, reproduce, or adapt. eventus separates these concerns
> by design.

---

## The eventus solution

### The config file

Every cleaning decision lives in a versioned YAML file — not in code.
This is the documented, reproducible record of every choice made.

```yaml
# configs/hospitalization_cleaner.yaml

normalize_dates:   true
coalesce_dates:    false
causality_check:   reject
parse_dates:       true
drop_duplicates:   true
merge_overlapping: true
meaningful_gap:    1       # gaps of 1 day or less treated as continuous stays
                           # — discharged Monday, readmitted Tuesday = one episode
                           # set to 0 to treat them as separate stays
date_floor:        "1920-01-01"
date_ceiling:      "2030-01-01"
```

`meaningful_gap: 1` is the answer to Problem 5. It is explicit,
versioned, and documented in plain English. A collaborator reading
this file in six months knows exactly what was decided and why.

### The code

```python
import pandas as pd
from eventus import EventSemantics, EventsCleaner, EventsCleanerConfig

raw_hosp_df = pd.read_csv("vignettes/data/hospitalization_claims.csv")

sem    = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)

config = EventsCleanerConfig.build_from_yaml("configs/hospitalization_cleaner.yaml")
events = EventsCleaner(raw_hosp_df, sem, config).clean()
```

Three lines of analysis code. The decisions live in the YAML.

### The audit trail

```python
cleaner = EventsCleaner(raw_hosp_df, sem, config)
events  = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report
────────────────────────────────────────────────────────
Total input rows:                               11,500
────────────────────────────────────────────────────────
  Rejected:
    null_entity_id:                                115   (1.0%)
    null_start_date:                               345   (3.0%)
    before_date_floor:                               2   (0.0%)
    end_before_start_rejected:                      57   (0.5%)
    duplicate_row:                               9,437   (82.1%)
────────────────────────────────────────────────────────
Total rejected:                                9,956   (86.6%)
Clean rows (before merge):                     1,544   (13.4%)
```

Every rejected row is accounted for. The IRB report asks how many
rows were excluded and why — this is the answer, produced
automatically, without any manual bookkeeping.

To inspect the rejected rows directly:

```python
rejected = cleaner.rejected
# → pd.DataFrame — one row per rejected input row
#   _rejection_reason column, original values preserved
```

### The result

```python
print(events)
```

```
Events(
  rows             : 1,544
  unique entities  : 477
  entity_col       : 'patient_id'
  start_col        : 'admit_date'
  end_col          : 'discharge_date'
)
```

The `Events` object is validated and structurally sound. It knows
what its columns mean. If it exists, it is complete.

---

## What this demonstrated

- **Domain agnosticism** — column names are defined once in
  `EventSemantics` and never referenced again. Change `patient_id`
  to `member_id` in one place and nothing else changes.

- **Config is the methods section** — every cleaning decision lives
  in a versioned YAML file. The file is the reproducible record of
  what was done.

- **Auditable by design** — the rejection report is automatic.
  No manual bookkeeping. No silent failures.

---

*Bonus A — Cleaning occurrence data (ED visits) follows the same
pattern with even less code. See `vignette_01A_cleaning_occs.md`.*

*Chapter 2 — Event Duration asks: "How long were these
hospitalizations?" See `vignette_02_event_duration.md`.*
