# eventus

**`eventus`** is a Python framework for longitudinal cohort analysis of
entities that experience episodes and events within defined observation
periods. It addresses a gap in the scientific Python ecosystem: existing
tools handle survival analysis (`lifelines`, `pysurvival`) or general
tabular computation (`pandas`, `polars`) but neither provides a
principled, reproducible pipeline from raw clinical or administrative
data to publication-ready analytical results.

The framework is built around at least four design commitments. First, a
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
analysis, event co-occurrence statistics, and survival-style inference
in a single auditable workflow — where every decision from schema
declaration to final figure is documented, validated, and reproducible.

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
Analyzers                             — compute typed result objects
    ↓
Intermediates                         — self-describing results
    ↓
Configs + Plotters                    — reproducible, YAML-driven figures
```

---

## Quick start

```python
import eventus

# 1. Declare semantics — what your columns mean
sem = eventus.EpisodeSemantics(
    identity        = "insurance_coverage",
    entity_id_col   = "person_id",
    start_time_col  = "enrollment_start",
    end_time_col    = "enrollment_end",
    descriptor_cols = {
        "plan_type": eventus.DescriptorColConfig(type="category"),
        "premium":   eventus.DescriptorColConfig(type="numeric"),
    },
)

# 2. Load and validate data
episodes = eventus.Episodes(df, sem)

# 3. Clean with a declared config
config   = eventus.EpisodesCleanerConfig.build_from_yaml("cleaning.yaml")
cleaner  = eventus.EpisodesCleaner(episodes, config)
cleaned  = cleaner.clean()
report   = cleaner.get_report()   # structured audit of every decision

# 4. Build a CohortTimeline
ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes   = cleaned,
)

# 5. Analyze
analyzer = eventus.CohortTimelineEpisodeAnalyzer(ct, "insurance_coverage")
ct       = analyzer.enrich_with_episode_coverage()
summary  = analyzer.get_summary()

# 6. Plot — all visual decisions in a YAML file
config  = eventus.StackedTimelineConfig.build_from_yaml("timeline.yaml")
plotter = eventus.StackedTimelinePlotter(ct, config)
plotter.plot("timeline.png")
```

---

## Modules

| Module | Responsibility |
|---|---|
| `eventus.semantics` | `EpisodeSemantics`, `EventSemantics`, `DescriptorColConfig` |
| `eventus.data_objects` | `Episodes`, `Events`, `ObsPeriodPerEntity` and per-entity variants |
| `eventus.cleaners` | `EpisodesCleaner`, `EventsCleaner`, filter classes, cleaner configs |
| `eventus.intermediates` | All typed result objects — `CohortTimeline`, `EventResultVolume`, `EventCoOccurrencePresenceResult`, etc. |
| `eventus.analyzers` | `CohortTimelineEpisodeAnalyzer`, `CohortTimelineEventAnalyzer`, `EventCoOccurrenceAnalyzer`, etc. |
| `eventus.visualizers` | All plotters and their configs |
| `eventus.types` | `DateBoundary`, `EpisodeCoverageMetric` |

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

**Config is the methods section.** Every analytical and visual decision
lives in a validated, round-trippable YAML file. Hand someone a config
file and they can reproduce any result exactly.

**Concept honesty.** Each class represents exactly one real concept.
No class absorbs a neighboring concern for convenience.

---

## Citation

If you use `eventus` in your research, please cite:

> Arenas, D. et al. (2025). *eventus: A Python framework for longitudinal
> cohort analysis of episodes and events.* Journal of Statistical Software.
> (submitted)
