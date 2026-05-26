# eventus

A domain-agnostic Python framework for longitudinal cohort analysis
with episodes, events, and observation periods — object-oriented,
configuration-driven, and auditable.

Built for recurring challenges in health services research and
insurance analytics, but applicable wherever entities, time spans,
interval episodes, and point-in-time events co-exist.

> **Note:** eventus is an evolving research package released under
> the MIT License — free to use, modify, and distribute (see LICENSE).
> Its architecture aims to surface structural errors early and make
> analytical decisions auditable. It may contain bugs — please report
> them and contributions are welcome at
> https://github.com/djarenas/eventus. Scientific judgment remains
> the researcher's responsibility.

---

## The six abstractions

```
Semantics — Data Objects — Cleaners — Analyzers — Intermediates — Visualizers
```

**Semantics** — map column names to concepts. Declare what your
columns mean and what defines a unique episode or event. Define
once, reuse everywhere.

**Data Objects** — validated containers. If it exists, it is
complete. Constructors raise on invalid data — no silent failures,
no partial objects. An `Episodes` object guarantees every row has a
valid entity identifier, a start date, an end date, and that
causality holds.

**Cleaners** — transparent, auditable row-level cleaning pipelines.
Every rejected row is recorded with an explicit reason. Every
repaired row is recorded with a description of what changed. Call
`print_report()` to see a full summary of every decision made.
Config files are the methods section — every cleaning decision
versioned in YAML.

**Analyzers** — compute quantities from validated data objects and
produce typed intermediates. Analyzers do not clean. By the time
an analyzer receives its input, structural soundness is already
guaranteed by the objects themselves.

**Intermediates** — validated result objects produced by analyzers
and consumed by visualizers. `CohortTimeline` is the central
intermediate: one row per entity, assembling observation periods,
episodes, and events into a single validated object that every
downstream component trusts.

**Visualizers** — consume one intermediate and one configuration
object and produce one plot. Every visual decision lives in a
versioned YAML config file.

---

## Installation

eventus is not yet on PyPI. Install in editable mode from the repo
root:

```bash
pip install -e .
```

Changes to source files take effect immediately — no reinstall
needed.

> PyPI release planned for v1.0.

---

## Quick start

```python
import eventus
import pandas as pd

# 1. Declare what your columns mean
sem = eventus.EpisodeSemantics(
    identity        = "inpatient_hospitalization",
    entity_id_col   = "patient_id",
    start_time_col  = "admit_date",
    end_time_col    = "discharge_date",
    also_defined_by = ["hospital_id"],
)

# 2. Configure and run the cleaner
config  = eventus.EpisodesCleanerConfig.build_from_yaml("hospitalization_cleaner.yaml")
cleaner = eventus.EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()
cleaner.print_report()   # → structured audit trail, every decision recorded

# 3. Define the observation period
obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = episodes.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# 4. Filter and assemble
episodes = eventus.EpisodesFilter(episodes).to_obs_period(obs, clip=True).result

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes     = episodes,
)

# 5. Analyze
analyzer    = eventus.CohortTimelineEpisodeAnalyzer(ct, "inpatient_hospitalization")
ct_enriched = analyzer.enrich_with_episode_coverage()
summary     = analyzer.get_summary()
print(summary)

# 6. Visualize
config  = eventus.StackedTimelineConfig.build_from_yaml("timeline_config.yaml")
sample  = ct_enriched.sample_subset(n=50, random_seed=42)
eventus.StackedTimelinePlotter(sample, config).plot("timeline.png")
```

---

## Key classes

### Semantics
| Class | Purpose |
|---|---|
| `EpisodeSemantics` | Column mapping for interval episode data |
| `EventSemantics` | Column mapping for point-in-time event data |

### Data Objects
| Class | Purpose |
|---|---|
| `Episodes` | Validated interval episode data |
| `Events` | Validated point-in-time event data |
| `ObsPeriodPerEntity` | Per-entity observation windows |

