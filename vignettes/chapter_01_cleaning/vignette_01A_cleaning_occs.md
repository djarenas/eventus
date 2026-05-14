# Chapter 1A — Bonus A: Cleaning Occurrence Data

## Vignette: Cleaning ED Visit Records

Occurrences are point-in-time events — an entity, a date, no duration.
Cleaning them follows the same pattern as events with less complexity:
no causality to enforce, no overlaps to merge.

---

### The config file

```yaml
# configs/ed_cleaner.yaml

normalize_dates: true
parse_dates:     true
drop_duplicates: true
date_floor:      "1920-01-01"
date_ceiling:    "2030-01-01"
```

### The code

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
ed_visits = OccurrencesCleaner(raw_ed_df, sem, config).clean()
```

Same pattern. Different data type. No new concepts.

### The audit trail

```python
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
    null_date:                                     108   (2.0%)
    duplicate_row:                                 432   (8.0%)
────────────────────────────────────────────────────────
Total rejected:                                   594   (11.0%)
Clean rows:                                     4,806   (89.0%)
```

### The result

```python
print(ed_visits)
```

```
Occurrences(
  identity        : 'ed_visit'
  rows            : 4,806
  unique entities : 431
  entity_col      : 'patient_id'
  date_col        : 'ed_visit_date'
)
```

---

## What this demonstrated

- **Parallel design** — `OccurrencesCleaner` and `EventsCleaner`
  follow the same pattern. Learning one means you already know the
  other.

- **Simpler config for simpler data** — occurrences have no causality,
  no overlaps, no merging. The config is four lines. The complexity
  of the config matches the complexity of the data type.

- **Same audit trail** — `print_report()` works identically. The
  framework's guarantees apply regardless of data type.

---

*Continue to Chapter 2 — Event Duration:
`vignette_02_event_duration.md`.*
