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
> a large language model to implement the same cleaning pipeline,
> refactored to use global constants — the fairest possible comparison.
> The script is at `vignettes/without_eventus/clean_hospitalizations_no_eventus.py`.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~90 lines vs 8 lines |
> | Error reporting | ✓ | ✓ | Coded manually vs included at no cost |
> | Per-row audit trail | ✗ | ✓ | `cleaner.rejected` — one row per rejected input row |
> | Config is versioned | ✗ | ✓ | YAML file — the record of every decision |
> | Reusable on new dataset | ✗ | ✓ | Change `EventSemantics` — one place, nothing else breaks |
> | IRB-ready report | ✗ | ✓ | `cleaner.print_report()` — automatic, no bookkeeping |
> | Column names decoupled | ✗ | ✓ | `EventSemantics` defined once, never referenced again |
>
> **The structural problem is not the code quality — it is the
> paradigm.**

---

## The eventus solution

Every cleaning decision lives in a versioned YAML file — not in code.

```yaml
# configs/hospitalization_cleaner.yaml

normalize_dates:   true
coalesce_dates:    false
causality_check:   reject
parse_dates:       true
drop_duplicates:   true
merge_overlapping: true
meaningful_gap:    1       # gaps of 1 day or less = one continuous stay
                           # set to 0 to treat next-day readmissions as separate
date_floor:        "1920-01-01"
date_ceiling:      "2030-01-01"
```

`meaningful_gap: 1` is the answer to Problem 5. Explicit, versioned,
documented in plain English.

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

config  = EventsCleanerConfig.build_from_yaml("configs/hospitalization_cleaner.yaml")
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

Every rejected row is accounted for with an explicit reason.
To inspect them directly:

```python
cleaner.rejected   # → pd.DataFrame, one row per rejected input row
```

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

---

## What this demonstrated

- **Domain agnosticism** — column names defined once in `EventSemantics`,
  never referenced again. Rename a column in one place, nothing breaks.

- **Config is the methods section** — every cleaning decision in a
  versioned YAML file. The file is the reproducible record of what
  was done.

- **Auditable by design** — the rejection report is automatic.
  No manual bookkeeping. No silent failures.

---

*Bonus A — Cleaning occurrence data (ED visits) follows the same
pattern with even less code. See `vignette_01A_cleaning_occs.md`.*

*Chapter 2 — "How long were these hospitalizations?"
See `vignette_02_event_duration.md`.*
