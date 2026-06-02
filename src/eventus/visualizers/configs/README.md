# eventus.visualizers.configs

Modular, configuration-driven plotting for eventus intermediates.
Every visual decision lives in a versioned, validated config object —
not in code. A config file is a complete, reproducible description of
a plot. Hand someone a YAML file and they know exactly what was plotted
and how.

---

## The problem visualizers solve

A typical data science visualization workflow embeds visual choices
directly in code — colors, bin widths, axis ranges, tick formats,
figure sizes. These choices are invisible to anyone reading the
analysis later. They cannot be versioned, shared, or reproduced without
reading the script line by line.

eventus visualizers separate the *what* from the *how*. The plotter
knows how to draw. The config knows what to draw. The intermediate
carries the data. None of the three knows about the others' concerns.

---

## The pipeline

```
Intermediate                      — validated result object
    ↓
Config (YAML or code)             — every visual decision, validated
    ↓                               at construction, round-trippable
Plotter                           — consumes one intermediate and
    ↓                               one config, produces one plot
plot.png / plt.show()
```

The intermediate and the config are independent. An `EventResultShape`
can be plotted with a default config, a custom config loaded from YAML,
or a config built programmatically. The plotter does not care how the
config was built — only that it is valid.

---

## Config architecture

The config system is built on two principles stated explicitly in the
configs README:

**Trust through construction.** If a config object exists, it is valid.
All validation happens at `__post_init__`. Downstream plotting code
never needs to defensive-check its inputs.

**Concept honesty.** Each class represents exactly one real concept.
A labels class knows about labels. A style class knows about style. An
axis class knows about axis behavior. No class absorbs a neighboring
concern for convenience.

### The hierarchy

```
BasePlotConfig                    — abstract base
    ↓ inherits
Concrete configs                  — one per plot type
    ↓ composed of
Section dataclasses               — small, single-concern, validated
```

`BasePlotConfig` does three things and nothing else: enforces that
every config has a `CanvasConfig`, owns `build_from_yaml /
build_from_dict / to_yaml / to_dict` for free inheritance, and runs
base validation. Every concrete config calls `super().__post_init__()`
first, then adds its own cross-section checks.

### The shared building blocks

**`CanvasConfig`** — the physical canvas every plot is drawn on.
figsize, dpi, font_size. Nothing else.

**Labels hierarchy** — three honest concepts, three classes:

```
BasePlotLabels          — title, subtitle
    ↓
AxisLabels              — + xlabel, ylabel, units
    ↓
HistogramLabels         — no extras yet
StackedTimelineLabels   — + title_font_size
```

Plots without axes compose `BasePlotLabels` directly. The hierarchy
follows what plots actually have in common.

**`AxisConfig`** — how axes behave visually. Tick locations, rotation,
format strings. Separate from `AxisLabels` because "what are the axes
called" and "how do the axes look" are different concerns.

`TimelineAxisConfig` extends `AxisConfig` with date-aware tick control:
`mode` (`auto`/`calendar`/`normalized`), `unit` (`days`/`months`/`years`),
`interval`, and `format`. Used only by `StackedTimelineConfig`.

**Style hierarchy** — alpha is the only truly universal style field:

```
BaseStyleConfig         — alpha
    ↓
AxisStyleConfig         — + color, show_grid
    ↓
EdgeStyleConfig         — + edgecolor
    ↓
HistogramStyleConfig    — no extras yet
```

**`PercentilesConfig`** — reference lines at chosen percentile values.
Composable into any config that needs them — histograms, violins,
count distributions.

**`CategoryConfig`** — visual identity for one category: color and
optional display label. Used wherever plots stratify by group.

**`ViolinAxisConfig`** — axis config for violin plots, extending `AxisConfig` with
optional `y_min` and `y_max` bounds. Lives in `violin_axis_config.py` and is
shared by all violin configs. Separate from `AxisConfig` because violins
frequently need hard y-axis clamping that other plot types do not.

