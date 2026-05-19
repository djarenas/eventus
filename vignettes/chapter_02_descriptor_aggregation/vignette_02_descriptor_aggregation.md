# Chapter 2 — The Aggregation Problem

## Vignette: Cleaning Nursing Facility Assessment Data

You are analyzing residents of a long-term nursing facility. Each
resident has monthly clinical assessments — blood pressure, BMI, and
mobility status recorded by nursing staff. Your data warehouse gives
you one row per assessment, not one row per stay.

Before you can analyze anything, you need to collapse the assessments
into one row per resident per stay. This sounds like a groupby. It is
not that simple.

---

### The five problems

**Problem 1 — Every column needs its own aggregation rule.** BMI might
need median. Systolic BP might need mean. Mobility status is categorical
— averaging it makes no sense. A script that hardcodes these rules
buries each decision in a different line of a groupby block.

**Problem 2 — Category and numeric columns are fundamentally
different.** Nothing in a pandas script stops you from accidentally
applying `mean` to `mobility_status`. The error won't surface until
the output looks wrong — if you notice at all.

**Problem 3 — "Sequence" and "unique" are different scientific
claims.** A sequence of `independent | assisted | dependent` tells a
story of decline. A unique set `assisted | dependent | independent`
loses the order entirely. Which one did you use? If it's buried in a
lambda on line 89, your co-author cannot tell.

**Problem 4 — Changing one rule requires finding the right line.**
When your statistician asks you to use median instead of mean for
systolic BP, you go hunting through the script. When they ask you to
add a fourth column with a different rule, you add another aggregation
block. Each change is a surgery on the code.

**Problem 5 — A facility transfer is not a merged stay.** Resident
NF0023 spent 90 days at Facility A and then 60 days at Facility B.
Those are two different stays and must not be merged. The facility is
part of what defines a nursing facility stay.

---

> ### The script-based alternative
>
> Script at
> `vignettes/without_eventus/without_eventus_clean_nursing_facility.py`.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~150 lines vs ~10 lines |
> | Aggregation rules versioned | ✗ | ✓ | Hardcoded in lambda vs declared in YAML |
> | Column types declared | ✗ | ✓ | Implicit vs `DescriptorColConfig(type=...)` |
> | Type-rule validation | ✗ | ✓ | Nothing stops mean on a category column |
> | Facility-aware merging | ✓ | ✓ | Hardcoded groupby vs `also_defined_by` |
> | Adding a new descriptor | ✗ | ✓ | New aggregation block vs two lines in YAML |
> | Changing one rule | ✗ | ✓ | Find the right lambda vs change one word in YAML |
>
> **The structural problem is not the code quality — it is the
> paradigm.**

---

## The eventus solution

### Step 1 — Declare what the data means

```yaml
# configs/nursing_facility_semantics.yaml

identity:        nursing_facility_stay
entity_id_col:   resident_id
start_time_col:  admit_date
end_time_col:    discharge_date
also_defined_by:
  - facility_id
descriptor_cols:
  systolic_bp:
    type: numeric
  bmi:
    type: numeric
  mobility_status:
    type: category
```

`also_defined_by: [facility_id]` answers Problem 5 — stays at
different facilities are never merged. `descriptor_cols` declares what
each column is. That's all semantics does — it declares structure, not
behavior.

### Step 2 — Configure the aggregation

```yaml
# configs/nursing_facility_cleaner.yaml

normalize_dates:     true
coalesce_dates:      false
causality_check:     reject
parse_dates:         true
drop_duplicate_rows: true
date_floor:          "1920-01-01"
date_ceiling:        "2030-01-01"

merge:
  meaningful_gap_days: 0
  descriptor_cols:
    systolic_bp:     mean
    bmi:             median
    mobility_status: sequence
```

Every aggregation decision is here, versioned, in plain English.
`systolic_bp: mean`. `bmi: median`. `mobility_status: sequence`.

When your statistician asks for median instead of mean on systolic BP,
you change one word. When you add a fourth column, you add one line.
Six months from now this file is the answer to "how did we aggregate?"

The eventus cleaner validates that `mean` is not applied to a category
column and `sequence` is not applied to a numeric column — at
construction, before any data is touched.

### Step 3 — Clean

```python
raw_df  = pd.read_csv("vignettes/data/nursing_facility_assessments.csv")

sem     = eventus.EventSemantics.build_from_yaml("configs/nursing_facility_semantics.yaml")
config  = eventus.EventsCleanerConfig.build_from_yaml("configs/nursing_facility_cleaner.yaml")
cleaner = eventus.EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report
────────────────────────────────────────────────────────
Total input rows:                                1,016
────────────────────────────────────────────────────────
  Rejected:
    duplicate_row:                                  48   (4.7%)
────────────────────────────────────────────────────────
Total rejected:                                     48   (4.7%)
Clean rows:                                        227   (22.3%)
```

### Step 4 — Inspect the result

```python
print(events)
print(events.data[["resident_id", "facility_id",
                   "systolic_bp", "bmi", "mobility_status"]].head(3))
```

```
Events(
  rows             : 227
  unique entities  : 200
  entity_col       : 'resident_id'
  start_col        : 'admit_date'
  end_col          : 'discharge_date'
)

  resident_id facility_id  systolic_bp   bmi                                     mobility_status
0      NF0154  Facility_A       164.70  20.8  dependent | dependent | dependent | dependent | ...
1      NF0105  Facility_A       129.98  22.4  assisted | assisted | assisted | assisted | as...
2      NF0043  Facility_A       103.92  24.9  dependent | dependent | assisted | dependent | ...
3      NF0043  Facility_A       108.33  24.6                               dependent | dependent
```

Note that NF0043 appears twice — two separate stays at the same
facility. `also_defined_by` prevents merging across facilities, but
two non-overlapping stays at the same facility are kept as separate
episodes. Each is correct.

---

## What this demonstrated

- **Aggregation rules are scientific decisions** — they belong in a
  versioned config file, not buried in a groupby lambda.

- **Type declarations prevent silent errors** — declaring
  `type: numeric` or `type: category` in semantics lets the cleaner
  validate that the aggregation rule is appropriate before any data
  is touched.

- **`sequence` vs `unique` are different claims** — the order of
  mobility assessments across a stay is clinically meaningful.
  eventus makes that choice explicit and versioned.

- **~10 lines of analysis code vs ~150 without eventus** — and the
  ~150 lines have aggregation rules hardcoded across multiple lambda
  functions with no type validation and no config file.

---

*Chapter 3 — "How long were these stays?" introduces event duration
analysis. See `vignette_03_event_duration.md`.*
