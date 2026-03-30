# Python Events Package — Design README

## Overview

A Python package for analyzing events, spans, and occurrences for entities
(persons, companies, policies, etc.). All classes are domain-agnostic and
composable. The package follows a clean pipeline:

**Raw objects → Analyzers → Intermediates → Plotters**

All inter-module imports use relative imports (`from .module import ...`)
so the package can be installed and used as a proper Python package.

---

## Module Structure

```
event_semantics.py                              ✅
events.py                                       ✅
events_per_entity.py                            ✅
events_utils.py                                 ✅
validation_utils.py                             ✅
events_within_span_analyzer.py                  ✅
events_within_span_analyzer_utils.py            ✅
pipe_delimited_intermediate.py                  ✅
pipe_delimited_utils.py                         ✅
pipe_delimited_intermediate_event_analysis.py   ✅
pipe_delimited_intermediate_event_analysis_utils.py ✅
occurrence_semantics.py                         ✅
occurrences.py                                  ✅
occurrences_per_entity.py                       ✅
occurrences_utils.py                            ✅
viz_stacked_events.py                           ✅
stacked_events_config.yaml                      ✅
viz_activity_over_time.py                       ✅
activity_over_time_config.yaml                  ✅
viz_histograms.py                               ✅
histograms_config.yaml                          ✅
test_utils.py                                   ✅
occurrences_within_spans_analyzer.py            🔲
occurrences_within_events_analyzer.py           🔲
```

---

## Pipeline

```
Events + EventsPerEntity (spans)
        ↓
EventsWithinSpansAnalyzer.calc_active_vs_inactive()
        ↓
PipeDelimitedIntermediateEventAnalysis
        ├── .tier1() / .tier2() / .tier3() / .print_summary()
        ├── .sort(by, ascending)
        ├── .activity_over_time(granularity)
        ├── .plot_activity_over_time(config_path, path, granularity)
        ├── .plot_active_days(config_path, path)
        ├── .plot_inactive_days(config_path, path)
        ├── .plot_inactive_before(config_path, path)
        ├── .plot_inactive_after(config_path, path)
        ├── .plot_inactive_middle(config_path, path)
        ├── .plot_violin(config_path, path)
        └── StackedEventsPlotter(config_path, intermediate, ...).plot(path)

OccurrencesPerEntity
        └── .build_span(window, span_semantics) → EventsPerEntity
```

---

## Built Classes

### `EventSemantics`
Maps generic concepts to specific column names in a DataFrame.

**Attributes:** `entity_id_col`, `start_time_col`, `end_time_col`,
`event_id_col` (optional), `event_type_col` (optional), `metadata_cols`

**Key methods:** `build_from_yaml(path)` → `EventSemantics`

---

### `Events`
A validated collection of events with start and end times.
Bad rows are triaged into `.rejected`.

**Attributes:** `data`, `semantics`, `rejected`

**Triage rules:**
- Null `entity_id_col`, `start_time_col`, or `end_time_col` → rejected
- `start_time_col > end_time_col` → rejected

**Key methods:**
- `merge_overlapping_events(meaningful_gap=0)` → `Events`
- `clip_to_spans(spans, ignore_entities_with_no_span=False)` → `Events`
- `filter_by_entities(ids)` → `Events`
- `filter_by_dates(start, end)` → `Events`
- `count_per_entity()` → `np.ndarray`
- `copy()` → `Events`

---

### `EventsPerEntity`
Inherits from `Events`. Enforces exactly one row per entity after triage.

---

### `events_utils.py`
- `merge_overlapping_events(events_df, semantics, meaningful_gap)` → `pd.DataFrame`
- `clip_events_to_spans(events_df, spans_df, entity_col, start_col, end_col, span_start_col, span_end_col, ignore_entities_with_no_span=False)` → `pd.DataFrame`

---

### `validation_utils.py`
- `validate_shared_entity_col(obj_a, obj_b, label_a, label_b)` → `str`

---

### `EventsWithinSpansAnalyzer`
Analyzes event coverage within per-entity span windows.
Overlapping events are merged once at construction time.

**Constructor:**
```python
EventsWithinSpansAnalyzer(
    events: Events,
    spans: EventsPerEntity,
    entity_col: str | None = None,
    meaningful_gap: int = 0,
)
```

**Key methods:**
- `calc_active_vs_inactive()` → `PipeDelimitedIntermediateEventAnalysis`

---

### `PipeDelimitedIntermediate`
Base class. Universal handshake format between analyzers and visualizers.
One row per entity. All multi-value columns are pipe-delimited strings.

**Required columns:** `entity_id` (name configurable)

**Optional paired columns** (must have both or neither):
- `span_start` + `span_end`
- `event_starts` + `event_ends`

**Optional occurrence columns:** any column prefixed `occ_`

