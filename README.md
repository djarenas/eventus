# eventus

A domain-agnostic Python framework for analyzing entities that experience events within defined observation periods, with optional point-in-time occurrences.

Motivated by recurring analytical challenges in health services research and insurance analytics — where entities have coverage periods, claim events, and discrete clinical occurrences — eventus provides a principled object-oriented pipeline applicable to any domain where entities, time spans, events, and occurrences co-exist.

---

## The five abstractions

```
Semantics → Data Objects → Cleaners → Analyzers → Intermediates → Visualizers
```

**Semantics** — column mappings and identity labels. Decouple analytical logic from specific data schemas.

**Data Objects** — validated containers. If it exists, it is complete. The constructor raises on invalid data.

**Cleaners** — transparent, auditable row-level cleaning. Every rejected row is recorded with an explicit reason. Call `print_quality_report()` to see a full summary.

**Analyzers** — compute quantities from data objects, produce intermediates.

**Intermediates** — the universal handshake format between analyzers and visualizers. One row per entity, pipe-delimited multi-value columns.

**Visualizers** — consume intermediates and config files, produce plots. Config-driven — all visual choices live in a versioned YAML.

---

## Module structure

### Semantics
| Module | Class | Purpose |
|---|---|---|
| `event_semantics.py` | `EventSemantics` | Column mapping for event data |
| `occurrence_semantics.py` | `OccurrenceSemantics` | Column mapping for occurrence data |

### Data objects
| Module | Class | Purpose |
|---|---|---|
| `events.py` | `Events` | Validated event collection |
| `events_per_entity.py` | `EventsPerEntity` | One row per entity enforced |
| `obs_period_per_entity.py` | `ObsPeriodPerEntity` | One observation window per entity |
| `occurrences.py` | `Occurrences` | Validated occurrence collection |
| `occurrences_per_entity.py` | `OccurrencesPerEntity` | One occurrence per entity (landmark events) |

### Cleaning
| Module | Class | Purpose |
|---|---|---|
| `events_cleaner_config.py` | `EventsCleanerConfig` | Events cleaning configuration |
| `events_cleaner.py` | `EventsCleaner` | Full events cleaning pipeline with audit trail |
| `occurrences_cleaner_config.py` | `OccurrencesCleanerConfig` | Occurrences cleaning configuration |
| `occurrences_cleaner.py` | `OccurrencesCleaner` | Occurrences cleaning pipeline with audit trail |

### Analyzers
| Module | Class | Purpose |
|---|---|---|
| `events_within_obs_periods_analyzer.py` | `EventsWithinObsPeriodsAnalyzer` | Active/inactive days per entity |
| `occurrences_within_obs_periods_analyzer.py` | `OccurrencesWithinObsPeriodsAnalyzer` | Occurrences within observation periods |
| `event_duration_analyzer.py` | `EventDurationAnalyzer` | Duration distribution |

### Intermediates
| Module | Class | Purpose |
|---|---|---|
| `pipe_delimited_intermediate.py` | `PipeDelimitedIntermediate` | Base intermediate — `combine()`, `from_objects()`, `copy()` |
| `pipe_delimited_intermediate_events.py` | `PipeDelimitedIntermediateEvents` | Events intermediate — `self_analyze()`, `print_summary()` |
| `pipe_delimited_intermediate_occurrences.py` | `PipeDelimitedIntermediateOccurrences` | Occurrences intermediate — `self_analyze(extras=)`, `print_summary()` |

### Visualizers
| Module | Class | Purpose |
|---|---|---|
| `stacked_timeline_plotter.py` | `StackedTimelinePlotter` | Stacked bar timeline — `plot()`, `from_objects()` |
| `stacked_timeline_config.py` | `StackedTimelineConfig` | Timeline config — `build_from_yaml()`, `to_yaml()` |
| `activity_over_time_plotter.py` | `ActivityOverTimePlotter` | Cohort activity line + entry/exit bars |
| `activity_over_time_config.py` | `ActivityOverTimeConfig` | Activity plotter config |
| `events_duration_plotter.py` | `EventsDurationPlotter` | Duration histograms |
| `histogram_config.py` | `HistogramConfig` | Histogram configuration |

