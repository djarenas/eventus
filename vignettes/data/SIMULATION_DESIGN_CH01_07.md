# Simulation Design — Chapters 1–7

This document describes the synthetic datasets used in the eventus
vignette series (chapters 1–7), the design decisions behind them, and
the properties each dataset was built to demonstrate. All data are
generated deterministically from a fixed seed — running
`generate_vignette_data.py` always produces identical output.

---

## Guiding principles

**Every dataset property is intentional.** Null rates, duplicate rates,
causality violations, and DOB distributions are not noise — they are
designed to trigger specific framework behaviors so the vignettes can
demonstrate them explicitly.

**Every warning that fires should be explained.** A warning that appears
silently in a vignette run is indistinguishable from a bug. The one
exception is the future-period warning in Chapter 7, which fires
deliberately on `ch04_07_member_demographics_mixed_dob.csv` as a pedagogical
demonstration. All other vignette runs use clean data and produce no
warnings.

**Null and signal simulations share the same structure.** Where a
chapter demonstrates signal detection, a null simulation (no signal)
runs alongside the signal simulation (signal present) using identical
code. The difference is in the data, not the pipeline.

---

## Shared cohort

All chapters use the same 800-member cohort: `P0001` through `P0800`.
This is intentional — an analyst working through the vignettes sees the
same patients across hospitalization, nursing facility, coverage, and
ED visit analyses. The framework assembles all of these into a single
`CohortTimeline` per member.

---

## Datasets

### `ch01_hospitalization_claims.csv`
**Used in:** Chapter 1 (episode cleaning)

10,000 raw hospitalization rows for 800 patients across 2020-2022.
Designed to contain every cleaning problem `EpisodesCleaner` handles:

| Property | Value | Purpose |
|---|---|---|
| Null patient IDs | ~1% | Tests null rejection |
| Null admit dates | ~3% | Tests null rejection |
| Causality violations | ~0.5% | Tests reject vs swap |
| Exact duplicates | ~15% | Tests deduplication |
| Overlapping stays | ~10% of patients | Tests interval merging |
| Implausible dates | 2 rows (1899, 2090) | Tests floor/ceiling enforcement |
| Billing-day rows | Multiple rows per stay | Tests that raw structure is handled |

The billing-day structure — multiple rows per stay — is realistic for
US administrative claims data, where hospitals submit one claim per
billing day rather than one claim per episode.

---

### `ch02_03_nursing_facility_assessments.csv`
**Used in:** Chapters 2 (descriptor aggregation) and 3 (duration)

Monthly assessments for 200 nursing facility residents across
Facility_A and Facility_B. Each resident has one primary stay of
60-180 days with monthly assessments; ~15% have a readmission.

| Property | Value | Purpose |
|---|---|---|
| Clinical measurements | systolic_bp, bmi, mobility_status | Demonstrates numeric vs category aggregation |
| Null rates | ~5% per column | Tests None propagation through aggregation |
| Multiple rows per stay | One per ~30 days | Tests that episode structure survives assessment flattening |
| Facility assignment | 60% A, 40% B | Enables facility-level stratification in Chapter 3 |

Clinical values drift slightly over time — BP, BMI, and mobility
worsen gradually — to produce realistic per-stay distributions.

---

### `ch04_06_medicaid_coverage.csv`
**Used in:** Chapters 4 (observation periods) and 6 (event volume)

Coverage periods for 800 members across 2021-2022 with three patterns:

| Pattern | Proportion | Description |
|---|---|---|
| Full | 15% | Exactly Jan 1 to Dec 31 — full year coverage |
| Continuous | 55% | One long period, late start or early exit |
| One gap | 20% | Two periods with a lapse between them |
| Partial | 10% | Short coverage, only part of the year |

The gap pattern is the core of the observation period chapters — it
produces meaningful variation in `obs_duration_days` and demonstrates
why the observation period must be explicitly declared rather than
inferred from the data.

---

### `ch04_07_member_demographics_mixed_dob.csv`
**Used in:** Chapter 7 (future-period warning demonstration only)

800 members with a deliberately varied DOB distribution:

