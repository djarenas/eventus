# cleaners

Transparent, auditable row-level cleaning pipelines for event and
occurrence data. Every decision a cleaner makes is recorded — no row
disappears without an explanation.

---

## Why cleaners are separate

Data objects enforce the "if it exists it is complete" principle —
their constructors raise on invalid data. But real data is messy.
Null dates, causality violations, duplicates, and out-of-range values
are facts of life in clinical and administrative datasets.

Cleaners bridge the gap. They accept messy raw data, apply a
configurable set of rules, and produce a validated data object. Every
rejected row is recorded with an explicit reason. The config can be
built from a YAML file and saved back to one — making every cleaning
decision explicit, stored alongside your code, and auditable later.

This separation is intentional. Data objects stay pure — they never
contain cleaning logic. Cleaners stay focused — they never contain
analytical logic. The boundary between them is the quality report.

---

## Classes

### `EventsCleanerConfig`

> *"I am a reproducible set of rules for what counts as a valid event row. I can be built from a YAML file and saved back to one — every cleaning decision is explicit, stored alongside your code, and auditable later."*

Controls every cleaning decision `EventsCleaner` makes. All parameters
have sensible defaults. Declarative construction is available through
`build_from_yaml()` to make your cleaning choices explicit and
reproducible — errors are raised if bad choices are in the YAML.

```python
from eventus import EventsCleanerConfig

# Defaults
config = EventsCleanerConfig()

# From YAML
config = EventsCleanerConfig.build_from_yaml("event_cleaner.yaml")

# Save current config to YAML
config.to_yaml("event_cleaner.yaml")
```

**Parameters**
| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `normalize_dates` | bool | True | Strip time components — keep dates only |
| `coalesce_dates` | bool | False | Fill missing start or end from the other if only one is null |
| `causality_check` | str | `"reject"` | What to do when end < start: `"reject"` or `"swap"` |
| `parse_dates` | bool | True | Auto-parse date columns from strings |
| `drop_duplicates` | bool | True | Remove rows identical across entity, start, and end |
| `merge_overlapping` | bool | False | Merge overlapping or adjacent intervals into episodes |
| `meaningful_gap` | int | 0 | Gaps ≤ this many days are bridged when merging |
| `date_floor` | str | `"1920-01-01"` | Reject rows with start before this date |
| `date_ceiling` | str | `"2100-01-01"` | Reject rows with end after this date |

**Example YAML**
```yaml
normalize_dates:   true
coalesce_dates:    false
causality_check:   reject
parse_dates:       true
drop_duplicates:   true
merge_overlapping: false
meaningful_gap:    0
date_floor:        "1920-01-01"
date_ceiling:      "2100-01-01"
```

---

### `EventsCleaner`

> *"I am a transparent, auditable pipeline that cleans raw event data and records every decision I make."*

```python
from eventus import EventsCleaner, EventsCleanerConfig, EventSemantics

sem    = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)
config = EventsCleanerConfig.build_from_yaml("event_cleaner.yaml")
events = EventsCleaner(raw_df, sem, config).clean()
```

**Cleaning pipeline order**
1. Parse dates
2. Normalize to date only
3. Reject null entity IDs
4. Reject null or unparseable dates
5. Apply causality check (reject or swap)
6. Coalesce missing start/end dates
7. Reject rows outside `date_floor` / `date_ceiling`
8. Drop exact duplicates
9. Merge overlapping intervals (if configured)

**Key methods**
```python
cleaner = EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()           # → Events
cleaner.print_report()              # prints quality report to stdout
cleaner.quality_report_df()         # → pd.DataFrame
cleaner.rejected                    # → pd.DataFrame with _rejection_reason column
```

`print_report()` requires `clean()` to be called first. It shows
total input rows, each rejection reason with count and percentage,
and the final clean row count.

---

### `OccurrencesCleanerConfig`

> *"I am a reproducible set of rules for what counts as a valid occurrence row. I can be built from a YAML file and saved back to one — every cleaning decision is explicit, stored alongside your code, and auditable later."*

Simpler than `EventsCleanerConfig` — occurrences have no causality,
no merging, no coalescing.

```python
from eventus import OccurrencesCleanerConfig

config = OccurrencesCleanerConfig()
config = OccurrencesCleanerConfig.build_from_yaml("occ_cleaner.yaml")
config.to_yaml("occ_cleaner.yaml")
```

**Parameters**
| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `normalize_dates` | bool | True | Strip time components — keep dates only |
| `parse_dates` | bool | True | Auto-parse date column from strings |
| `drop_duplicates` | bool | True | Remove rows identical across entity and date |
| `date_floor` | str | `"1920-01-01"` | Reject rows with date before this value |
| `date_ceiling` | str | `"2100-01-01"` | Reject rows with date after this value |

**Example YAML**
```yaml
normalize_dates: true
parse_dates:     true
drop_duplicates: true
date_floor:      "1920-01-01"
date_ceiling:    "2100-01-01"
```

---

### `OccurrencesCleaner`

> *"I am a transparent, auditable pipeline that cleans raw occurrence data and records every decision I make."*

```python
from eventus import OccurrencesCleaner, OccurrencesCleanerConfig, OccurrenceSemantics

sem    = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)
config = OccurrencesCleanerConfig.build_from_yaml("occ_cleaner.yaml")
occs   = OccurrencesCleaner(raw_df, sem, config).clean()
```

**Cleaning pipeline order**
1. Parse dates
2. Normalize to date only
3. Reject null entity IDs
4. Reject null or unparseable dates
5. Reject rows outside `date_floor` / `date_ceiling`
6. Drop exact duplicates

**Key methods**
```python
cleaner = OccurrencesCleaner(raw_df, sem, config)
occs    = cleaner.clean()           # → Occurrences
cleaner.print_report()              # prints quality report to stdout
cleaner.quality_report_df()         # → pd.DataFrame
cleaner.rejected                    # → pd.DataFrame with _rejection_reason column
```

---

## The quality report

Every cleaner produces a quality report after `clean()` is called.
This is the audit trail — every row that was removed is accounted for.
No more combing through scripts or modifying old ones to see what got
rejected and why.

```
Cleaning report — events
────────────────────────────────────────────────────────
Total input rows:                              10,000
────────────────────────────────────────────────────────
  Rejected:
    null_entity_id:                    12     (0.1%)
    unparseable_date:                  34     (0.3%)
    causality_violation:               89     (0.9%)
    before_date_floor:                  3     (0.0%)
    duplicate_row:                    201     (2.0%)
────────────────────────────────────────────────────────
Total rejected:                               339     (3.4%)
Clean rows:                                 9,661    (96.6%)
```

The config is your methods section. The quality report is your
results section. Together they make your cleaning decisions fully
reproducible and reportable.

---

## Internal utils

| File | Contains |
|---|---|
| `events_cleaner_config.py` | Config dataclass, YAML validation |
| `occurrences_cleaner_config.py` | Config dataclass, YAML validation |

All heavy lifting — overlap merging, causality checking, date
coalescing — lives in `events_utils.py` in `data_objects/`.

---

## Design note

Cleaners do not modify data in place. Each cleaning step produces a
new DataFrame, and rejected rows are collected separately. The original
raw data passed into the constructor is never mutated. This means you
can inspect `cleaner.rejected` after calling `clean()` without any
risk of losing information.

No more combing through scripts or modifying old ones to see what got rejected and why.