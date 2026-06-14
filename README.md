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

`eventus` is likely a good fit if you need auditable, reproducible
longitudinal analysis — especially across many datasets, or across many
reasonable analytical variations of the same study (sensitivity and
multiverse analyses), where every cleaning, analytical, and visual
decision should be declared and versioned. For a single quick exploratory
pass on one clean dataset, a direct `pandas` script may serve you better;
`eventus` trades a little upfront ceremony for guarantees, audit trails,
and reproducibility that pay off at scale.

`eventus` is domain-agnostic: the same pipeline handles insurance
enrollment gaps, inpatient hospitalization coverage, vaccination
sequences, and emergency department visit patterns without modification.
It is designed for researchers who need to combine episode coverage
analysis, event statistics, and temporal co-occurrence inference in a
single auditable workflow — where every decision from schema declaration
to final figure is documented, validated, and reproducible.

---

## Status

**eventus is v0.1 (alpha) and in active development.** It installs, runs, and
the ten vignettes reproduce their published results — but the API is still
stabilizing and may change between 0.x releases. It is ready to use and to
build on; it is not yet frozen.

The design — validated typed objects, the layered pipeline, and the composable
algebra over episodes and events — is stable. Currently staged for upcoming
releases:

- Bootstrap confidence intervals for co-occurrence measures (analytical CIs available now)
- Episode–episode interaction analyzers, completing the pairwise algebra
- Sequential-dependency analysis (Markov-chain characterization of event ordering)
- Descriptor-based filtering and interactive visualization
- Nearest-neighbor event-to-episode gap statistics (accounting for both episode start and end); the current `EpisodeEventInteractionAnalyzer` computes position classification only

Issues, use cases, and contributions are warmly welcomed.

---

## Installation

Once published to PyPI:

```bash
pip install eventus
```

Until then, install the latest from source:

```bash
pip install git+https://github.com/djarenas/eventus.git
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
EpisodeEventInteractionAnalyzer       — event–episode temporal relationships
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

# 2. Clean raw data with a declared config
#    (the cleaner takes the raw DataFrame + semantics; it returns a
#     validated Episodes object)
config  = eventus.EpisodesCleanerConfig.build_from_yaml("cleaning.yaml")
cleaner = eventus.EpisodesCleaner(df, sem, config)
cleaned = cleaner.clean()         # -> validated Episodes object

cleaner.print_report()            # human-readable audit of every decision
report   = cleaner.calc_report()  # same audit as a structured dict
rejected = cleaner.rejected       # DataFrame of every rejected row + reason
modified = cleaner.modified       # DataFrame of every repaired row

# 3. Build a CohortTimeline
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

These are the architectural choices `eventus` makes. They are what the
framework is built around — offered as a coherent way to structure this
kind of analysis, not as a verdict on how everyone must work.

**Semantics first.** Every column is given a declared role before any
computation begins. The semantics object acts as the contract between
your data schema and the framework.

**Validation at construction.** `eventus` objects validate themselves
when built, so a constructed object can be trusted by everything
downstream. Errors surface immediately, with messages that show the
correct structure rather than just rejecting the wrong one.

**Nothing happens silently.** Cleaners report what they did. NaN values in
results carry meaning — absent signal, not missing data — and every
transformation is recorded in an audit trail you can read.

**Typed results over enriched DataFrames.** Analytical results are
first-class objects with documented columns, properties, and a meaningful
`__repr__`. The column-naming problem
(`evt_ed_visit_n_co_occurrences_within_7_specialist_referral`) goes away
when results carry their own context.

**Two-tier co-occurrence analysis.** `EventCoOccurrenceAnalyzer` produces
per-entity summaries. Second-level analyzers (`EventCoOccurrenceGapAnalyzer`,
`EventCoOccurrenceDirectionalityAnalyzer`) take those summaries and add
statistical testing against a permutation null. The tiers are independent
— the summary is useful on its own, and the test is a separate concern.

**Config as the methods section.** Every analytical and visual decision
can live in a validated, round-trippable YAML file. Hand someone a config
file and they can reproduce a result exactly.

**One concept per class.** Each class is designed to represent exactly one
real concept, rather than absorbing a neighboring concern for convenience.

---

## Citation

If you use `eventus` in your research, please cite:

> Arenas, D., & Fincato, R. (2026). *eventus: Object-Oriented Longitudinal
> Cohort Analysis with Episodes, Events, and Observation Periods.*
> arXiv preprint. [arXiv link forthcoming]