**`ViolinStyleConfig`** — visual style for violin plots: bandwidth method,
box display, point overlay, and `max_categories` limit. Lives in
`violin_style_config.py` and is shared by `ArraysViolinConfig`,
`BaseViolinConfig`, and `EpisodeDurationViolinConfig`.

**`BinsConfig`** — standalone, composable binning configuration.
Four bin types with friendly alternative constructors:

```python
BinsConfig.auto()
BinsConfig.uniform(n_bins=20, min=0, max=365)
BinsConfig.log(n_bins=20, min=1, max=10_000)
BinsConfig.custom(edges=[0, 10, 25, 50, 100, 365])
BinsConfig.from_dict({"type": "uniform", "n_bins": 20})
```

`BinsConfig` and `AxisConfig.x_ticks` are independent concerns. Bins
control where bars are cut — a data concern. Ticks control what numbers
appear on the axis — a display concern. You may have bins every 7 days
but ticks every 30.

---

## Concrete configs

### `StackedTimelineConfig`

Configuration for `StackedTimelinePlotter`. Draws one horizontal bar
per entity, with episode coverage layers and event markers overlaid.

```python
from eventus.visualizers.configs import StackedTimelineConfig

config = StackedTimelineConfig.build_from_yaml("timeline.yaml")
```

Note: `StackedTimelineConfig` raises at construction if neither `episodes`
nor `events` contains at least one layer — a config with no layers is not
valid. Always provide at least one entry in `episodes` or `events`.

**Sections**

| Section | Class | Controls |
|---|---|---|
| `canvas` | `CanvasConfig` | figsize, dpi, font_size |
| `labels` | `StackedTimelineLabels` | title, subtitle, title_font_size |
| `layout` | `LayoutConfig` | row height, bar height, entity labels, jitter |
| `x_axis` | `TimelineAxisConfig` | mode (auto/calendar/normalized), tick unit and interval |
| `poi` | `POIConfig` | observation period bar colors — before/active/gap/after |
| `episodes` | `list[EpisodeLayerConfig]` | one entry per episode identity — color, alpha, label |
| `events` | `list[EventLayerConfig]` | one entry per event identity — color, marker, size |
| `legend` | `LegendConfig` | show, location, font size, outside placement |

**YAML example**

```yaml
canvas:
  figsize: [18, 10]
  dpi: 120

layout:
  row_height: 0.6
  max_entities: 50
  jitter: false

x_axis:
  mode: calendar
  unit: months
  interval: 3
  format: "%Y-%m"

poi:
  color_before:    "#9E9E9E"
  color_middle:    "#F44336"
  color_after:     "#BDBDBD"
  color_no_episodes: "#EEEEEE"

episodes:
  - identity: inpatient_hospitalization
    color:    "#028090"
    label:    "Inpatient"
  - identity: medicaid_coverage
    color:    "#6B4FA0"
    label:    "Coverage"

events:
  - identity: ed_visit
    color:    "#E05C40"
    marker:   circle
    size:     6
    label:    "ED visit"

legend:
  show:    true
  outside: true
```

---

### `ActivityOverTimeConfig`

Configuration for `ActivityOverTimePlotter`. Two-panel plot: top panel
shows percentage of cohort with active episode coverage over time; bottom
panel shows entities entering and exiting coverage.

```python
from eventus.visualizers.configs import ActivityOverTimeConfig

config = ActivityOverTimeConfig.build_from_yaml("activity.yaml")
```

**Sections**

| Section | Class | Controls |
|---|---|---|
| `canvas` | `CanvasConfig` | figsize, dpi, font_size |
| `labels` | `AxisLabels` | title, subtitle, axis labels |
| `time` | `TimeConfig` | x_unit, x_interval, matplotlib style |
| `axes` | `AxisConfig` | tick locations, rotation, format |
| `line_style` | `ActivityLineStyleConfig` | line color, alpha, fill, linewidth |
| `flow_style` | `FlowStyleConfig` | bottom panel mode (bar/scatter), entered/exited colors |
| `layout` | `ActivityLayoutConfig` | relative height of top vs bottom panel |

