# eventus

**`eventus`** is a Python framework for longitudinal cohort analysis of
entities that experience episodes and events within defined observation
periods. It addresses a gap in the scientific Python ecosystem: existing
tools handle survival analysis (`lifelines`, `pysurvival`) or general
tabular computation (`pandas`, `polars`) but neither provides a
principled, reproducible pipeline from raw clinical or administrative
data to publication-ready analytical results — one that handles the full
chain from schema declaration and data cleaning through episode coverage,
event volume and timing, and temporal co-occurrence between event types.

The framework is built around four design commitments. First, a
**semantics layer** — `EpisodeSemantics` and `EventSemantics` — that does
more than map column names. It declares what *defines* an episode or event
(which columns determine identity and drive deduplication and merging
decisions), what *describes* it (descriptor columns with explicit type
declarations and carriage rules into downstream objects), and what
structural role each column plays. The same analysis code runs unchanged
across datasets with different schemas, and the semantics object is the
only place a schema decision ever needs to be made. Second, a **validated
configuration system** that governs both cleaning and visualization
decisions. `EpisodesCleanerConfig` and `EventsCleanerConfig` declare
merging strategy, overlap handling, deduplication logic, and descriptor
aggregation rules — all validated at construction, all round-trippable to
YAML. Every analytical and visual decision is versioned, shareable, and
reproducible from a plain text file. Third, a **transparent cleaning
pipeline** — cleaners produce structured audit reports documenting every
transformation decision: how many episodes were merged, what overlaps were
resolved, which duplicates were dropped. Nothing is silent. Fourth, a
**typed intermediate pipeline** — every analytical result is a validated
object with documented columns, NaN semantics, and a meaningful
`__repr__` — eliminating the column-naming fragility of enriched
DataFrames and making results self-describing at every stage of the
analysis.

`eventus` is domain-agnostic: the same pipeline handles insurance
enrollment gaps, inpatient hospitalization coverage, vaccination
sequences, and emergency department visit patterns without modification.
It is designed for researchers who need to combine episode coverage
analysis, event statistics, and temporal co-occurrence inference in a
single auditable workflow — where every decision from schema declaration
to final figure is documented, validated, and reproducible.

---

## Installation

```bash
pip install eventus
```

---

## The pipeline

```
EpisodeSemantics / EventSemantics     — declare what columns mean and
                                        what defines vs describes an event
    ↓
Episodes / Events / ObsPeriodPerEntity — validated data objects
    ↓
EpisodesCleanerConfig                 — declare cleaning decisions in YAML
EpisodesCleaner / EventsCleaner       — transform, audit, report
    ↓
CohortTimeline                        — per-entity table, one row per entity
    ↓
CohortTimelineEpisodeAnalyzer         — episode coverage, activity over time
CohortTimelineEventAnalyzer           — volume, timing, shape
EventEpisodeAnalyzer                  — event–episode temporal relationships
EventCoOccurrenceAnalyzer             — co-occurrence: presence, gaps, directionality
    ↓ (second-level analyzers for statistical testing)
EventCoOccurrenceGapAnalyzer          — gap test vs permutation null (KS test)
EventCoOccurrenceDirectionalityAnalyzer — directionality test vs permutation null
    ↓
Intermediates                         — self-describing typed result objects
    ↓
Configs + Plotters                    — reproducible, YAML-driven figures
```

---

## Quick start

### Episode coverage

```python
import eventus

# 1. Declare semantics
sem = eventus.EpisodeSemantics(
    identity        = "insurance_coverage",
    entity_id_col   = "person_id",
    start_time_col  = "enrollment_start",
    end_time_col    = "enrollment_end",
    descriptor_cols = {
        "plan_type": eventus.DescriptorColConfig(type="category"),
    },
)

# 2. Load and validate
episodes = eventus.Episodes(df, sem)

# 3. Clean with a declared config
config  = eventus.EpisodesCleanerConfig.build_from_yaml("cleaning.yaml")
cleaner = eventus.EpisodesCleaner(episodes, config)
cleaned = cleaner.clean()
report  = cleaner.get_report()   # structured audit of every decision

# 4. Build a CohortTimeline
ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes   = cleaned,
)

# 5. Analyze coverage
analyzer = eventus.CohortTimelineEpisodeAnalyzer(ct, "insurance_coverage")
ct       = analyzer.enrich_with_episode_coverage()
summary  = analyzer.get_summary()

# 6. Plot
config  = eventus.StackedTimelineConfig.build_from_yaml("timeline.yaml")
plotter = eventus.StackedTimelinePlotter(ct, config)
plotter.plot("timeline.png")
```

### Event co-occurrence