| Group | DOB range | 18-21 window | Proportion |
|---|---|---|---|
| full_window | 1997-2000 | 2015-2021 | 40% |
| late_start | 2001-2004 | 2019-2025 | 30% |
| too_old | 1990-1996 | 2008-2017 | 16% |
| too_young | 2005-2008 | 2023-2029 | 14% |

The `too_young` group (DOB 2005-2008) has observation windows that
extend into the future. `ObsPeriodPerEntity.construct_from_age_window`
will warn about these. **This warning is intentional** — Chapter 7
uses this file in its first scenario to demonstrate that the warning
fires when it should, and what an analyst should do when they see it
on real data.

**Do not use this file for chapters 4-6.** Use
`ch04_07_member_demographics_age18_21.csv` instead.

---

### `ch04_07_member_demographics_age18_21.csv`
**Used in:** Chapters 4, 5, 6, and the null/signal scenarios in Chapter 7

Same 800 members, all born 1995-2003. Every 18-21 observation window
falls entirely within 2013-2024. No future periods. No warnings.

This is the correct demographics file for all analytical chapters.
The original `ch04_07_member_demographics_mixed_dob.csv` exists solely
for the Chapter 7 warning demonstration.

---

### `ch04_05_medicaid_coverage_agewindow.csv`
**Used in:** Chapters 4 (obs period construction) and 5 (timeline)

Coverage periods spread across 2018-2025 with four patterns:
continuous, one gap, two gaps, and partial. The wider date range
(vs the 2021-2022 file) is required to overlap with the 18-21 age
windows of all members.

---

### `ch01_06_ed_visits.csv`
**Used in:** Chapters 1 and 6

0-8 ED visits per patient across 2020-2022 with realistic messiness:
same-date same-hospital records (consolidation candidates), same-date
different-hospital records (must not be consolidated), exact
duplicates, null patient IDs, and null visit dates.

The `also_defined_by: [hospital_id]` field in the semantics is
demonstrated by the same-date different-hospital design — two visits
on the same day at different hospitals are distinct events, not
duplicates.

---

### `ch07_ed_visits_agewindow_null.csv` and `ch07_ed_visits_agewindow_signal.csv`
**Used in:** Chapter 7

ED visits spread across 2018-2025 (the full age-window coverage
period). Two simulations:

**Null** — all members have λ=1.0 visits/year. Condition assigned
randomly. No signal in gap distributions by condition.

**Signal** — visit rate depends on primary condition:

| Condition | λ (visits/year) |
|---|---|
| conditionA | 1.0 |
| conditionB | 1.5 |
| conditionC | 2.0 |

Condition on individual visits is assigned from the member's
`primary_condition` 80% of the time, with 20% random noise —
realistic for administrative claims where billing codes reflect the
visit context, not always the underlying condition.

The null and signal files use the same structure so identical
code runs on both. The difference is in the numbers produced,
not in the pipeline.

---

## Warnings by chapter

| Chapter | Expected warnings | Source |
|---|---|---|
| 1 | None | Clean hospitalization data |
| 2 | None | Clean nursing facility data |
| 3 | None | Clean nursing facility data |
| 4 | None | Uses `ch04_07_member_demographics_age18_21.csv` |
| 5 | None | Uses `ch04_07_member_demographics_age18_21.csv` |
| 6 | None | Uses `ch04_07_member_demographics_age18_21.csv` |
| 7 (future_dob scenario) | `UserWarning` — 14 entities period_start in future, 101 period_end in future | Deliberate — see Chapter 7 |
| 7 (null scenario) | None | Uses `ch04_07_member_demographics_age18_21.csv` |
| 7 (signal scenario) | None | Uses `ch04_07_member_demographics_age18_21.csv` |

---

## Random seeds

All generators use `numpy.random.default_rng` with offsets from a
base seed of 42:

| Dataset | Seed offset |
|---|---|
| Hospitalization | seed + 0 |
| ED visits (ch01-06) | seed + 1 |
| Nursing facility | seed + 2 |
| Medicaid coverage (2021-2022) | seed + 3 |
| Member demographics (mixed DOB) | seed + 4 |
| Medicaid coverage (age window) | seed + 5 |
| ED visits age window — null | seed + 6 |
| ED visits age window — signal | seed + 7 |
| Member demographics (age 18-21) | seed + 10 |

Seed + 10 for the clean demographics avoids collision with any future
additions at seeds + 8 and + 9.