---

### `HistogramPlotConfig`

General-purpose histogram configuration. Composable into any plotter
that needs histogram-style plots.

```python
from eventus.visualizers.configs import HistogramPlotConfig

config = HistogramPlotConfig.build_from_yaml("histogram.yaml")
config = HistogramPlotConfig.build_from_dict({
    "canvas": {"figsize": [10, 5]},
    "bins":   {"type": "uniform", "n_bins": 20, "min": 0, "max": 365},
    "style":  {"color": "#028090"},
})
```

**Sections:** `canvas`, `bins`, `labels`, `axes`, `style`,
`percentile_lines`, `stratification`.

The `stratification` section controls optional overlaid or faceted
breakdowns by a grouping column. Category colors are configured per
key; missing keys are auto-assigned from the default palette with a
warning.

---

### `EventResultVolumeConfig`

Configuration for `EventResultVolumePlotter`. Acts as an
orchestrator — each attribute owns the full configuration for exactly
one plot method.

```python
config = EventResultVolumeConfig.build_from_yaml("volume.yaml")
```

| Attribute | Class | Plot method |
|---|---|---|
| `bar` | `CategoryBarConfig` | `plot_prevalence_bar()` |
| `count_bar` | `CountDistributionBarConfig` | `plot_count_distribution_bar()` |

`CountDistributionBarConfig` renders one bar per integer count value
from n=0 to max_n-1, plus an overflow bar for n≥max_n. Percentile
lines are snapped to the nearest bar position.

---

### `EventResultTimingConfig`

Configuration for `EventResultTimingPlotter`. Orchestrates
histogram configs per nth event, with per-nth overrides.

```python
config = EventResultTimingConfig.build_from_yaml("timing.yaml")
```

The plotter resolves the right config for each nth via:
```python
cfg.histogram_per_n.get(nth, cfg.histogram)
```

This means you can configure a base histogram for all nths, then
override specific ones — a different color for the second event,
a narrower range for the third.

```python
config = EventResultTimingConfig.build_from_dict({
    "histogram": {
        "bins":  {"type": "uniform", "n_bins": 52, "min": 0, "max": 365}
    },
    "histogram_per_n": {
        2: {"style": {"color": "#E05C40"}},
        3: {"style": {"color": "#6B4FA0"}},
    },
})
```

---

### `EventResultShapeConfig`

Configuration for `EventResultShapePlotter`. Orchestrates three
distinct plot methods from one config object. The canvas is shared
across all three.

```python
config = EventResultShapeConfig.build_from_yaml("shape.yaml")
```

| Attribute | Class | Plot method |
|---|---|---|
| `center_of_mass` | `HistogramPlotConfig` | `plot_center_of_mass()` |
| `density` | `HistogramPlotConfig` | `plot_density()` |
| `scatter` | `ShapeScatterConfig` | `plot_fingerprint()` |

`plot_fingerprint()` draws the behavioral fingerprint scatter plot —
burstiness on the x-axis, memory on the y-axis. Quadrant lines divide
the space into four behavioral regions. Each entity is one point.

---

### `EpisodeDurationViolinConfig`

Configuration for `EpisodeDurationViolinPlotter`. Built on
`BaseViolinConfig` — adds a `stratify_by` column name that tells the
plotter which column in `EpisodeDurationResult.data` to group by.

```python
from eventus.visualizers.configs import EpisodeDurationViolinConfig

config = EpisodeDurationViolinConfig.build_from_dict({
    "stratify_by": "hospital_id",
    "stratify": {
        "all_data": {"color": "#AAAAAA", "label": "All"},
        "H01":      {"color": "#028090", "label": "North"},
    },
})
```