**Key methods:**
- `self_validate()` → `pd.DataFrame` of bad rows
- `from_dataframe(df, entity_col)` → `PipeDelimitedIntermediate`
- `to_csv(path)`
- `identity_to_col(identity)` → `str`
- `col_to_identity(col)` → `str`

**Properties:** `has_spans`, `has_events`, `occurrence_cols`, `occurrence_identities`

---

### `pipe_delimited_utils.py`
- `validate_content(data, entity_col)` → `pd.DataFrame` of bad rows

---

### `PipeDelimitedIntermediateEventAnalysis`
Inherits from `PipeDelimitedIntermediate`.
Result of `EventsWithinSpansAnalyzer.calc_active_vs_inactive()`.
One row per entity.

**Additional required columns:**

| Column | Description |
|---|---|
| `span_duration_days` | total span length in days |
| `active_days` | days covered by events (NA if no coverage) |
| `inactive_days` | span_duration_days - active_days (NA if no coverage) |
| `inactive_days_before_first_event` | gap before first event (NA if no coverage) |
| `inactive_days_after_last_event` | gap after last event (NA if no coverage) |
| `inactive_days_middle` | inactive days between events (NA if no coverage) |
| `first_event_start` | first event start clipped to span_start (NA if no coverage) |
| `last_event_end` | last event end clipped to span_end (NA if no coverage) |

**Diagnostic methods** (thin wrappers over utils):
- `tier1()`, `tier2()`, `tier3(percentiles=[25,50,75])` → dict
- `full_summary(percentiles)` → dict
- `print_summary(percentiles)`, `save_summary(path, percentiles)`

**Analysis methods:**
- `activity_over_time(granularity="month")` → `pd.DataFrame`
  Columns: `[day, n_total, n_active, pct_active, n_entered, n_exited]`
  X axis is relative days from span_start. `pct_active` is a fraction (0–1).
- `sort(by, ascending=True)` → `PipeDelimitedIntermediateEventAnalysis`

**Visualization methods:**
- `plot_activity_over_time(config_path, path, granularity="month")`
- `plot_active_days(config_path, path)`
- `plot_inactive_days(config_path, path)`
- `plot_inactive_before(config_path, path)`
- `plot_inactive_after(config_path, path)`
- `plot_inactive_middle(config_path, path)`
- `plot_violin(config_path, path)`

**Inherited:** `self_validate()`, `to_csv()`, `from_dataframe()`

---

### `pipe_delimited_intermediate_event_analysis_utils.py`
Workhorse functions — all independently callable:
- `calc_tier1(data, entity_col)` → dict
- `calc_tier2(data, entity_col)` → dict
- `calc_tier3(data, entity_col, percentiles)` → dict
- `calc_activity_over_time(data, entity_col, granularity)` → `pd.DataFrame`

---

### `OccurrenceSemantics`
Maps column names for point-in-time occurrence data.

**Attributes:** `entity_id_col`, `date_col`, `identity` (optional human-readable label),
`occurrence_id_col` (optional), `metadata_cols`

**Key methods:** `build_from_yaml(path)` → `OccurrenceSemantics`

---

### `Occurrences`
A validated collection of point-in-time occurrences (no end date).

**Attributes:** `data`, `semantics`, `rejected`

**Triage rules:**
- Null `entity_id_col` → rejected
- Null or unparseable `date_col` → rejected

**Key methods:**
- `filter_by_entities(ids)` → `Occurrences`
- `filter_by_dates(start, end)` → `Occurrences`
- `count_per_entity()` → `pd.Series`
- `copy()` → `Occurrences`

---

### `OccurrencesPerEntity`
Inherits from `Occurrences`. One occurrence per entity.

**Additional method:**
- `build_span(window=(before_days, after_days), span_semantics)` → `EventsPerEntity`

---

### `occurrences_utils.py`
- `build_span_from_occurrences(data, semantics, span_semantics, window)` → `pd.DataFrame`

---

### `StackedEventsPlotter`
Pure renderer. One horizontal bar per entity showing event intervals within
a span, with optional occurrence markers as vertical lines.
Accepts any `PipeDelimitedIntermediate` or subclass.

**Constructor:**
```python
StackedEventsPlotter(
    config_path: str,
    intermediate: PipeDelimitedIntermediate,
    occurrences: list | None = None,
    sort_by: list[str] | None = None,
    ascending: bool | list = True,
    n_sample: int | None = None,
    random_state: int | None = None,
)
```

**Key methods:** `plot(path)` — saves to .png, .jpg, .jpeg

---

### `stacked_events_config.yaml`
```yaml
general:
  row_height: 0.5
  bar_height_ratio: 0.8
  dpi: 150
  font_size: 11
  title_font_size: 13
  style: "seaborn-v0_8-whitegrid"
  title: null

colors:
  before: "#9E9E9E"
  active: "#4CAF50"
  middle: "#F44336"
  after:  "#BDBDBD"
  no_coverage: "#EEEEEE"

occurrences:
  - identity: "Hepatitis B vaccination"
    color: "#FF5722"
    thickness: 1.5
```

