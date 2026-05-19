# Chapter 6 — Occurrence Analysis

## Vignette: ED Visit Volume in a Medicaid Cohort

You have cleaned Medicaid coverage records and a file of emergency
department visits. You want to know: *"How many ED visits did members
have during their coverage period — and how does that change when you
restrict to the ages 18-21 transition window?"*

This is the first chapter where two data types appear in the same
pipeline — events (coverage periods) and occurrences (ED visits).
The `CohortTimeline` holds both. The analyzer asks one of them a
question.

---

### The five problems

**Problem 1 — Occurrences need the same cleaning guarantees as
events.** Null IDs, unparseable dates, exact duplicates. The pipeline
is simpler but the guarantees must be the same.

**Problem 2 — Same-date same-hospital records are not duplicates.**
Two records for the same patient, same date, same hospital but
different diagnoses or blood pressure readings are the same visit
recorded twice — not two visits. The cleaner needs to consolidate
them. The aggregation rules belong in a config file, not a groupby
lambda.

**Problem 3 — The observation period determines what counts.**
An ED visit on March 15 may or may not fall within a member's 18-21
window. The observation period is a first-class object that defines
what counts for each member individually — not a date filter applied
after the fact.

**Problem 4 — Volume statistics need correct denominators.**
"68.5% of members had any ED visit" uses 495 as the denominator.
"67.4% had any ED visit during ages 18-21" uses 500. Different
questions, different denominators. A script must track these manually.
eventus validates them at construction.

**Problem 5 — Changing the observation period should not require
rewriting the analysis.** The calendar year and the age window
analysis are the same pipeline. One constructor call should change
the scientific question.

---

> ### The script-based alternative
>
> The without-eventus script is at
> `vignettes/without_eventus/without_eventus_occurrences.py`.
> It required **~99 lines** for the calendar year analysis and
> produced a pandas `UserWarning` — the same silent correctness risk
> seen in Chapter 4.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~50 lines vs ~5 lines |
> | Per-row audit trail | ✓ | ✓ | Coded manually vs included at no cost |
> | Consolidation of descriptors | ✓ | ✓ | Hardcoded groupby vs one YAML section |
> | Aggregation rules versioned | ✗ | ✓ | Hardcoded lambdas vs `icd10_condition: unique` |
> | Correct denominator | ✓ | ✓ | Requires loading coverage file separately |
> | Denominator validated | ✗ | ✓ | Manual tracking vs validated at construction |
> | Structured result object | ✗ | ✓ | Printout only vs `OccurrenceResultVolume` |
> | Raises on bad input | ✗ | ✓ | pandas UserWarning vs specific error message |
> | Age window analysis | ✗ | ✓ | ~75 more lines vs change one constructor call |
>
> **~99 lines for the calendar year analysis. ~175 lines estimated for
> both analyses combined.** With eventus, Bonus B is 8 additional
> lines — the only change is the `ObsPeriodPerEntity` constructor.

---

## The eventus solution

### Step 1 — Declare what the data means

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

`also_defined_by: [hospital_id]` — two visits on the same date at
different hospitals are different events. `descriptor_cols` declares
the clinical columns available for consolidation.

### Step 2 — Configure the cleaner

```yaml
# configs/ed_cleaner_with_consolidation.yaml

normalize_dates:     true
parse_dates:         true
drop_duplicate_rows: true
date_floor:          "1920-01-01"
date_ceiling:        "2030-01-01"

consolidate:
  descriptor_cols:
    icd10_condition: unique
    systolic_bp:     median
```

`consolidate` declares what to do with same-date same-hospital
records. `icd10_condition: unique` collects all unique diagnoses
across the visit records. `systolic_bp: median` takes the median
blood pressure measurement. These are the scientific decisions — they
belong in a versioned config file.

### Step 3 — Clean

```python
raw_df    = pd.read_csv("vignettes/data/simulated_ed_visits.csv")
sem       = eventus.OccurrenceSemantics.build_from_yaml("configs/ed_semantics.yaml")
config    = eventus.OccurrencesCleanerConfig.build_from_yaml("configs/ed_cleaner_with_consolidation.yaml")
cleaner   = eventus.OccurrencesCleaner(raw_df, sem, config)
ed_visits = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report — occurrences
────────────────────────────────────────────────────────
Total input rows:                                5,442
────────────────────────────────────────────────────────
  Rejected:
    duplicate_row:                               3,195   (58.7%)
    null_date:                                     107   (2.0%)
    null_entity_id:                                 54   (1.0%)
────────────────────────────────────────────────────────
Total rejected:                                3,356   (61.7%)
Clean rows:                                    2,060   (37.9%)
  (after consolidation)
```

### Step 4 — Assemble CohortTimeline with both data types

```python
ct = eventus.CohortTimeline.build_from_components(
    obs_period  = obs,
    events      = cov_events,
    occurrences = ed_visits,
)
print(ct)
```

```
CohortTimeline(
  entities             : 495
  has_obs_period       : True
  event_identities     : ['medicaid_coverage']
  occurrence_identities: ['ed_visit']
)
```