### Utils
| Module | Purpose |
|---|---|
| `events_utils.py` | Overlap merging, clipping |
| `events_within_obs_period_analyzer_utils.py` | Activity/inactivity computation |
| `obs_period_per_entity_utils.py` | Span construction helpers |
| `occurrences_utils.py` | Span building from occurrence dates |
| `occurrences_self_analyze_utils.py` | Burstiness, memory, gap stats computation |
| `pipe_delimited_utils.py` | Intermediate validation |
| `pipe_delimited_intermediate_events_utils.py` | Events analysis column computation |
| `pipe_delimited_intermediate_occurrences_utils.py` | Cohort-level summary after self_analyze() |
| `stacked_timeline_plotter_utils.py` | Segment parsing, x-axis formatting |
| `activity_over_time_plotter_utils.py` | Line panel, diverging bar panel |
| `events_duration_utils.py` | Duration computation |
| `validation_utils.py` | Shared validation helpers |
| `test_utils.py` | Testing helpers |

### Example data
| Module | Function | Purpose |
|---|---|---|
| `generate_example_data.py` | `generate_hospitalizations()` | Synthetic messy hospitalization data |
| | `generate_patient_demographics()` | Synthetic patient demographics with DOB |

---

## The hierarchy

```
Events                    Occurrences
    ↓                         ↓
EventsPerEntity           OccurrencesPerEntity
    ↓
ObsPeriodPerEntity
```

---

## Quick start

### 1. Define semantics

```python
from eventus import EventSemantics, OccurrenceSemantics

event_sem = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)

occ_sem = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)
```

### 2. Clean

```python
from eventus import EventsCleanerConfig, EventsCleaner
from eventus import OccurrencesCleanerConfig, OccurrencesCleaner

event_config = EventsCleanerConfig.build_from_yaml("event_cleaner.yaml")
events       = EventsCleaner(raw_hosp_df, event_sem, event_config).clean()

occ_config   = OccurrencesCleanerConfig.build_from_yaml("occ_cleaner.yaml")
ed_visits    = OccurrencesCleaner(raw_ed_df, occ_sem, occ_config).clean()
```

### 3. Define observation period

```python
from eventus import ObsPeriodPerEntity

# Fixed calendar period
obs = ObsPeriodPerEntity.from_calendar(
    entity_ids = events.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "medicaid_2022",
)

# Age window
obs = ObsPeriodPerEntity.from_age_window(
    entity_df  = demographics_df,
    dob_col    = "date_of_birth",
    age_start  = 65,
    age_end    = 70,
    entity_col = "patient_id",
    age_unit   = "years",        # "years" or "months"
    identity   = "age_65_to_70",
)
```

### 4. Convenience path — from_objects()

```python
from eventus import PipeDelimitedIntermediate

intermediate = PipeDelimitedIntermediate.from_objects(
    obs_period  = obs,
    events      = events,
    occurrences = [ed_visits, vaccinations],
)
```

### 5. Or explicit path — full control

```python
from eventus import (
    EventsWithinObsPeriodsAnalyzer,
    OccurrencesWithinObsPeriodsAnalyzer,
)

events_result = EventsWithinObsPeriodsAnalyzer(
    events     = events,
    obs_period = obs,
).compute_event_coverage()

occ_result = OccurrencesWithinObsPeriodsAnalyzer(
    occurrences = ed_visits,
    obs_period  = obs,
).calc()

# Optionally enrich with statistics before plotting
occ_enriched = occ_result.self_analyze(
    extras = ["burstiness", "memory", "mean_gap"]
)

# Combine
combined = PipeDelimitedIntermediate.combine(events_result, occ_enriched)
```

### 6. Visualize — stacked timeline

```python
from eventus import StackedTimelinePlotter, StackedTimelineConfig

# Convenience path
StackedTimelinePlotter.from_objects(
    obs_period  = obs,
    events      = events,
    occurrences = ed_visits,
    config      = StackedTimelineConfig.build_from_yaml("config.yaml"),
).plot("timeline.png")

# Or with the intermediate directly
config = StackedTimelineConfig.build_from_yaml("config.yaml")
StackedTimelinePlotter(combined, config).plot("timeline.png")
```

### 7. Visualize — activity over time

```python
from eventus import ActivityOverTimePlotter, ActivityOverTimeConfig

config  = ActivityOverTimeConfig.build_from_yaml("activity_config.yaml")
plotter = ActivityOverTimePlotter(events_result, config, granularity="month")
plotter.plot("activity.png")
```

---

## Observation period construction paths

