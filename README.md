# eventus

A domain-agnostic Python framework for longitudinal cohort analysis
with events, occurrences, and observation periods — object-oriented,
configuration-driven, and auditable.

Built for recurring challenges in health services research and
insurance analytics, but applicable wherever entities, time spans,
interval events, and point-in-time occurrences co-exist.

> **Note:** eventus is research software provided as-is under the
> MIT License. Its architecture is designed to enforce structural
> validity and produce auditable pipelines. It does not guarantee
> the scientific validity of analytical decisions — that
> responsibility remains with the researcher. Contributions, bug
> reports, and extensions are welcome.

---

## The six abstractions

```
Semantics — Data Objects — Cleaners — Analyzers — Intermediates — Visualizers
```

**Semantics** — map column names to concepts. Declare what your
columns mean and what defines a unique event or occurrence. Define
once, reuse everywhere.

**Data Objects** — validated containers. If it exists, it is
complete. Constructors raise on invalid data — no silent failures,
no partial objects. An `Events` object guarantees every row has a
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
events, and occurrences into a single validated object that every
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
sem = eventus.EventSemantics(
    identity        = "inpatient_hospitalization",
    entity_id_col   = "patient_id",
    start_time_col  = "admit_date",
    end_time_col    = "discharge_date",
    also_defined_by = ["hospital_id"],
)

# 2. Configure and run the cleaner
config  = eventus.EventsCleanerConfig.build_from_yaml("hospitalization_cleaner.yaml")
cleaner = eventus.EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()
cleaner.print_report()   # → structured audit trail, every decision recorded

# 3. Define the observation period
obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = events.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# 4. Filter and assemble
events = eventus.EventsFilter(events).to_obs_period(obs, clip=True).result

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    events     = events,
)

# 5. Analyze
analyzer    = eventus.CohortTimelineEventAnalyzer(ct, "inpatient_hospitalization")
ct_enriched = analyzer.enrich_with_event_coverage()
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
| `EventSemantics` | Column mapping for interval event data |
| `OccurrenceSemantics` | Column mapping for point-in-time occurrence data |

### Data Objects
| Class | Purpose |
|---|---|
| `Events` | Validated interval event data |
| `Occurrences` | Validated point-in-time occurrence data |
| `ObsPeriodPerEntity` | Per-entity observation windows |

### Cleaners and Filters
| Class | Purpose |
|---|---|
| `EventsCleaner` | Clean raw event DataFrames → `Events` |
| `OccurrencesCleaner` | Clean raw occurrence DataFrames → `Occurrences` |
| `EventsCleanerConfig` | Versioned cleaning configuration |
| `OccurrencesCleanerConfig` | Versioned cleaning configuration |
| `EventsFilter` | Subset `Events` by entity or date |
| `OccurrencesFilter` | Subset `Occurrences` by entity or date |

### Analyzers
| Class | Purpose |
|---|---|
| `CohortTimelineEventAnalyzer` | Event coverage analysis from `CohortTimeline` |
| `CohortTimelineOccurrenceAnalyzer` | Occurrence volume, timing, shape, survival |
| `OccurrenceEventAnalyzer` | Temporal relationships between occurrences and events |
| `EventDurationAnalyzer` | Event durations from `Events` directly |

### Intermediates
| Class | Purpose |
|---|---|
| `CohortTimeline` | Central per-entity table — assembles all streams |
| `OccurrenceResultVolume` | Per-entity occurrence counts |
| `OccurrenceResultTiming` | Time to nth occurrence |
| `OccurrenceResultShape` | Behavioral fingerprint (gaps, burstiness, memory) |
| `OccurrenceEventResult` | Temporal co-occurrence statistics |
| `EventCoverageSummary` | Tiered coverage summary with validated denominators |
| `EventDurationResult` | Per-event duration statistics |
| `SurvivalResult` | Kaplan-Meier survival curve |

### Visualizers
| Class | Config |
|---|---|
| `StackedTimelinePlotter` | `StackedTimelineConfig` |
| `OccurrenceResultVolumePlotter` | `OccurrenceResultVolumeConfig` |
| `OccurrenceResultTimingPlotter` | `OccurrenceResultTimingConfig` |
| `OccurrenceResultShapePlotter` | `OccurrenceResultShapeConfig` |
| `ActivityOverTimePlotter` | `ActivityOverTimeConfig` |
| `ArraysViolinPlotter` | `ArraysViolinConfig` |
| `EventDurationHistogramPlotter` | `EventDurationPlotConfig` |

---

## Design principles

**Each class has a single responsibility.** `Events` validates.
`EventsCleaner` cleans. Analyzers compute. Visualizers draw. No
class does two jobs.

**Objects trust what they receive.** An analyzer that accepts a
validated `Events` object does not re-check for null identifiers or
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
| 3 | Event duration analysis |
| 4 | Observation period construction |
| 5 | Stacked timeline visualization |
| 6 | Occurrence volume analysis |
| 7 | Occurrence timing and gap analysis |
| 8 | Occurrence-event co-occurrence analysis |

Each chapter includes a without-eventus comparison script in
`vignettes/without_eventus/`.

---

## Future work

- Co-occurrence extensions (occurrence + occurrence, event + event)
- Descriptor-based filtering (`OccurrencesFilter.by_descriptor()`)
- Sequential dependency / Markov chain analysis
- Interactive visualization
- PyPI release (`pip install eventus`)
