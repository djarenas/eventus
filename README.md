# eventus

**`eventus`** is an object-oriented Python framework for longitudinal
cohort analysis of entities that experience episodes and events within
defined observation periods. It turns messy temporal data — hospitalization
records, administrative claims, and the like — into validated, typed objects
that can be carried through analysis pipelines. Cleaners and analyzers are
fully reproducible and auditable: every cleaning and analytical decision is
declared in a versioned configuration file rather than buried in a script.
Beyond cleaning, `eventus` defines an algebra for combining event, episode,
and observation-period objects — design rules in the intermediate objects
govern how they compose. And because results are themselves typed objects,
downstream work like plotting draws on validated data without re-checking it.

## Core concepts

Three kinds of object sit at the center of `eventus`. The distinction
between them is what the whole framework is built on:

- **Event** — something that happens at a *point in time*: an emergency
  department visit, a diagnosis, a vaccination. One date.
- **Episode** — something that occupies an *interval of time*, with a start
  and an end: a hospital stay, a span of insurance coverage, a nursing-facility
  stay.
- **Observation period** — the *window during which an entity is observed*.
  It is the denominator: it defines when a person was eligible to have events
  or episodes recorded at all (e.g. the 2022 calendar year, or the window
  between someone's 18th and 21st birthdays).

An **entity** is whoever (or whatever) these belong to — a patient, a member,
a device.

### What makes up an event (or episode)

`eventus` asks you to declare, up front, what each column *means*. Every
event has four kinds of column, and the distinction between "defines" and
"describes" matters:

| Role | Question it answers | ED visit example |
|---|---|---|
| **Entity** | Who is this about? | `patient_id` |
| **Date** | When did it happen? | `ed_visit_date` |
| **Identity** | What kind of thing is it? | `ed_visit` |
| **Also defined by** | What else distinguishes one occurrence from another? | `hospital_id` — two visits on the same day at *different* hospitals are two distinct events, not a duplicate |
| **Descriptors** | What attributes describe it, without defining it? | `icd10_condition`, `systolic_bp` — extra information carried along and aggregated, but not used to tell events apart |

An **episode** is declared the same way, except it carries a *start* and an
*end* column (e.g. `admit_date` and `discharge_date`) instead of a single
date — because it spans an interval rather than marking a point.

Declaring "defines" versus "describes" explicitly is what lets `eventus`
clean and combine these objects safely: it knows that two records differing
only in a descriptor are the same occurrence, while two records differing in
a defining column are genuinely distinct.

### Is this package a good fit for you?

`eventus` is likely a good fit if you need auditable, reproducible
longitudinal analysis — especially across many datasets, or across many
reasonable analytical variations of the same study (sensitivity and
multiverse analyses), where every cleaning, analytical, and visual
decision should be declared and versioned. For a single quick exploratory
pass on one clean dataset, a direct `pandas` script may serve you better;
`eventus` trades a little upfront ceremony for guarantees, audit trails,
and reproducibility that pay off at scale.

It is not meant as a preachy way to say everyone should do things this way,
but hopefully it is a package that helps show the OOP style can be useful to
some data scientists as well.

### Not limited to claims or hospitalization data

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

## Example pipeline

`eventus` is not a fixed pipeline. Its components are typed objects that compose as your analysis needs; the flow below is *one* common arrangement, not a required sequence. Most analyses use only the pieces they need.

**Example 1 — episode duration, stratified by a descriptor.**
A single-object analysis: clean one stream, then analyze it directly. No
`CohortTimeline` needed.

```
EpisodeSemantics.build_from_yaml(...)          declare columns + identity
        ↓
EpisodesCleaner(df, semantics, config).clean()  →  Episodes   (validated, audited)
        ↓
EpisodeDurationAnalyzer(episodes,
        descriptor_cols=["facility_id"]).calc()  →  EpisodeDurationResult
        ↓
Config + Plotter                                 →  duration distribution by facility
```

**Example 2 — temporal gap timing between two event types.**
A multi-object analysis: clean two event streams independently, align them
to an observation period inside a `CohortTimeline`, then test their gap
timing against a permutation null.

```
EventSemantics + EventsCleaner(...).clean()      →  Events A   (e.g. diagnoses)
EventSemantics + EventsCleaner(...).clean()      →  Events B   (e.g. ED visits)
        ↓  EventsFilter(...).to_obs_period(obs).result   (clip both to the period)
        ↓
CohortTimeline.build_from_components(
        obs_period=obs, events=[A, B])           →  aligned, validated streams
        ↓
EventCoOccurrenceAnalyzer(ct, "A", "B")
        .compute_gaps()                          →  EventCoOccurrenceGapSummary
        ↓
EventCoOccurrenceGapAnalyzer(summary)
        .compute_test(n_permutations=500)        →  gap timing vs permutation null
        ↓
Config + Plotter                                 →  observed vs null gap distributions
```

The two flows share their early steps — declare, clean, validate — then
diverge. You assemble only the pieces an analysis needs.

### Combining objects

Once episodes, events, and an observation period are assembled into a
`CohortTimeline`, they can be analyzed *together*. The `CohortTimeline`
holds the validated, time-aligned objects and enforces the rules that let
them compose — so these pairwise analyses run without re-validating their
inputs:

| Combination | Analyzer | Produces |
|---|---|---|
| Episode × Observation period | `CohortTimelineEpisodeAnalyzer` | Coverage: active/inactive days, gaps, activity over time |
| Event × Observation period | `CohortTimelineEventAnalyzer` | Volume, timing, and shape relative to the period |
| Event × Episode | `EpisodeEventInteractionAnalyzer` | Events classified by position: before / during / in gaps / after episodes |
| Event × Event | `EventCoOccurrenceAnalyzer` | Presence, gap timing, and directionality between two event types |
| Episode × Episode | *(planned for a future release)* | — |

This small algebra of validated combinations — rather than any single
analyzer — is what the `CohortTimeline` is for.

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
- Position classification: each event labeled by where it falls relative to an entity's episodes — before the first, during an active episode, in a gap between episodes, or after the last
- Per-position counts and proportions per entity

---

## Design principles

These are the architectural choices `eventus` makes. They are what the
framework is built around. 

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

**Declarative construction through configs.** Every analytical and visual decision
can live in a validated, round-trippable YAML file. Hand someone a config
file and they can reproduce a result exactly.

**One concept per class.** Each class is designed to represent exactly one
real concept, rather than absorbing a neighboring concern for convenience.
This keeps each class aligned with the single-responsibility principle, which
makes changes easier to reason about.

---

## Citation

If you use `eventus` in your research, please cite:

> Arenas, D., & Fincato, R. (2026). *eventus: Object-Oriented Longitudinal
> Cohort Analysis with Episodes, Events, and Observation Periods.*
> arXiv preprint. [arXiv link forthcoming]
