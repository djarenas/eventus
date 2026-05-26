# Chapter 4 — Handling Observation Periods

## Vignette: Medicaid Coverage Analysis

You have coverage records for 500 Medicaid members. Before you can
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
denominators.** "19.4% of members had gaps" means 19.4% of members
*with any coverage*. "13.6% had no coverage" means 13.6% of the full
cohort. Mixing denominators silently produces wrong statistics. A
script that computes these inline has no mechanism to enforce
denominator consistency.

**Problem 3 — Age-based windows are per-entity.** When the
observation window is each member's 18th to 25th birthday, every
member has a different start and end date. Members who turned 25
before the data starts, or who turn 18 after the data ends, have
zero-length windows. A script that applies a single date filter
silently includes or excludes them incorrectly.

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
> It required **275 lines** and still produced a pandas `UserWarning`
> from boolean indexing — a subtle bug that could silently produce
> wrong results in certain cohort configurations.
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
> | Specific errors raised | ✗ | ✓ | pandas UserWarning vs raises with actionable message |
> | Structured result object | ✗ | ✓ | Printout only vs `EpisodeCoverageSummary` |
> | Enriched columns carry forward | ✗ | ✓ | Recompute every time vs `ct_enriched` |
>
> **275 lines vs ~20 lines with eventus.** The script produces correct
> output but has no structured result object, no validated denominators,
> and a pandas warning that signals a latent correctness issue.
>
> *This script is not meant to be optimized — it is meant to be honest.
> The point is not the line count. It is what the lines are doing and
> what they are missing. For production use, use eventus.*

---

## The eventus solution — Main: Calendar Year 2022

### Step 1 — Clean

```python
raw_df  = pd.read_csv("vignettes/data/simulated_medicaid_coverage.csv")
sem     = eventus.EpisodeSemantics.build_from_yaml("configs/medicaid_coverage_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml("configs/medicaid_coverage_cleaner.yaml")
cleaner = eventus.EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()
cleaner.print_report()
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
  total_entities     : 495
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
    episodes     = episodes,
)
```

### Step 4 — Enrich with coverage analysis

```python
from eventus.analyzers import CohortTimelineEpisodeAnalyzer

analyzer    = CohortTimelineEpisodeAnalyzer(ct, "medicaid_coverage")
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

The naming convention `eps_comp_` marks these as computed episode
columns. The identity `medicaid_coverage` is carried from the
semantics object through the entire pipeline.

### Step 5 — Coverage summary

```python
summary = analyzer.get_summary()
print(summary)
```

```
EpisodeCoverageSummary:
  identity : medicaid_coverage
  entities : 495
  coverage prevalence  (denominator: all entities)
    t1_no_coverage              : 0 (0.0%)
    t1_any_coverage             : 495 (100.0%)
  coverage patterns    (denominator: entities with any coverage)
    t2_full_coverage            : 0 (0.0%)
    t2_entered_during_obs       : 480 (97.0%)
    t2_exited_during_obs        : 474 (95.8%)
    t2_has_middle_gaps          : 96 (19.4%)
  distributions        (denominator: entities with any coverage)
    t3_active_days              : mean=300.8  p25=309.5  p50=329.0  p75=339.0
    t3_inactive_days            : mean=63.2   p25=25.0   p50=35.0   p75=54.5
```

Every tier has an explicit denominator. Tier 1 uses all 495 members.
Tiers 2 and 3 use only members with any coverage. These denominators
are validated at construction — they cannot be accidentally mixed.

---

## Bonus A — Age-Based Observation Periods: Ages 18-25

*"I am only interested in coverage for 18-25 year olds. During those
seven years, what was their coverage?"*

This is the harder and more realistic question. Every member has a
different observation window. Members who turned 25 before 2018 or
turn 18 after 2025 have zero-length windows — they are outside the
study period entirely.

### One constructor call changes everything

```python
demog_df = pd.read_csv("vignettes/data/simulated_member_demographics.csv")