| Classmethod | Requires | Output columns |
|---|---|---|
| `ObsPeriodPerEntity(df, sem)` | DataFrame + semantics | Your column names |
| `from_calendar(entity_ids, start, end, entity_col)` | List of IDs + dates | `obs_start`, `obs_end` |
| `from_age_window(entity_df, dob_col, age_start, age_end, entity_col, age_unit)` | Demographics with DOB | `obs_start`, `obs_end` |
| `from_events(events)` | Events object | Same as events columns |
| `occurrences_per_entity.build_obs_period(window, span_sem)` | OccurrencesPerEntity | Your column names |

---

## Combining intermediates

`PipeDelimitedIntermediate.combine()` merges two or more intermediates. All must share the same entity_col, entity set, and span boundaries:

```python
combined = PipeDelimitedIntermediate.combine(events_result, ed_result, hep_result)
```

Raises with specific entity IDs if span boundaries differ — ensures all intermediates came from the same `ObsPeriodPerEntity`.

---

## Occurrence statistics — self_analyze()

`PipeDelimitedIntermediateOccurrences.self_analyze()` computes per-entity statistics from pipe-delimited occurrence columns:

```python
# Default — always computed
enriched = result.self_analyze()
# Adds: occ_{identity}_n, _first, _last, _time_to_first, _recency_days

# Optional extras
enriched = result.self_analyze(extras=["burstiness", "memory", "mean_gap"])
# Also adds: occ_{identity}_burstiness, _memory, _mean_gap

# Everything
enriched = result.self_analyze(extras="all")
```

Available extras: `mean_gap`, `std_gap`, `cv_gap`, `min_gap`, `max_gap`, `burstiness`, `memory`, `density`

Burstiness and memory follow the Goh-Barabási formulation. Burstiness requires ≥ 3 occurrences, memory requires ≥ 4. Entities below the threshold get `NaN` — never an error.

---

## Stacked timeline config reference

```yaml
general:
  row_height:         0.5       # inches per entity row
  bar_height_ratio:   0.8       # bar fills this fraction of row
  dpi:                150
  show_entity_labels: false
  x_axis:             "auto"    # "auto", "calendar", "normalized"

poi_settings:
  color_before:    "#9E9E9E"   # inactive before first event
  color_middle:    "#F44336"   # gap between events
  color_after:     "#BDBDBD"   # inactive after last event
  color_no_events: "#EEEEEE"   # entity with no events at all

events_settings:
  - identity: events            # required — no auto-discovery
    color:    "#4CAF50"
    label:    "Hospitalization"

occurrences_settings:           # required — no auto-discovery
  - identity: ed_visit          # matches occ_ed_visit column
    color:    "#FF5722"
    marker:   "circle"          # "circle", "triangle", "square", "diamond", "star"
    size:     5
    label:    "ED Visit"

legend:
  show:               true
  outside:            true      # place legend outside plot area (recommended)
  font_size:          9
  show_poi_in_legend: false

x_axis_labels:
  format:   "%Y-%m"             # strftime — calendar mode only
  unit:     "months"            # "days", "months", or "years"
  interval: 3                   # tick every N units
```

**Config is authoritative — no auto-discovery.** If `events_settings` is empty, only the POI bar is drawn. If `occurrences_settings` is empty, no markers are drawn. Unconfigured `occ_` columns are silently ignored.

---

## Design principles

**Domain agnosticism** — all classes accept user-defined column names through semantics objects.

**One job per class** — Events validates, EventsCleaner cleans, Analyzers compute, Visualizers draw.

**If it exists it is complete** — constructors raise on invalid data. No silent failures, no partial objects.

**Config is the methods section** — every analytical and visual decision lives in a versioned YAML, not in code.

**The intermediate is the handshake** — any analyzer output can feed any visualizer. Column naming conventions carry all structural information.

**Parallelism** — Events and Occurrences are siblings, not parent/child. Both have cleaners, both feed analyzers, both produce pipe-delimited intermediates that combine freely.

---

## Identity rules

The `identity` attribute must contain only letters, numbers, and underscores (`^[a-zA-Z0-9_]+$`):

```python
# Valid
EventSemantics(..., identity="inpatient_hospitalization")
OccurrenceSemantics(..., identity="ed_visit")

# Raises
EventSemantics(..., identity="inpatient hospitalization")  # spaces not allowed
```

