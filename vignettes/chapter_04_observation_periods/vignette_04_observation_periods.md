# Chapter 4 — Handling Observation Periods

## Vignette: Medicaid Coverage Analysis

You have coverage records for 800 Medicaid members. Before you can
ask any scientific question — who was covered, for how long, were
there gaps — you need to answer a structural one: *"What is each
member's observation window, and what happened inside it?"*

This question has two versions. The first is simple: everyone shares
the same calendar year. The second is harder and more realistic: each
member has a different window based on their age.

---

### The problems

**Problem 1 — Coverage records are not the same as coverage within
a period.** A member may have a coverage period starting in 2021 and
ending in 2023. Their coverage in 2022 is the intersection of that
period with the observation window — not the raw record. Computing
that intersection correctly for every member requires interval
arithmetic that a simple date filter cannot provide.

**Problem 2 — Gaps, lapses, and partial coverage require careful
denominators.** "19.2% of members had gaps" means 19.2% of members
*with any coverage*. "0.0% had no coverage" means 0.0% of the full
cohort. Mixing denominators silently produces wrong statistics. A
script that computes these inline has no mechanism to enforce
denominator consistency.

**Problem 3 — Age-based windows are per-entity.** When the
observation window is each member's 18th to 21st birthday, every
member has a different start and end date. Members whose window falls
outside the data range have zero coverage. A script that applies a
single date filter silently includes or excludes them incorrectly.

**Problem 4 — The enriched CohortTimeline carries computed columns
forward.** After computing coverage statistics, those columns should
be available for every downstream step — sorting, filtering,
visualizing — without recomputing. A script that computes them inline
must recompute them every time they are needed.

---

> ### The script-based alternative
>
> We asked a large language model to implement the equivalent pipeline
> without eventus, attempting full feature parity. The resulting script
> is available at
> `vignettes/without_eventus/without_eventus_observation_periods.py`.
> It required **253 lines** and raises an `AttributeError` on real
> data: `numpy.timedelta64` objects returned from date subtraction
> do not have a `.days` attribute, causing the coverage gap calculation
> to crash at runtime. The script ran correctly during development
> but fails on the actual vignette dataset.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Filter coverage to obs period | ✓ | ✓ | ~10 lines vs 1 line |
> | Clip overlapping intervals | ✓ | ✓ | ~15 lines vs included |
> | Coverage stats per member | ✓ | ✓ | ~80 lines with Python loop vs included |
> | Three-tier summary | ✓ | ✓ | ~30 lines, denominators tracked manually |
> | Denominator validation | ✗ | ✓ | Silent wrong stats vs validated tiers |
> | Age-based per-entity window | ✓ | ✓ | ~40 lines vs 1 constructor call |
> | Feb 29 birthday handling | ✓ | ✓ | Explicit try/except vs handled automatically |
> | Out-of-window members handled | ✓ | ✓ | Explicit logic vs automatic |
> | Bad input validation | ✗ | ✓ | No pre-analysis checks vs cleaner as required gate |
> | Per-row audit trail | ✗ | ✓ | Aggregate counts only vs `cleaner.rejected` |
> | Specific errors raised | ✗ | ✓ | `AttributeError` on `numpy.timedelta64.days` vs raises with actionable message |
> | Structured result object | ✗ | ✓ | Printout only vs `EpisodeCoverageSummary` |
> | Enriched columns carry forward | ✗ | ✓ | Recompute every time vs `ct_enriched` |
>
> **253 lines vs ~35 lines with eventus.** The script produces correct
> output but has no structured result object, no validated denominators,
> and raises an `AttributeError` at runtime on the actual vignette
> dataset — the script does not complete successfully.
>
> *This script is not meant to be optimized — it is meant to be honest.
> The point is not the line count. It is what the lines are doing and
> what they are missing. For production use, use eventus.*

---

## The eventus solution — Main: Calendar Year 2022

### Step 1 — Clean

```python
raw_df  = pd.read_csv("vignettes/data/ch04_06_medicaid_coverage.csv")
sem     = eventus.EpisodeSemantics.build_from_yaml("configs/medicaid_coverage_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml("configs/medicaid_coverage_cleaner.yaml")
cleaner = eventus.EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()
cleaner.print_report()
```

