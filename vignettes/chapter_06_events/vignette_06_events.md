# Chapter 6 — Event Analysis

## Vignette: ED Visit Volume and Coverage Interaction

You have cleaned Medicaid coverage records and a file of emergency
department visits. Two questions:

1. *"How many ED visits did members have during calendar year 2022?"*
2. *"Where in their coverage structure did those visits fall?"*

The first question asks about events. The second asks about the
relationship between events and episodes. Both questions live in the
same `CohortTimeline` — but they require different analyzers.

---

### The problems

**Problem 1 — Events need the same cleaning guarantees as episodes.**
Null IDs, unparseable dates, exact duplicates. The pipeline is simpler
but the guarantees must be the same. An unvalidated event file is as
dangerous as an unvalidated episode file.

**Problem 2 — Same-date same-hospital records are not duplicates.**
Two records for the same patient, same date, same hospital but
different diagnoses or blood pressure readings are the same visit
recorded twice. The cleaner needs to consolidate them. The aggregation
rule belongs in a config file, not a groupby lambda.

**Problem 3 — Coverage episodes define the cohort, not the filter.**
The observation period is built from the coverage cohort. ED visits are
filtered to that window — not to coverage periods specifically. A member
with a gap in coverage who visits the ED during that gap is still in
the analysis. The coverage episodes tell you the window. The events
tell you what happened inside it.

**Problem 4 — The cross-type question requires both objects assembled.**
"How many members visited the ED during a coverage gap?" cannot be
answered from either data object alone. It requires both, in the same
validated structure, with a single analyzer call. In a script, this
requires a custom join, manual gap computation, and careful date
arithmetic — and the result is an unvalidated DataFrame with no
denominator guarantees.

---

> ### The script-based alternative
>
> The without-eventus script is at
> `vignettes/without_eventus/without_eventus_events.py`.
> It required **97 lines** for the calendar year volume analysis alone
> and produced correct output. The cross-type question was not
> implemented — it would require significant additional join logic.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Cleans the data | ✓ | ✓ | ~50 lines vs ~5 lines |
> | Per-row audit trail | ✓ | ✓ | Coded manually vs included at no cost |
> | Consolidation of descriptors | ✓ | ✓ | Hardcoded groupby vs one YAML section |
> | Aggregation rules versioned | ✗ | ✓ | Hardcoded lambdas vs `icd10_condition: unique` |
> | Denominator validated | ✗ | ✓ | Manual tracking vs validated at construction |
> | Cross-type question | ✗ | ✓ | Not implemented vs one analyzer call |
> | Age window analysis | ✗ | ✓ | ~75 more lines vs change one constructor call |

---

## The eventus solution

### Step 1 — Clean the ED visits

```python
raw_df    = pd.read_csv("vignettes/data/ch01_06_ed_visits.csv")
sem       = eventus.EventSemantics.build_from_yaml("configs/ed_semantics.yaml")
config    = eventus.EventsCleanerConfig.build_from_yaml("configs/ed_cleaner_with_consolidation.yaml")
cleaner   = eventus.EventsCleaner(raw_df, sem, config)
ed_visits = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report — events
────────────────────────────────────────────────────────
Total input rows:                                5,459
────────────────────────────────────────────────────────
  Rejected:
    duplicate_row:                            1,907   (34.9%)
    null_date:                                  108   (2.0%)
    null_entity_id:                              54   (1.0%)
────────────────────────────────────────────────────────
Total rejected:                               2,069   (37.9%)
Consolidated into other events:                  35   (0.6%)
Clean rows:                                   3,355   (61.5%)
  (clean rows are consolidated events)
```

### Step 2 — Build the observation period from the coverage cohort

```python
obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = cov_episodes.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)
```

The observation period is defined by the coverage cohort — 793 members
with at least one coverage record. This is the denominator for all
downstream statistics.

### Step 3 — Assemble CohortTimeline with both data types

```python
ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes   = cov_episodes,
    events     = ed_visits,
)
```

```
CohortTimeline(
  entities             : 793
  has_obs_period       : True
  episode_identities   : ['medicaid_coverage']
  event_identities     : ['ed_visit']
)
```