This is the first time both data types appear in the same timeline.
`event_identities` and `occurrence_identities` are tracked separately
— the timeline knows what it holds.

### Step 5 — Compute volume and enrich

```python
analyzer      = eventus.CohortTimelineOccurrenceAnalyzer(ct, "ed_visit")
volume_result = analyzer.compute_volume()
print(volume_result)
```

```
OccurrenceResultVolume:
  identity         : ed_visit
  entity_col       : patient_id
  entities         : 495
  n_with_any       : 339 (68.5%)
  n_with_multiple  : 199 (40.2%)
```

```python
ct_enriched = analyzer.enrich_with_volume()
```

The enriched `CohortTimeline` now carries `occ_comp_ed_visit_n` for
every member — available for downstream filtering, sorting, and
visualization without recomputing.

### Step 6 — Volume distribution

```
ED visit volume distribution — 2022 cohort:
  0 visits     :  156  (31.5%)
  1 visit      :  140  (28.3%)
  2 visits     :   94  (19.0%)
  3 visits     :   70  (14.1%)
  4 visits     :   31  (6.3%)
  5 visits     :    3  (0.6%)
  6 visits     :    1  (0.2%)
```

---

## Bonus A — Plot the distribution

Two plot calls from the validated `OccurrenceResultVolume` object.
Every visual decision is versioned in `ed_visit_volume_config.yaml`.

```python
vol_config = eventus.OccurrenceResultVolumeConfig.build_from_yaml(
    "configs/ed_visit_volume_config.yaml"
)
plotter = eventus.OccurrenceResultVolumePlotter(volume_result, vol_config)

plotter.plot_prevalence_bar("output/ed_visit_prevalence.png")
plotter.plot_count_distribution_bar("output/ed_visit_count_distribution.png")
```

---

## Bonus B — The same question for ages 18-21

*"How many ED visits did members have between ages 18 and 21?"*

One constructor call changes the scientific question. Everything else
is identical.

```python
obs_age = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 21,
    entity_col = "patient_id",
    identity   = "age_18_to_21",
)
```

```
ObsPeriodPerEntity(
  identity           : 'age_18_to_21'
  construction_path  : 'construct_from_age_window(age 18→21 years)'
  total_entities     : 500
  period_length_mean : 1,095.7 days
  period_length_min  : 1,095 days
  period_length_max  : 1,096 days
  earliest_start     : 2008-01-11
  latest_end         : 2029-12-25
)
```

Note that `latest_end: 2029-12-25` — some members' 21st birthday falls
after today. The package warns rather than silently accepting:

```
UserWarning: [ObsPeriodPerEntity] 66 entities have span_end in the
future. Example entity IDs: ['P0001', 'P0005', ...]. Is this
intentional (prospective study)?
```

This is a warning, not an error — a prospective study is valid. The
package surfaces the decision rather than hiding it.

```
OccurrenceResultVolume:
  identity         : ed_visit
  entity_col       : patient_id
  entities         : 500
  n_with_any       : 337 (67.4%)
  n_with_multiple  : 243 (48.6%)
```

### The contrast

| | Calendar 2022 | Ages 18-21 |
|---|---|---|
| Entities in window | 495 | 500 |
| Any ED visit | 339 (68.5%) | 337 (67.4%) |
| Multiple ED visits | 199 (40.2%) | 243 (48.6%) |
| Total ED visits in window | 683 | 872 |

**48.6% of members had multiple ED visits between ages 18-21** —
nearly half. The transition into young adulthood is associated with
higher repeat ED utilization than a single calendar year suggests.

The pipeline that produced both of these results is the same pipeline.
One constructor call separated the two analyses.

---

## What this demonstrated

- **`OccurrencesCleaner` provides the same guarantees as `EventsCleaner`**
  — validated output, per-row audit trail, auditable config. The
  parallel design means everything learned in Chapter 1 applies here.

- **Consolidation is a scientific decision** — `icd10_condition: unique`
  and `systolic_bp: median` are declared in the cleaner config, not
  hardcoded in a groupby lambda. Change one word to change the rule.

- **`CohortTimeline` holds both data types** — `event_identities` and
  `occurrence_identities` are tracked separately. The timeline knows
  what it contains.

- **`OccurrenceResultVolume` validates its denominators** — `n_with_any`
  and `n_with_multiple` are properties of a validated object, not
  manual groupby operations. They cannot be accidentally computed
  against the wrong denominator.

- **One constructor call changes the scientific question** — replacing
  `construct_from_calendar()` with `construct_from_age_window()` is
  the only difference between the 2022 analysis and the 18-21 analysis.
  The rest of the pipeline is identical.

- **The package warns on future dates** — when observation windows
  extend past today, the package warns explicitly rather than silently
  accepting. The researcher decides whether this is intentional.

---

*Chapter 7 — Occurrence timing and shape analysis: when do ED visits
happen relative to enrollment, and are they bursty or regular?
See `vignette_07_occurrence_shape.md`.*
