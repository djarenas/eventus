# eventus.visualizers

Configuration-driven, reproducible plotting for eventus intermediates.
Every visual decision lives in a validated config object — not in code.
A config file is a complete, human-readable record of what was plotted
and how. Hand someone a YAML file and they can reproduce any plot exactly.

---

## The problem visualizers solve

A typical data science visualization workflow embeds visual choices
directly in code — colors, bin widths, axis ranges, tick formats,
figure sizes. These choices are invisible to anyone reading the analysis
later. They cannot be versioned, shared, or reproduced without reading
the script line by line.

eventus visualizers separate the *what* from the *how*. The plotter
knows how to draw. The config knows what to draw. The intermediate
carries the data. None of the three knows about the others' concerns.

---

## The pipeline

```
Intermediate                      — validated result object
    ↓
Config                            — every visual decision, validated
    ↓                               at construction, round-trippable
Plotter                           — consumes one intermediate and
    ↓                               one config, produces one plot
plot.png
```

The intermediate and the config are fully independent. The same
`EventResultShape` can be plotted with a default config, a custom
config loaded from YAML, or a config built programmatically. The plotter
does not care how the config was built — only that it is valid.

---

## Shared utilities

Three utility modules live at the top level of `visualizers/` and are
shared across all plotters. Plotters never duplicate these.

### `plot_utils.py` — universal primitives

| Function | Purpose |
|---|---|
| `validate_path(path, error_prefix)` | Check output file extension and parent directory |
| `save_figure(fig, path, dpi, verbose=False)` | Save and close a figure. `verbose=True` prints the saved path |
| `apply_style(fig, axes, canvas, labels, auto_title)` | Apply font sizes and title |

### `histogram_utils.py` — histogram and distribution primitives

| Function | Purpose |
|---|---|
| `compute_bins(series, bins_cfg)` | Derive bin edges from `BinsConfig` and data |
| `draw_histogram(ax, series, cfg, label)` | Draw a histogram on an `Axes` |
| `draw_percentile_lines(ax, series, pct_cfg)` | Draw vertical percentile reference lines |
| `resolve_x_limits(series_list, bins_cfg)` | Compute shared x limits across multiple series |

### `violin_utils.py` — violin drawing primitives

| Function | Purpose |
|---|---|
| `compute_widths(arrays, plot_order)` | sqrt(n)-scaled violin widths |
| `draw_violin_body(ax, arr, position, width, color, bandwidth)` | KDE outline violin |
| `draw_box(ax, arr, position, color)` | Median and range summary lines |
| `draw_points(ax, arr, position, width, color, alpha, size)` | Jittered scatter overlay |
| `draw_percentile_lines(ax, arr, position, width, pct_cfg, font_size)` | Horizontal reference lines |
| `apply_y_bounds(ax, axcfg)` | Set y limits from `ViolinAxisConfig` |
| `build_tick_labels(plot_order, resolved, sizes)` | `"Label\n(n=N)"` tick strings |
| `build_tick_labels_with_pct(plot_order, arrays, n_total, resolved)` | `"Label\n(n=N, X%)"` tick strings |

---

## Config architecture

The config system is built on two principles:

**Trust through construction.** If a config object exists, it is valid.
All validation happens at `__post_init__`. Plotters never defensive-check
their config inputs.

**Concept honesty.** Each class represents exactly one real concept.
A labels class knows about labels. A style class knows about style.
An axis class knows about axis behavior.

### The hierarchy

```
BasePlotConfig                    — abstract base
    ↓ inherits
Concrete configs                  — one per plot type or orchestrator
    ↓ composed of
Section dataclasses               — small, single-concern, validated
```

### Shared building blocks

**`CanvasConfig`** — figsize, dpi, font_size. Every config has one.

**Labels:** `BasePlotLabels` → `AxisLabels` → plot-specific subclasses.

**`AxisConfig`** — tick locations, rotation, format strings. Separate
from labels — "what are the axes called" and "how do they look" are
different concerns.

**Style hierarchy:** `BaseStyleConfig` (alpha) → `AxisStyleConfig`
(+ color, show_grid) → `EdgeStyleConfig` (+ edgecolor).

**`PercentilesConfig`** — vertical reference lines at chosen percentiles.
Composable into any config that needs them.

**`BinsConfig`** — standalone binning configuration with four types:

```python
BinsConfig.auto()
BinsConfig.uniform(n_bins=30, min=0, max=365)
BinsConfig.log(n_bins=20, min=1, max=10_000)
BinsConfig.custom(edges=[0, 10, 25, 50, 100, 365])
```