The reserved key `"all_data"` always plots first if present. Missing
keys are auto-assigned from the default palette with a warning.

---

### `ArraysViolinConfig`

Configuration for `ArraysViolinPlotter`. The plotter receives a
pre-built `{key: np.ndarray}` dict and draws one violin per key. This
config controls all visual aspects — category colors, labels, bandwidth,
percentile lines, axis bounds.

```python
config = ArraysViolinConfig.build_from_dict({
    "labels": {"title": "Duration by site", "units": "days"},
    "categories": {
        "all_data":   {"color": "#AAAAAA", "label": "All"},
        "Hospital_A": {"color": "#028090", "label": "North"},
        "Hospital_B": {"color": "#E05C40", "label": "South"},
    },
})
```

Plot order is determined by the order categories are defined — first
defined is leftmost violin. Missing keys are auto-assigned from the
default palette with a warning.

---

## YAML round-trip

Every config can be saved and reloaded exactly:

```python
config = StackedTimelineConfig.build_from_yaml("timeline.yaml")
config.to_yaml("timeline_copy.yaml")   # identical to the original

# Or build from code and save for the record
config = HistogramPlotConfig.build_from_dict({...})
config.to_yaml("methods/histogram_config_2024_01.yaml")
```

The YAML file is the record of every visual decision made in an
analysis. It can be version-controlled, shared with collaborators, and
used to reproduce any plot exactly.

---

## Plotters

Plotters consume one intermediate and one config. They do not validate
data — the intermediate already guarantees structural soundness. They do
not make visual decisions — the config already owns all of those.

| Plotter | Intermediate | Config |
|---|---|---|
| `StackedTimelinePlotter` | `CohortTimeline` | `StackedTimelineConfig` |
| `ActivityOverTimePlotter` | `EpisodeActivityOverTime` | `ActivityOverTimeConfig` |
| `EpisodeDurationHistogramPlotter` | `EpisodeDurationResult` | `EpisodeDurationPlotConfig` |
| `EpisodeDurationViolinPlotter` | `EpisodeDurationResult` | `EpisodeDurationViolinConfig` |
| `EventResultVolumePlotter` | `EventResultVolume` | `EventResultVolumeConfig` |
| `EventResultTimingPlotter` | `EventResultTiming` | `EventResultTimingConfig` |
| `EventResultShapePlotter` | `EventResultShape` | `EventResultShapeConfig` |
| `ArraysViolinPlotter` | `dict[str, np.ndarray]` | `ArraysViolinConfig` |

---

## Design notes

**Config is the methods section.** Every visual decision — colors, bin
widths, axis ranges, tick formats, figure sizes — lives in a versioned
YAML file. The config file is a complete, human-readable description of
what was plotted and how. This is reproducibility at the visualization
layer.

**Concept honesty over convenience.** Every section dataclass
represents exactly one real concept. `AxisLabels` knows about labels.
`AxisConfig` knows about axis behavior. `BinsConfig` knows about
binning. No class absorbs a neighboring concern because it would be
convenient to share. The result is a hierarchy that is predictable,
extensible, and honest.

**Orchestrator configs.** Some configs — `EventResultShapeConfig`,
`EventResultTimingConfig`, `EventResultVolumeConfig` — act as
orchestrators. Each attribute owns the full configuration for exactly
one plot method. This means one YAML file configures an entire
analytical visualization suite, and each method gets its own
independently tunable config.

**Validation at construction, not at plot time.** If a config exists,
it is valid. Plotters never defensive-check their config inputs.
Errors surface immediately when the config is built — not silently
at plot time when the figure is half-drawn.

**The intermediate is the handshake.** A plotter accepts an intermediate
type, not a specific analyzer. Any analyzer that produces an
`EventResultShape` can feed `EventResultShapePlotter`. The
config and the intermediate are fully decoupled — the same intermediate
can be plotted with a default config, a saved config from a previous
analysis, or a new config built for a different publication.