obs = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 25,
    entity_col = "patient_id",
    identity   = "age_18_to_25",
)
print(obs)
```

```
ObsPeriodPerEntity(
  identity           : 'age_18_to_25'
  construction_path  : 'construct_from_age_window(age 18→25 years)'
  entity_col         : 'patient_id'
  total_entities     : 500
  period_length_mean : 1,734.5 days
  period_length_min  : 0 days
  period_length_max  : 2,557 days
  earliest_start     : 2018-01-01
  latest_end         : 2025-12-31
)
```

`period_length_min: 0 days` — the out-of-window members are present
and accounted for. They are not silently dropped. They contribute to
the `t1_no_coverage` count in the summary.

The rest of the pipeline is identical to the main chapter — same
filter, same assembly, same enrichment, same summary call.

### The summary

```
EpisodeCoverageSummary:
  identity : medicaid_coverage
  entities : 500
  coverage prevalence  (denominator: all entities)
    t1_no_coverage              : 68 (13.6%)
    t1_any_coverage             : 432 (86.4%)
  coverage patterns    (denominator: entities with any coverage)
    t2_full_coverage            : 15 (3.5%)
    t2_entered_during_obs       : 228 (52.8%)
    t2_exited_during_obs        : 219 (50.7%)
    t2_has_middle_gaps          : 138 (31.9%)
  distributions        (denominator: entities with any coverage)
    t3_active_days              : mean=1,482.4  p25=986.5  p50=1,573.5  p75=2,067.2
    t3_inactive_days            : mean=1,074.3  p25=489.5  p50=983.5    p75=1,570.5
```

The contrast with the main chapter is the scientific story:

| | Calendar 2022 | Age 18-25 window |
|---|---|---|
| No coverage | 0.0% | 13.6% |
| Full coverage | 0.0% | 3.5% |
| Has middle gaps | 19.4% | 31.9% |
| Mean active days | 300.8 | 1,482.4 |
| Mean inactive days | 63.2 | 1,074.3 |

The young adult coverage story in five rows: 13.6% had no Medicaid
coverage during ages 18-25. Only 3.5% were continuously covered for
the full seven years. Nearly a third had gaps in the middle of their
coverage window. The average member was covered for about 4 years and
uncovered for about 3.

---

## What this demonstrated

- **`ObsPeriodPerEntity` separates the window from the data** — the
  observation period is a first-class object, not a filter applied
  inline. It carries its construction path, its entity count, and its
  period statistics as validated properties.

- **The enriched `CohortTimeline` carries computed columns forward** —
  `enrich_with_episode_coverage()` adds seven `eps_comp_*` columns to
  the object. They are available for every downstream step without
  recomputing. The naming convention `eps_comp_{identity}_{stat}` is
  meaningful — computed episode columns, namespaced by identity.

- **`EpisodeCoverageSummary` validates its denominators** — three tiers,
  each with an explicit denominator. Tier 1 uses the full cohort. Tiers
  2 and 3 use only members with any coverage. These cannot be
  accidentally mixed.

- **One constructor call changes the analytical question** — replacing
  `construct_from_calendar()` with `construct_from_age_window()` is
  the only change between the main chapter and Bonus A. The rest of
  the pipeline is identical. The out-of-window members are handled
  correctly and automatically.

- **275 lines without eventus vs ~20 lines with eventus** — and the
  275 lines still produced a pandas `UserWarning` signaling a latent
  correctness issue, had no structured result object, and required
  manual denominator tracking throughout.

- **Our ~20 lines do more than the 275.** The eventus version includes
  full input validation, a per-row audit trail with rejection reasons,
  causality checking, date floor/ceiling enforcement, and duplicate
  detection — all through the cleaner that runs before the first
  analysis line. The without-eventus script rebuilds a fraction of
  this inline, imperfectly, with no reuse across analyses.

- **eventus raises specific errors. The script warns or fails
  silently.** The pandas `UserWarning` in the script is not an
  exception — it continues and produces output that may be wrong.
  eventus raises at construction with a specific, actionable message
  before any data is touched. "Silent wrong output that propagates
  into downstream analyses" is the failure mode the script-based
  paradigm cannot prepisode.

- **A disclaimer on the 275-line script.** It is not meant to be
  optimized — it is meant to be honest. A more experienced pandas
  developer could condense some functions. The point is not the line
  count — it is what the lines are doing and what they are missing.
  The without-eventus script builds validated layers from scratch,
  imperfectly, inline, with no reuse. That is the paradigm problem,
  not a programmer problem. For production use, use eventus.

---

*Chapter 5 — Stacked timelines visualize the coverage patterns
discovered in this chapter. See `vignette_05_stacked_timeline.md`.*