**`CategoryConfig`** — color and optional label for one category.
Used wherever plots stratify by group.

**`KDEStyleConfig`** — color, alpha, fill_alpha, linewidth, bandwidth,
show_grid. Used by `KDEPlotConfig`.

### Construction paths

Every config supports three construction paths:

```python
MyConfig()                          # zero-argument defaults
MyConfig.build_from_yaml(path)      # from YAML file — primary path
MyConfig.build_from_dict(data)      # from a plain dict — used programmatically
                                    # and by orchestrator _build_sections() internally
```

`build_from_yaml()` is the primary path for reproducible analyses.
Zero-argument construction is the fallback for quick exploration.

### YAML round-trip

Every config can be saved and reloaded exactly:

```python
config = HistogramPlotConfig.build_from_yaml("histogram.yaml")
config.to_yaml("histogram_copy.yaml")   # identical to the original
```

---

## Configs reference

### `StackedTimelineConfig`

Full configuration for `StackedTimelinePlotter`.

**Requires at least one episode layer or event layer** — raises at
construction if both `episodes` and `events` are empty lists.

| Section | Class | Controls |
|---|---|---|
| `canvas` | `CanvasConfig` | figsize, dpi, font_size |
| `labels` | `StackedTimelineLabels` | title, subtitle, title_font_size |
| `layout` | `LayoutConfig` | row height, max entities, entity labels, jitter |
| `x_axis` | `TimelineAxisConfig` | mode (auto/calendar/normalized), unit, interval |
| `poi` | `POIConfig` | observation period bar segment colors |
| `episodes` | `list[EpisodeLayerConfig]` | one per episode identity — color, alpha, label |
| `events` | `list[EventLayerConfig]` | one per event identity — color, marker, size |
| `legend` | `LegendConfig` | show, location, font size, outside placement |

### `ActivityOverTimeConfig`

Full configuration for `ActivityOverTimePlotter`.

| Section | Class | Controls |
|---|---|---|
| `canvas` | `CanvasConfig` | figsize, dpi, font_size |
| `labels` | `AxisLabels` | title, subtitle, axis labels |
| `time` | `TimeConfig` | x_unit, x_interval, matplotlib style |
| `line_style` | `ActivityLineStyleConfig` | color, alpha, fill, linewidth |
| `flow_style` | `FlowStyleConfig` | bottom panel mode, colors, enabled |
| `layout` | `ActivityLayoutConfig` | relative height of top vs bottom panel |

### `HistogramPlotConfig`

General-purpose histogram configuration. Used directly and composed
into orchestrator configs.

**Sections:** `canvas`, `bins`, `labels`, `axes`, `style`,
`percentile_lines`, `stratification`.

### `KDEPlotConfig`

Standalone KDE density curve configuration. Reusable by any plotter
that draws a KDE curve.

**Sections:** `canvas`, `labels`, `axes`, `style` (`KDEStyleConfig`),
`percentiles`.

### `EpisodeDurationPlotConfig`

Orchestrator config for `EpisodeDurationHistogramPlotter`. One YAML file
configures both plot methods. Canvas propagates into both sub-configs.

| Attribute | Class | Plot method |
|---|---|---|
| `histogram` | `HistogramPlotConfig` | `plot_histogram()` |
| `kde` | `KDEPlotConfig` | `plot_kde()` |

### `EventResultVolumeConfig`

Orchestrator for `EventResultVolumePlotter`.

| Attribute | Class | Plot method |
|---|---|---|
| `bar` | `CategoryBarConfig` | `plot_prevalence_bar()` |
| `count_bar` | `CountDistributionBarConfig` | `plot_count_distribution_bar()` |

### `EventResultTimingConfig`

Orchestrator for `EventResultTimingPlotter`. Supports per-nth
histogram overrides resolved at draw time:
`cfg.histogram_per_n.get(nth, cfg.histogram)`.

| Attribute | Class | Controls |
|---|---|---|
| `histogram` | `HistogramPlotConfig` | base config for all nths |
| `histogram_per_n` | `dict[int, HistogramPlotConfig]` | per-nth overrides |
| `facet` | `FacetConfig` | subplot height and width |

### `EventResultShapeConfig`

Orchestrator for `EventResultShapePlotter`. Canvas shared across
all three plot methods.

| Attribute | Class | Plot method |
|---|---|---|
| `center_of_mass` | `HistogramPlotConfig` | `plot_center_of_mass()` |
| `density` | `HistogramPlotConfig` | `plot_density()` |
| `scatter` | `ShapeScatterConfig` | `plot_fingerprint()` |

