# eventus.visualizers.occurrences

Plotters for occurrence result intermediates. Each plotter consumes one
validated result object and one config object and produces one or more
plots. No computation happens here — the intermediate already carries
everything needed.

---

## Structure

```
occurrences/
    occurrence_result_plotter_utils.py      — shared drawing primitives
    occurrence_result_volume_plotter.py     — OccurrenceResultVolumePlotter
    occurrence_result_volume_plotter_utils.py
    occurrence_result_timing_plotter.py     — OccurrenceResultTimingPlotter
    occurrence_result_timing_plotter_utils.py
    occurrence_result_shape_plotter.py      — OccurrenceResultShapePlotter
    occurrence_result_shape_plotter_utils.py
```

`occurrence_result_plotter_utils.py` is the shared backbone — every
plotter in this subfolder draws on it for path validation, style
application, histogram drawing, percentile lines, bin computation, and
figure saving. Plotter-specific utils handle only what is unique to
that plotter.

---

## The pattern

All three plotters follow the same structure:

```
OccurrenceResult*                    — validated intermediate
    ↓
OccurrenceResult*Plotter             — accepts intermediate + config
    ↓                                  delegates drawing to utils
occurrence_result_*_plotter_utils    — domain-specific drawing logic
    ↓
occurrence_result_plotter_utils      — shared primitives
    ↓
matplotlib → plot.png
```

The plotter does not compute — the intermediate already guarantees
structural soundness. The plotter does not make visual decisions —
the config owns all of those. The plotter wires them together and
delegates.

---

## `OccurrenceResultVolumePlotter`

Plots occurrence volume statistics from an `OccurrenceResultVolume`.

```python
from eventus.visualizers.occurrences import OccurrenceResultVolumePlotter
from eventus.visualizers.configs import OccurrenceResultVolumeConfig

config  = OccurrenceResultVolumeConfig.build_from_yaml("volume.yaml")
plotter = OccurrenceResultVolumePlotter(volume, config)
```

### Plot methods

**`plot_prevalence_bar(path)`**

Bar chart showing percentage of cohort with any occurrence, multiple
occurrences, and no occurrences. Wilson confidence intervals are drawn
on each bar when `config.bar.show_ci=True`. Percentage and count labels
are shown above each bar when `config.bar.show_pct_labels=True`.

```python
plotter.plot_prevalence_bar("prevalence.png")
```

**`plot_count_distribution_bar(path)`**

Discrete breakdown of occurrence counts per entity — one bar for n=0,
n=1, ... n=max_n-1, and a final overflow bar for n≥max_n. Percentile
reference lines are snapped to the nearest bar position. Y-axis shows
percentage of cohort (`show_as_pct=True`) or raw entity counts.

```python
plotter.plot_count_distribution_bar("count_distribution.png")
```

### Config

`OccurrenceResultVolumeConfig` is an orchestrator — each attribute
owns the full configuration for exactly one plot method.

| Attribute | Class | Plot method |
|---|---|---|
| `bar` | `CategoryBarConfig` | `plot_prevalence_bar()` |
| `count_bar` | `CountDistributionBarConfig` | `plot_count_distribution_bar()` |

```python
config = OccurrenceResultVolumeConfig.build_from_dict({
    "canvas":    {"figsize": [10, 5]},
    "bar":       {"color_any": "#028090", "show_ci": True},
    "count_bar": {"max_n": 10, "show_as_pct": True},
})
```

---

## `OccurrenceResultTimingPlotter`

Plots occurrence timing statistics from an `OccurrenceResultTiming`.

```python
from eventus.visualizers.occurrences import OccurrenceResultTimingPlotter
from eventus.visualizers.configs import OccurrenceResultTimingConfig

config  = OccurrenceResultTimingConfig.build_from_yaml("timing.yaml")
plotter = OccurrenceResultTimingPlotter(timing, config)
```

### Plot methods

**`plot_histogram(path)`**

Faceted histograms — one subplot per nth occurrence from 1 to max_n,
stacked vertically and sharing the same x-axis scale. Each subplot
shows time_to_{nth} for entities with at least nth occurrences, with
the eligible count and percentage in the subplot title.

```python
plotter.plot_histogram("timing_histograms.png")
```

The shared x-axis scale is computed across all nths from the base
`histogram.bins` config. Per-nth overrides in `histogram_per_n` change
color and style but not the shared scale — the x-axis is never mutated
after drawing.

### Config

`OccurrenceResultTimingConfig` owns a base histogram config and
optional per-nth overrides.

```python
config = OccurrenceResultTimingConfig.build_from_dict({
    "canvas": {"figsize": [8, 12]},
    "histogram": {
        "bins":  {"type": "uniform", "n_bins": 52, "min": 0, "max": 365},
        "style": {"color": "#028090"},
    },
    "histogram_per_n": {
        2: {"style": {"color": "#E05C40"}},
        3: {"style": {"color": "#6B4FA0"}},
    },
    "facet": {"facet_height": 3.0, "facet_width": 6.0},
})
```