```
Cleaning report
────────────────────────────────────────────────────────
Total input rows:                               982
────────────────────────────────────────────────────────
  Rejected:
    duplicate_row:                               28   (2.9%)
    null_start_date:                              9   (0.9%)
────────────────────────────────────────────────────────
Total rejected:                                  37   (3.8%)
Clean rows:                                     945   (96.2%)
```

### Step 2 — Define the observation period

```python
obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = episodes.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)
print(obs)
```

```
ObsPeriodPerEntity(
  identity           : 'calendar_2022'
  construction_path  : 'construct_from_calendar'
  entity_col         : 'patient_id'
  total_entities     : 793
  period_length_mean : 364.0 days
  earliest_start     : 2022-01-01
  latest_end         : 2022-12-31
)
```

Every member has the same 365-day window. The `construction_path`
attribute records how this object was built — part of the audit trail.

### Step 3 — Filter and assemble

```python
episodes = eventus.EpisodesFilter(episodes).to_obs_period(obs, clip=True).result

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes   = episodes,
)
```

### Step 4 — Enrich with coverage analysis

```python
analyzer    = eventus.CohortTimelineEpisodeAnalyzer(ct, "medicaid_coverage")
ct_enriched = analyzer.enrich_with_episode_coverage()
```

`enrich_with_episode_coverage()` adds seven computed columns to the
`CohortTimeline`. These columns are now part of the object — available
for sorting, filtering, and visualization without recomputing:

```
eps_comp_medicaid_coverage_active_days
eps_comp_medicaid_coverage_inactive_days
eps_comp_medicaid_coverage_inactive_days_before_first_episode
eps_comp_medicaid_coverage_inactive_days_after_last_episode
eps_comp_medicaid_coverage_inactive_days_middle
eps_comp_medicaid_coverage_first_start
eps_comp_medicaid_coverage_last_end
```

### Step 5 — Coverage summary

```python
summary = analyzer.get_summary()
print(summary)
```

```
EpisodeCoverageSummary:
  identity : medicaid_coverage
  entities : 793
  coverage prevalence  (denominator: all entities)
    t1_total_entities             : 793
    t1_no_coverage                : 0 (0.0%)
    t1_any_coverage               : 793 (100.0%)
  coverage patterns    (denominator: entities with any coverage)
    t2_full_coverage              : 147 (18.5%)
    t2_entered_during_obs         : 641 (80.8%)
    t2_exited_during_obs          : 640 (80.7%)
    t2_has_middle_gaps            : 152 (19.2%)
    t2_entered_late_and_exited_early : 635 (80.1%)
    t2_entered_late_and_has_gaps  : 147 (18.5%)
    t2_exited_early_and_has_gaps  : 146 (18.4%)
  distributions        (denominator: entities with any coverage)
    t3_active_days                                 : mean=310.1  p25=313.0  p50=332.0  p75=348.0
    t3_inactive_days                               : mean=53.9   p25=16.0   p50=32.0   p75=51.0
    t3_inactive_days_before_first_episode (n=641)  : mean=22.8   p25=8.0    p50=16.0   p75=25.0
    t3_inactive_days_after_last_episode (n=640)    : mean=35.3   p25=9.0    p50=17.0   p75=25.0
    t3_inactive_days_middle (n=152)                : mean=35.9   p25=23.0   p50=36.0   p75=47.2
```

18.5% of members have full-year coverage (Jan 1 to Dec 31). The
remaining 80.8% entered after Jan 1 or exited before Dec 31, with
19.2% having gaps in the middle of their coverage period. Every tier
has an explicit denominator — these cannot be accidentally mixed.

---

## Bonus A — Age-Based Observation Periods: Ages 18-21

*"I am only interested in coverage for members between ages 18 and 21.
During those three years, what was their coverage?"*

This is the harder and more realistic question. Every member has a
different observation window — their 18th to 21st birthday. Members
whose window falls outside the data range have zero coverage.