### `ArraysViolinConfig`

Configuration for `ArraysViolinPlotter`. Categories define one violin
each — plot order follows definition order.

**Sections:** `canvas`, `labels`, `axes` (`ViolinAxisConfig`), `style`
(`ViolinStyleConfig`), `percentiles`, `categories`.

### `EpisodeDurationViolinConfig`

Configuration for `EpisodeDurationViolinPlotter`. Extends
`BaseViolinConfig` with a `stratify_by` column name that tells the
plotter which column in `EpisodeDurationResult.data` to group by.

```python
config = EpisodeDurationViolinConfig.build_from_dict({
    "stratify_by": "hospital_id",
    "stratify": {
        "all_data": {"color": "#AAAAAA", "label": "All"},
        "H01":      {"color": "#028090", "label": "North"},
    },
})
```

**Sections:** `canvas`, `stratify_by`, `stratify`, `labels`, `axes`
(`ViolinAxisConfig`), `style` (`ViolinStyleConfig`), `percentiles`.

---

## Plotters reference

### `StackedTimelinePlotter`

One horizontal bar per entity. Observation period bar segmented into
before/active/gap/after regions. Episode coverage and event markers
overlaid. Optional entity sorting by any column in the `CohortTimeline`.

```python
from eventus.types import EpisodeCoverageMetric

config  = StackedTimelineConfig.build_from_yaml("timeline.yaml")
plotter = StackedTimelinePlotter(cohort_timeline, config)
plotter.plot("timeline.png")

# Sort by active days — longest first (default metric)
plotter = StackedTimelinePlotter(
    cohort_timeline,
    config,
    sort_identity = "inpatient_hospitalization",
    ascending     = False,
)

# Sort by multiple metrics — active days first, then inactive middle
plotter = StackedTimelinePlotter(
    cohort_timeline,
    config,
    sort_identity = "inpatient_hospitalization",
    sort_metrics  = [
        EpisodeCoverageMetric.ACTIVE_DAYS,
        EpisodeCoverageMetric.INACTIVE_DAYS_MIDDLE,
    ],
    ascending     = [False, True],
)
```

`sort_identity` must be present in `cohort_timeline.episode_identities`
and coverage columns must already exist (call
`enrich_with_episode_coverage()` first). `sort_metrics` defaults to
`[EpisodeCoverageMetric.ACTIVE_DAYS]` when not specified.

**Requires:** `CohortTimeline` with obs_start and obs_end.

### `ActivityOverTimePlotter`

Two-panel plot. Top: percentage of cohort with active episode coverage
at each timepoint. Bottom: entities entering and exiting coverage
(diverging bar or scatter). Supports calendar and normalized x-axis modes.

```python
config  = ActivityOverTimeConfig.build_from_yaml("activity.yaml")
plotter = ActivityOverTimePlotter(activity, config)
plotter.plot("activity.png")
```

**Requires:** `EpisodeActivityOverTime` from
`CohortTimelineEpisodeAnalyzer.compute_activity_over_time()`.

### `EpisodeDurationHistogramPlotter`

Histogram and KDE density curve of episode durations. No stratification
— use `EpisodeDurationViolinPlotter` for group comparisons.

```python
result  = EpisodeDurationAnalyzer(episodes).calc()
config  = EpisodeDurationPlotConfig.build_from_yaml("duration.yaml")
plotter = EpisodeDurationHistogramPlotter(result, config)
plotter.plot_histogram("duration_histogram.png")
plotter.plot_kde("duration_kde.png")
```

**Requires:** `EpisodeDurationResult` from `EpisodeDurationAnalyzer.calc()`.

### `EpisodeDurationViolinPlotter`

Violin plot of episode durations. Stratification is a constructor
argument — the column must be in `result.descriptor_cols`.

```python
# No stratification
result  = EpisodeDurationAnalyzer(episodes).calc()
config  = ArraysViolinConfig.build_from_yaml("duration_violin.yaml")
plotter = EpisodeDurationViolinPlotter(result, config)
plotter.plot("durations.png")

# Stratified by hospital
result  = EpisodeDurationAnalyzer(
    episodes, descriptor_cols=["hospital_id"]
).calc()
plotter = EpisodeDurationViolinPlotter(result, config, stratify_by="hospital_id")
plotter.plot("durations_by_hospital.png")
```

**Requires:** `EpisodeDurationResult` from `EpisodeDurationAnalyzer.calc()`.