Identities flow into intermediate column names (`occ_ed_visit`), plot labels, and the de-identification pipeline.

---

## Sorting entities in the timeline

The plotter draws entities in the order they appear in the intermediate. To sort, reorder before plotting:

```python
sorted_df  = combined.data.sort_values("active_days", ascending=False)
sorted_int = PipeDelimitedIntermediate(sorted_df, entity_col="patient_id")
StackedTimelinePlotter(sorted_int, config).plot("timeline.png")
```

Common sort columns from `compute_event_coverage()`:

| Column | Meaning |
|---|---|
| `active_days` | Total days covered by events |
| `inactive_days` | Total days with no events |
| `inactive_days_before_first_event` | Days before first event |
| `inactive_days_after_last_event` | Days after last event |
| `span_duration_days` | Total observation period length |

After `self_analyze()`, also sort by `occ_{identity}_n`, `occ_{identity}_first`, `occ_{identity}_burstiness`, etc.

A `sort_by` parameter will be added to `StackedTimelinePlotter.from_objects()` in a future release once `OccurrencesCleaner` is complete. *(Update: `OccurrencesCleaner` is now done — `from_objects()` sort support is the next step.)*

---

## Example data

```python
from eventus.generate_example_data import (
    generate_hospitalizations,
    generate_patient_demographics,
)

# Edit CONFIG section at the top of generate_example_data.py
# to change N_PATIENTS, OBS_PERIOD_START/END, DOB_YEAR_MIN/MAX, RANDOM_SEED

hosp_df  = generate_hospitalizations()    # messy — with intentional errors
demog_df = generate_patient_demographics() # DOBs, sex

# Patients with zero stays do not appear in hosp_df — realistic
```

---

## Vignettes

The following vignettes demonstrate the full eventus pipeline using synthetic inpatient hospitalization data generated by `generate_example_data.py`.

**Vignette 1 — Cleaning hospitalization data**
Raw hospitalization data with null dates, causality violations, duplicates, and overlapping stays. Clean it with a configurable pipeline that produces a full audit trail of every decision made.

**Vignette 2 — Duration histograms**
Plot the distribution of hospitalization lengths with configurable bins, percentile lines, and optional stratification by hospital or other categorical variables.

**Vignette 3 — Days hospitalized within an observation period**
For each patient, compute how many days they were hospitalized during their period of interest — handling overlapping stays, period boundary clipping, meaningful gap decisions, and patients with zero hospitalizations. Includes burstiness, memory, and gap statistics.

**Vignette 4 — Stacked timeline visualization**
Visualize hospitalizations and occurrences (ED visits, vaccinations) within each patient's observation period as a stacked bar chart. Color-coded segments show inactive time before, between, and after hospitalizations. Configuration-driven — all visual choices live in a YAML file.

**Vignette 5 — Activity over time**
Plot what fraction of the cohort is actively hospitalized at each timepoint. Includes a diverging bar panel showing how many patients entered and exited the active pool — revealing the flow behind the activity curve. A flat activity line with large bars in both directions tells a different story than a flat line with no movement.

*Vignettes are in development.*

---

## Planned future work

**`IntervalActivityCalculator`**
Standalone class for computing cohort activity timeseries from a `PipeDelimitedIntermediateEvents`. Currently `activity_over_time()` lives as a method on the intermediate — this will separate computation from visualization:

```python
ts = IntervalActivityCalculator(intermediate, granularity="month").calc()
ActivityOverTimePlotter(ts, config).plot("activity.png")
```

**`StackedTimelinePlotter.from_objects()` sort support**
Add `sort_by` parameter once the full pipeline is stable:

```python
StackedTimelinePlotter.from_objects(
    obs_period  = obs,
    events      = events,
    occurrences = ed_visits,
    sort_by     = ["active_days"],
    ascending   = [False],
    config      = config,
).plot("timeline.png")
```

**`Deidentifier` and `DeidentifierConfig`**
Entity-level date perturbation and ID hashing from a versioned config file. Destroys absolute dates required for re-identification while preserving all analytical quantities. See the de-identification paper draft for full design specification.

**`__init__.py` and `pyproject.toml`**
Package installation via `pip install eventus`.

**Simulation layer**
Generate synthetic entities whose spans, events, and occurrences conform to the `PipeDelimitedIntermediate` format. Enables validation of analytical methods against known ground truth.