Both data types are in the same validated structure.
`episode_identities` and `event_identities` are tracked separately —
the timeline knows what it holds. This is not a join. The coverage
episodes and ED visits were validated independently and assembled here.

### Step 4 — Event volume

```python
analyzer      = eventus.CohortTimelineEventAnalyzer(ct, "ed_visit")
volume_result = analyzer.compute_volume()
print(volume_result)
```

```
EventResultVolume:
  identity        : ed_visit
  entity_col      : patient_id
  entities        : 793
  n_with_any      : 554 (69.9%)
  n_with_multiple : 325 (41.0%)
```

```
ED visit volume distribution — 2022 cohort:
  0 visits     :  239  (30.1%)
  1 visit      :  229  (28.9%)
  2 visits     :  162  (20.4%)
  3 visits     :  106  (13.4%)
  4 visits     :   47  (5.9%)
  5 visits     :    8  (1.0%)
  6 visits     :    2  (0.3%)
```

### Step 5 — Where in the coverage structure did visits fall?

```python
interaction_analyzer = eventus.EpisodeEventInteractionAnalyzer(
    ct, "medicaid_coverage", "ed_visit"
)
interaction_result = interaction_analyzer.compute_interaction()
print(interaction_result)
```

```
EpisodeEventInteractionResult:
  episode_identity : medicaid_coverage
  event_identity   : ed_visit
  entity_col       : patient_id
  entities         : 793
  with episodes    : 793 (100.0%)
  without episodes : 0 (0.0%)
  events before first episode  : 61 entities (7.7%)
  events during active episodes: 509 entities (64.2%)
  events during gaps           : 19 entities (2.4%)
  events after last episode    : 60 entities (7.6%)
```

This question was not answerable from either data object alone. It
required both, assembled in the same `CohortTimeline`, with one
analyzer call. 2.4% of members visited the ED during a coverage gap —
a finding that would require a custom join and manual gap computation
in a script, and would still produce an unvalidated result with no
denominator guarantees.

Note that the percentages do not add to 100% — a single member can
appear in multiple segments. A member who visited before enrollment,
during coverage, and during a gap contributes to three counts. The
segments are distinct; the members are not.

---

## Bonus A — Plot the distribution

```python
vol_config = eventus.EventResultVolumeConfig.build_from_yaml(
    "configs/ed_visit_volume_config.yaml"
)
plotter = eventus.EventResultVolumePlotter(volume_result, vol_config)

plotter.plot_prevalence_bar("output/ed_visit_prevalence.png")
plotter.plot_count_distribution_bar("output/ed_visit_count_distribution.png")
```

---

## Bonus B — The same question for ages 18-21

One constructor call changes the observation window. The pipeline
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
EventResultVolume:
  identity        : ed_visit
  entity_col      : patient_id
  entities        : 800
  n_with_any      : 514 (64.2%)
  n_with_multiple : 382 (47.8%)
```

| | Calendar 2022 | Ages 18-21 |
|---|---|---|
| Entities in window | 793 | 800 |
| Any ED visit | 554 (69.9%) | 514 (64.2%) |
| Multiple ED visits | 325 (41.0%) | 382 (47.8%) |
| Total ED visits in window | 1,111 | 1,446 |

---

## What this demonstrated

- **Events get the same cleaning guarantees as episodes** — validated
  output, per-row audit trail, versioned consolidation rules.

- **The `CohortTimeline` holds both data types** — coverage episodes
  define the cohort and observation window; ED visits are what you
  analyze. The coverage layer is not a filter on the events. It defines
  who is in the study and for how long.

- **`EpisodeEventInteractionAnalyzer` closes the design space** — this
  is the final permutation of the three core object types:
  Events × ObsPeriod, Episodes × ObsPeriod, Events × Events, and now
  Events × Episodes. Each permutation has a dedicated analyzer. The
  architecture was designed for this from the start.

- **The cross-type question is one call** — "how many members visited
  the ED during a coverage gap?" required no join, no manual gap
  computation, no denominator tracking. The answer is in the result
  object with validated counts per segment.

- **One constructor call changes the scientific question** — the 2022
  calendar analysis and the 18-21 age window analysis share the same
  pipeline. One constructor call separated them.

---

*The next chapter examines event timing and shape — when do
ED visits happen, and does the pattern differ by condition?*