### One constructor call changes everything

```python
demog_df = pd.read_csv("vignettes/data/ch04_07_member_demographics_age18_21.csv")

obs = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 21,
    entity_col = "patient_id",
    identity   = "age_18_to_21",
)
print(obs)
```

```
ObsPeriodPerEntity(
  identity           : 'age_18_to_21'
  construction_path  : 'construct_from_age_window(age 18→21 years)'
  entity_col         : 'patient_id'
  total_entities     : 800
  period_length_mean : 1095.8 days
  period_length_min  : 1095 days
  period_length_max  : 1096 days
  earliest_start     : 2013-01-03
  latest_end         : 2024-12-22
)
```

All 800 members are present and accounted for. The `construction_path`
attribute records that this object was built from an age window —
downstream code can inspect this without the caller having to pass
that information separately.

### The summary

```
EpisodeCoverageSummary:
  identity : medicaid_coverage
  entities : 800
  coverage prevalence  (denominator: all entities)
    t1_total_entities             : 800
    t1_no_coverage                : 249 (31.1%)
    t1_any_coverage               : 551 (68.9%)
  coverage patterns    (denominator: entities with any coverage)
    t2_full_coverage              : 164 (29.8%)
    t2_entered_during_obs         : 292 (53.0%)
    t2_exited_during_obs          : 36 (6.5%)
    t2_has_middle_gaps            : 134 (24.3%)
    t2_entered_late_and_exited_early : 27 (4.9%)
    t2_entered_late_and_has_gaps  : 48 (8.7%)
    t2_exited_early_and_has_gaps  : 0 (0.0%)
    t2_clean_entry_exit_gaps_only : 86 (15.6%)
  distributions        (denominator: entities with any coverage)
    t3_active_days                                : mean=760.0   p25=436.0   p50=931.0   p75=1095.0
    t3_inactive_days                              : mean=335.7   p25=0.0     p50=165.0   p75=659.0
    t3_inactive_days_before_first_episode (n=292) : mean=545.5   p25=273.5   p50=559.0   p75=821.2
    t3_inactive_days_after_last_episode (n=36)    : mean=340.2   p25=75.0    p50=228.0   p75=507.0
    t3_inactive_days_middle (n=134)               : mean=100.2   p25=61.2    p50=92.0    p75=125.8
```

The contrast with the main chapter is the scientific story:

| | Calendar 2022 | Age 18-21 window |
|---|---|---|
| No coverage | 0.0% | 31.1% |
| Full coverage | 18.5% | 29.8% |
| Has middle gaps | 19.2% | 24.3% |
| Mean active days | 310.1 | 760.0 |
| Mean inactive days | 53.9 | 335.7 |

31.1% of members had no Medicaid coverage during ages 18-21. Nearly
a third of those who were covered had it for the full three-year
window. The average covered member was active for about 760 days out
of 1,096 — roughly two of the three years.

---

## What this demonstrated

- **`ObsPeriodPerEntity` separates the window from the data** — the
  observation period is a first-class object, not a filter applied
  inline. It carries its construction path, its entity count, and its
  period statistics as validated properties.

- **The enriched `CohortTimeline` carries computed columns forward** —
  `enrich_with_episode_coverage()` adds seven `eps_comp_*` columns to
  the object. They are available for every downstream step without
  recomputing.

- **`EpisodeCoverageSummary` validates its denominators** — three tiers,
  each with an explicit denominator. Tier 1 uses the full cohort. Tiers
  2 and 3 use only members with any coverage. These cannot be
  accidentally mixed.

- **One constructor call changes the analytical question** — replacing
  `construct_from_calendar()` with `construct_from_age_window()` is
  the only change between the main chapter and Bonus A. The rest of
  the pipeline is identical.

- **253 lines without eventus vs ~35 lines with eventus** — and the
  253 lines raise an `AttributeError` at runtime on the actual vignette
  dataset, have no structured result object, and require manual
  denominator tracking throughout. The script does not complete.

---

*The next chapter visualizes the coverage patterns discovered
here as a stacked timeline — one bar per member.*