```python
# Do cirrhosis diagnoses and ED visits co-occur more than chance predicts?
# Does one tend to precede the other?

analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "cirrhosis_diagnosis",
    identity_b      = "ed_visit",
)

# Chapter 8 — presence
presence = analyzer.compute_presence()
print(presence)
# prevalence_ratio=1.71  fisher_p=1.3e-06

# Chapter 9 — gap timing
gaps     = analyzer.compute_gaps()
gap_test = eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(n_permutations=500)
print(gap_test)
# gap_ratio=0.45  ks_p=5.8e-72  (gaps 55% shorter than independence predicts)

# Chapter 10 — directionality
directionality = analyzer.compute_directionality()
dir_test       = eventus.EventCoOccurrenceDirectionalityAnalyzer(directionality).compute_test()
print(dir_test)
# fraction_a_first=74.5%  direction_ratio=1.50  wilcoxon_p=0.049
```

---

## Modules

| Module | Responsibility |
|---|---|
| `eventus.semantics` | `EpisodeSemantics`, `EventSemantics`, `DescriptorColConfig` |
| `eventus.data_objects` | `Episodes`, `Events`, `ObsPeriodPerEntity` and per-entity variants |
| `eventus.cleaners` | `EpisodesCleaner`, `EventsCleaner`, filter classes, cleaner configs |
| `eventus.intermediates` | All typed result objects — `CohortTimeline`, `EventResultVolume`, `EventCoOccurrencePresenceResult`, `EventCoOccurrenceGapSummary`, `EventCoOccurrenceGapTest`, `EventCoOccurrenceDirectionalitySummary`, `EventCoOccurrenceDirectionalityTest`, etc. |
| `eventus.analyzers` | First-level analyzers (`CohortTimelineEpisodeAnalyzer`, `CohortTimelineEventAnalyzer`, `EventCoOccurrenceAnalyzer`) and second-level statistical analyzers (`EventCoOccurrenceGapAnalyzer`, `EventCoOccurrenceDirectionalityAnalyzer`) |
| `eventus.visualizers` | All plotters and their configs — episode, event, and co-occurrence |
| `eventus.types` | `DateBoundary`, `EpisodeCoverageMetric` |

---

## What eventus computes

### Episode analysis
- Coverage: active days, inactive days, before/middle/after gaps
- Activity over time: fraction of cohort active at each timepoint, entries and exits
- Duration distributions: histogram, KDE, violin by stratum

### Event analysis
- Volume: prevalence, count distribution
- Timing: time to nth event, recency
- Shape: mean gap, burstiness, memory, density, center of mass

### Event co-occurrence (chapters 8–10)
- **Presence** — do two event types co-occur in the same observation period above chance? Prevalence ratio, Fisher's exact test, full 2×2 association table
- **Gap timing** — are events closer in time than independence predicts? Per-entity nearest-neighbor gaps, permutation null, KS test, gap ratio
- **Directionality** — does one event tend to precede the other? Per-entity mean signed gaps, permutation null, Wilcoxon signed-rank test, direction ratio

### Event–episode relationships
- Events within episodes: counts, proportions
- Nearest-neighbor gaps in both directions: event → next episode, episode discharge → next event

---

## Design principles

**Semantics first.** Every column has a declared role before any
computation begins. The semantics object is the contract between your
data schema and the framework.

**Validation at construction.** If an object exists, it is valid. Errors
surface immediately with messages that show the correct structure, not
just reject the wrong one.

**Nothing is silent.** Cleaners report what they did. NaN values in
results mean absent signal, not missing data. Every transformation is
auditable.

**Typed results over enriched DataFrames.** Analytical results are
first-class objects with documented columns, properties, and `__repr__`.
The column-naming problem (`evt_ed_visit_n_co_occurrences_within_7_specialist_referral`)
disappears when results carry their own context.

**Two-tier co-occurrence analysis.** `EventCoOccurrenceAnalyzer` produces
per-entity summaries. Second-level analyzers (`EventCoOccurrenceGapAnalyzer`,
`EventCoOccurrenceDirectionalityAnalyzer`) take those summaries and add
statistical testing against a permutation null. The tiers are independent
— the summary is useful on its own, and the test is a separate concern.

**Config is the methods section.** Every analytical and visual decision
lives in a validated, round-trippable YAML file. Hand someone a config
file and they can reproduce any result exactly.

**Concept honesty.** Each class represents exactly one real concept.
No class absorbs a neighboring concern for convenience.

---

## Citation

If you use `eventus` in your research, please cite:

> Arenas, D. et al. (2026). *eventus: A Python framework for longitudinal
> cohort analysis of episodes and events.* arXiv preprint.
> [arXiv link forthcoming]