The plotter resolves the right config for each nth at draw time:
```python
hist_cfg = cfg.histogram_per_n.get(nth, cfg.histogram)
```

---

## `OccurrenceResultShapePlotter`

Plots occurrence behavioral fingerprint statistics from an
`OccurrenceResultShape`.

```python
from eventus.visualizers.occurrences import OccurrenceResultShapePlotter
from eventus.visualizers.configs import OccurrenceResultShapeConfig

config  = OccurrenceResultShapeConfig.build_from_yaml("shape.yaml")
plotter = OccurrenceResultShapePlotter(shape, config)
```

### Plot methods

**`plot_fingerprint(path)`**

Scatter plot of burstiness (x-axis) vs memory (y-axis) — the
behavioral fingerprint. Each point is one entity. Quadrant lines divide
the space into four behavioral regions:

| Quadrant | Burstiness | Memory | Interpretation |
|---|---|---|---|
| Top-right | > 0 | > 0 | Bursty and persistent |
| Bottom-right | > 0 | < 0 | Bursty and alternating |
| Top-left | < 0 | > 0 | Regular and persistent |
| Bottom-left | < 0 | < 0 | Regular and alternating |

Only entities with n ≥ 4 occurrences appear — memory requires at least
3 inter-occurrence gaps. The eligible count is shown in the title.

```python
plotter.plot_fingerprint("fingerprint.png")
```

**`plot_center_of_mass(path)`**

Histogram of center_of_mass values across the cohort. Center of mass
is normalized to [0, 1] — 0 means all occurrences cluster at obs_start,
1 means they cluster at obs_end, 0.5 means uniformly spread. Entities
with 0 occurrences (NaN) are excluded.

```python
plotter.plot_center_of_mass("center_of_mass.png")
```

**`plot_density(path)`**

Histogram of occurrence density across the cohort. Density = n /
obs_duration_days per entity. Entities with 0 occurrences (NaN) are
excluded.

```python
plotter.plot_density("density.png")
```

### Config

`OccurrenceResultShapeConfig` is an orchestrator — each attribute owns
the full configuration for exactly one plot method. The canvas is
shared across all three.

| Attribute | Class | Plot method |
|---|---|---|
| `center_of_mass` | `HistogramPlotConfig` | `plot_center_of_mass()` |
| `density` | `HistogramPlotConfig` | `plot_density()` |
| `scatter` | `ShapeScatterConfig` | `plot_fingerprint()` |

```python
config = OccurrenceResultShapeConfig.build_from_dict({
    "canvas":  {"figsize": [10, 7]},
    "scatter": {
        "color":               "#028090",
        "show_quadrant_lines": True,
        "quadrant_line_color": "#AAAAAA",
    },
    "center_of_mass": {
        "bins":  {"type": "uniform", "n_bins": 20, "min": 0.0, "max": 1.0},
        "style": {"color": "#028090"},
    },
    "density": {
        "bins":  {"type": "uniform", "n_bins": 20, "min": 0.0},
        "style": {"color": "#6B4FA0"},
    },
})
```

---

## Shared primitives — `occurrence_result_plotter_utils`

Every plotter in this subfolder draws on these shared functions.
They are internal — import them from the plotter classes, not directly.

| Function | Purpose |
|---|---|
| `validate_path` | Check output file extension |
| `apply_style` | Apply font sizes and title to figure |
| `compute_bins` | Derive bin edges from `BinsConfig` and data |
| `draw_histogram` | Draw a histogram on an `Axes` |
| `draw_percentile_lines` | Draw vertical percentile reference lines |
| `resolve_x_limits` | Compute shared x limits across multiple series |
| `save_figure` | Save and close a figure |

**`compute_bins` and `resolve_x_limits`** are the most important.
`compute_bins` handles all four bin types — `auto`, `uniform`, `log`,
`custom` — against the actual data at draw time. `resolve_x_limits`
respects explicit bounds from the bins config first, falls back to data
range otherwise. This is how shared x-axis scales across facets are
computed without mutating any config.

---

## Design notes

**One intermediate, one plotter, one config.** Each plotter accepts
exactly one intermediate type and exactly one config type. The types
are checked at construction — if a plotter exists, its inputs are
already valid.

**Orchestrator configs, multiple plot methods.** `OccurrenceResultShapeConfig`
and `OccurrenceResultTimingConfig` own sub-configs per plot method.
One YAML file configures an entire analytical suite. Each method gets
its own independently tunable config. The canvas is shared for visual
consistency.

**Per-nth override resolution at draw time.** `OccurrenceResultTimingPlotter`
resolves `cfg.histogram_per_n.get(nth, cfg.histogram)` at draw time,
not at construction. The config is never mutated. Overrides change
color and style; the shared x-axis scale is computed independently
from the base bins config.

**Eligible denominators are explicit.** Every plot that excludes
entities due to insufficient data (n < threshold) shows the eligible
count and percentage of cohort in the subplot title. The denominator
is always visible.