### Cleaners and Filters
| Class | Purpose |
|---|---|
| `EpisodesCleaner` | Clean raw episode DataFrames → `Episodes` |
| `EventsCleaner` | Clean raw event DataFrames → `Events` |
| `EpisodesCleanerConfig` | Versioned cleaning configuration |
| `EventsCleanerConfig` | Versioned cleaning configuration |
| `EpisodesFilter` | Subset `Episodes` by entity or date |
| `EventsFilter` | Subset `Events` by entity or date |

### Analyzers
| Class | Purpose |
|---|---|
| `CohortTimelineEpisodeAnalyzer` | Episode coverage analysis from `CohortTimeline` |
| `CohortTimelineEventAnalyzer` | Event volume, timing, shape, survival |
| `EventEpisodeAnalyzer` | Temporal relationships between events and episodes |
| `EpisodeDurationAnalyzer` | Episode durations from `Episodes` directly |

### Intermediates
| Class | Purpose |
|---|---|
| `CohortTimeline` | Central per-entity table — assembles all streams |
| `EventResultVolume` | Per-entity event counts |
| `EventResultTiming` | Time to nth event |
| `EventResultShape` | Behavioral fingerprint (gaps, burstiness, memory) |
| `EventEpisodeResult` | Temporal co-event statistics |
| `EpisodeCoverageSummary` | Tiered coverage summary with validated denominators |
| `EpisodeDurationResult` | Per-episode duration statistics |
| `SurvivalResult` | Kaplan-Meier survival curve |

### Visualizers
| Class | Config |
|---|---|
| `StackedTimelinePlotter` | `StackedTimelineConfig` |
| `EventResultVolumePlotter` | `EventResultVolumeConfig` |
| `EventResultTimingPlotter` | `EventResultTimingConfig` |
| `EventResultShapePlotter` | `EventResultShapeConfig` |
| `ActivityOverTimePlotter` | `ActivityOverTimeConfig` |
| `ArraysViolinPlotter` | `ArraysViolinConfig` |
| `EpisodeDurationHistogramPlotter` | `EpisodeDurationPlotConfig` |

---

## Design principles

**Each class has a single responsibility.** `Episodes` validates.
`EpisodesCleaner` cleans. Analyzers compute. Visualizers draw. No
class does two jobs.

**Objects trust what they receive.** An analyzer that accepts a
validated `Episodes` object does not re-check for null identifiers or
causality violations — those guarantees were earned upstream and are
carried by the object.

**Config is the methods section.** Every analytical and visual
decision lives in a versioned YAML file. Configs are frozen
dataclasses with `build_from_yaml()` and `to_yaml()`. The YAML file
is the reproducible record of what was done.

**Specific errors, not silent failures.** Every `raise` has a
message that tells you what went wrong, where, and what to fix.

**The cleaner is the required bridge.** A data object will not
construct from an uncleaned DataFrame. The audit trail — rejected
rows, modified rows, rejection reasons — is automatic.

---

## Submodule READMEs

Each abstraction has its own README with full API reference, design
notes, and examples:

| Folder | Contents |
|---|---|
| `src/eventus/semantics/` | Column mapping and identity rules |
| `src/eventus/data_objects/` | Validated containers and construction paths |
| `src/eventus/cleaners/` | Cleaning pipelines, filters, and quality reports |
| `src/eventus/analyzers/` | Analyzers and output patterns |
| `src/eventus/intermediates/` | `CohortTimeline` and result objects |
| `src/eventus/visualizers/` | Plotters, config files, and YAML reference |

---

## Vignettes

Eight worked examples demonstrating the full pipeline on simulated
data covering insurance coverage periods, nursing facility stays,
emergency department visits, and inpatient hospitalizations:

| Chapter | Topic |
|---|---|
| 1 | Cleaning hospitalization records |
| 2 | Descriptor aggregation in nursing facility data |
| 3 | Episode duration analysis |
| 4 | Observation period construction |
| 5 | Stacked timeline visualization |
| 6 | Event volume analysis |
| 7 | Event timing and gap analysis |
| 8 | Event-episode co-event analysis |

Each chapter includes a without-eventus comparison script in
`vignettes/without_eventus/`.

---

## Future work

- Co-event extensions (event + event, episode + episode)
- Descriptor-based filtering (`EventsFilter.by_descriptor()`)
- Sequential dependency / Markov chain analysis
- Interactive visualization
- PyPI release (`pip install eventus`)