---

### `ActivityOverTimePlotter`
Two subplots sharing the x-axis (relative days from span_start):
- Top: line chart of `pct_active` (fraction 0–1) with optional fill
- Bottom: up/down arrows showing entities entered/exited, sized proportionally

**Constructor:**
```python
ActivityOverTimePlotter(
    config_path: str,
    timeseries: pd.DataFrame,  # output of activity_over_time()
)
```

**Key methods:** `plot(path)` — saves to .png, .jpg, .jpeg

---

### `activity_over_time_config.yaml`
```yaml
general:
  figsize: [14, 7]
  dpi: 150
  font_size: 11
  title_font_size: 13
  style: "seaborn-v0_8-whitegrid"
  title: null
  xtick_interval: 60

line:
  color: "#2196F3"
  linewidth: 2.0
  fill_alpha: 0.15

arrows:
  show: true
  arrow_axis_y: 0.5
  entered_color: "#4CAF50"
  exited_color: "#F44336"
  max_size: 200
  min_size: 20

layout:
  top_height_ratio: 3
  bottom_height_ratio: 1
```

---

### `EventAnalysisHistogramPlotter`
Histograms and violin plots for `PipeDelimitedIntermediateEventAnalysis`.
All histograms show p25/p50/p75 percentile lines and n/% subtitle.
Metrics filtered to entities where value > 0 where appropriate.

**Constructor:**
```python
EventAnalysisHistogramPlotter(
    config_path: str,
    intermediate: PipeDelimitedIntermediateEventAnalysis,
)
```

**Plot methods:**
- `plot_active_days(path)`
- `plot_inactive_days(path)`
- `plot_inactive_before(path)`
- `plot_inactive_after(path)`
- `plot_inactive_middle(path)`
- `plot_violin(path)` — all four inactive metrics side by side, subtitle outside axes

**Workhorse extractors** (independently callable):
- `_get_active_days(data)`, `_get_inactive_days(data)`
- `_get_inactive_before(data)`, `_get_inactive_after(data)`, `_get_inactive_middle(data)`

---

### `histograms_config.yaml`
```yaml
general:
  dpi: 150
  font_size: 11
  title_font_size: 13
  style: "seaborn-v0_8-whitegrid"

histogram:
  bins: 30
  color: "#4CAF50"
  edgecolor: "#ffffff"
  alpha: 0.85
  figsize: [10, 5]
  legend_loc: "upper right"
  subtitle_loc: "upper right"

violin:
  color: "#2196F3"
  alpha: 0.7
  inner: "box"
  figsize: [12, 6]
```

---

### `test_utils.py`
Test utilities for validating the activity_over_time computation.

**Functions:**
- `make_asymptote_test_data(n, asymptote, scale, span_days, random_state)`
  → `PipeDelimitedIntermediateEventAnalysis`
  Builds synthetic data where true curve = `asymptote * (1 - exp(-x/scale))`
- `plot_asymptote_test(result, asymptote, scale, path, granularity)`
  Plots computed vs theoretical curve for visual validation.

---

## Designed Classes (not yet built)

### `OccurrencesWithinSpansAnalyzer`
Takes `Occurrences` + `EventsPerEntity`. Returns a `PipeDelimitedIntermediate`
child with per-occurrence rows.

### `OccurrencesWithinEventsAnalyzer`
Takes `Occurrences` + `Events`. Returns a `PipeDelimitedIntermediate` child
with per-occurrence rows.

---

## Typical Usage

```python
# Build semantics
event_sem = EventSemantics.build_from_yaml("event_sem.yaml")
span_sem  = EventSemantics.build_from_yaml("span_sem.yaml")
occ_sem   = OccurrenceSemantics.build_from_yaml("occ_sem.yaml")

# Build objects
events = Events(events_df, event_sem)
spans  = EventsPerEntity(spans_df, span_sem)

# Or build spans from an occurrence (e.g. index date)
diagnoses = OccurrencesPerEntity(dx_df, occ_sem)
spans     = diagnoses.build_span(window=(365, 365), span_semantics=span_sem)

# Analyze
result = EventsWithinSpansAnalyzer(events, spans, meaningful_gap=7).calc_active_vs_inactive()

# Diagnostics
result.print_summary()

# Stacked bar plot
StackedEventsPlotter(
    config_path="stacked_events_config.yaml",
    intermediate=result,
    sort_by=["active_days", "first_event_start"],
    n_sample=200,
    random_state=42,
).plot("stacked.png")

# Activity over time
result.plot_activity_over_time(
    config_path="activity_over_time_config.yaml",
    path="activity.png",
    granularity="month",
)

# Histograms
result.plot_active_days("histograms_config.yaml", "active_days.png")
result.plot_violin("histograms_config.yaml", "violin.png")
```
