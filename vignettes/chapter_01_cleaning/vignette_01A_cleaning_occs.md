# Chapter 1A — Bonus A: Cleaning Occurrence Data

## Vignette: Cleaning ED Visit Records

Occurrences are point-in-time events — an entity, a date, no duration.
Cleaning them follows the same pattern as events with less complexity:
no causality to enforce, no overlaps to merge.

---

> ### The script-based alternative
>
> Script at `vignettes/without_eventus/clean_ed_visits_no_eventus.py`.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~54 lines vs 5 lines |
> | Error reporting | ✓ | ✓ | Coded manually vs included at no cost |
> | Per-row audit trail | ✗ | ✓ | `cleaner.rejected` — one row per rejected input row |
> | Config is versioned | ✗ | ✓ | YAML file — the record of every decision |
> | Reusable on new dataset | ✗ | ✓ | Change `OccurrenceSemantics` — one place |
> | IRB-ready report | ✗ | ✓ | `cleaner.print_report()` — automatic |
> | Parallel with event cleaning | ✗ | ✓ | Same pattern — no new concepts to learn |
>
> **The structural problem is not the code quality — it is the
> paradigm.**

---

## The eventus solution

```yaml
# configs/ed_cleaner.yaml

normalize_dates: true
parse_dates:     true
drop_duplicates: true
date_floor:      "1920-01-01"
date_ceiling:    "2030-01-01"
```

```python
import pandas as pd
from eventus import OccurrenceSemantics, OccurrencesCleaner, OccurrencesCleanerConfig

raw_ed_df = pd.read_csv("vignettes/data/ed_visits.csv")

sem    = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)

config    = OccurrencesCleanerConfig.build_from_yaml("configs/ed_cleaner.yaml")
cleaner   = OccurrencesCleaner(raw_ed_df, sem, config)
ed_visits = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report — occurrences
────────────────────────────────────────────────────────
Total input rows:                                5,400
────────────────────────────────────────────────────────
  Rejected:
    null_entity_id:                                 54   (1.0%)
    null_date:                                     107   (2.0%)
    duplicate_row:                               3,254   (60.3%)
────────────────────────────────────────────────────────
Total rejected:                                3,415   (63.2%)
Clean rows:                                    1,985   (36.8%)
```

```python
print(ed_visits)
```

```
Occurrences(
  identity        : 'ed_visit'
  rows            : 1,985
  unique entities : 431
  entity_col      : 'patient_id'
  date_col        : 'ed_visit_date'
)
```

---

## What this demonstrated

- **Parallel design** — `OccurrencesCleaner` and `EventsCleaner`
  follow the same pattern. Learning one means you already know the other.

- **Simpler config for simpler data** — occurrences have no causality,
  no overlaps. The config is four lines. Complexity matches the data type.

- **Same guarantees** — `print_report()`, `cleaner.rejected`, validated
  output object. The framework's guarantees apply regardless of data type.

---

*Continue to Chapter 2 — Event Duration:
`vignette_02_event_duration.md`.*