### `EpisodeCoverageViolinPlotter`

Violin plots of episode coverage metrics — active days vs inactive days,
and inactive day breakdown — from a `CohortTimeline` enriched with
coverage analysis columns.

```python
ct      = CohortTimelineEpisodeAnalyzer(ct, "inpatient").enrich_with_episode_coverage()
config  = ArraysViolinConfig.build_from_yaml("coverage_violin.yaml")
plotter = EpisodeCoverageViolinPlotter(ct, identity="inpatient", config=config)
plotter.plot_total("total.png")
plotter.plot_inactive_breakdown("breakdown.png")
```

**Requires:** `CohortTimeline` enriched with `eps_comp_{identity}_*` columns.

### `ArraysViolinPlotter`

Generic violin drawing engine. Accepts a `{key: np.ndarray}` dict —
domain-agnostic. All other violin plotters delegate drawing to this.

```python
arrays  = {"all_data": dur_all, "Hospital_A": dur_a, "Hospital_B": dur_b}
config  = ArraysViolinConfig.build_from_yaml("violin.yaml")
plotter = ArraysViolinPlotter(arrays, config)
plotter.plot("violin.png")
```

### `EventResultVolumePlotter`

```python
config  = EventResultVolumeConfig.build_from_yaml("volume.yaml")
plotter = EventResultVolumePlotter(volume, config)
plotter.plot_prevalence_bar("prevalence.png")
plotter.plot_count_distribution_bar("count_distribution.png")
```

### `EventResultTimingPlotter`

```python
config  = EventResultTimingConfig.build_from_yaml("timing.yaml")
plotter = EventResultTimingPlotter(timing, config)
plotter.plot_histogram("timing.png")
```

### `EventResultShapePlotter`

```python
config  = EventResultShapeConfig.build_from_yaml("shape.yaml")
plotter = EventResultShapePlotter(shape, config)
plotter.plot_fingerprint("fingerprint.png")
plotter.plot_center_of_mass("center_of_mass.png")
plotter.plot_density("density.png")
```

---

## Full plotter — intermediate — config table

| Plotter | Intermediate | Config |
|---|---|---|
| `StackedTimelinePlotter` | `CohortTimeline` | `StackedTimelineConfig` |
| `ActivityOverTimePlotter` | `EpisodeActivityOverTime` | `ActivityOverTimeConfig` |
| `EpisodeDurationHistogramPlotter` | `EpisodeDurationResult` | `EpisodeDurationPlotConfig` |
| `EpisodeDurationViolinPlotter` | `EpisodeDurationResult` | `ArraysViolinConfig` |
| `EpisodeCoverageViolinPlotter` | `CohortTimeline` (enriched) | `ArraysViolinConfig` |
| `ArraysViolinPlotter` | `dict[str, np.ndarray]` | `ArraysViolinConfig` |
| `EventResultVolumePlotter` | `EventResultVolume` | `EventResultVolumeConfig` |
| `EventResultTimingPlotter` | `EventResultTiming` | `EventResultTimingConfig` |
| `EventResultShapePlotter` | `EventResultShape` | `EventResultShapeConfig` |

---

## Design notes

**Config is the methods section.** Every visual decision lives in a
versioned YAML file. The config file is a complete, human-readable
record of what was plotted and how. This is reproducibility at the
visualization layer.

**Concept honesty over convenience.** Every section dataclass represents
exactly one real concept. No class absorbs a neighboring concern for
convenience. The hierarchy is predictable and extensible.

**Orchestrator configs.** Some configs act as orchestrators — each
attribute owns the full configuration for exactly one plot method.
One YAML file configures an entire analytical visualization suite.
Canvas propagates into all sub-configs for visual consistency.

**Stratification belongs on the plotter, not the config.**
`EpisodeDurationViolinPlotter` accepts `stratify_by` as a constructor
argument. The config controls visual decisions. Which column to group
by is a data-wiring decision. These are different concerns.

**Validation at construction, not at plot time.** If a config exists,
it is valid. Errors surface immediately when the config is built.

**The intermediate is the handshake.** A plotter accepts an intermediate
type, not a specific analyzer. The config and the intermediate are fully
decoupled — the same intermediate can be plotted with any valid config.

**Shared utils, not duplicated logic.** `validate_path`, `save_figure`,
histogram drawing, violin drawing — these live once in `plot_utils.py`,
`histogram_utils.py`, and `violin_utils.py`. Every plotter imports from
those. No plotter reimplements them.
