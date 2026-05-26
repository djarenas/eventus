# eventus.visualizers.events

Plotters for event result intermediates. Each plotter consumes one
`EventResult` subclass and one matching config object and produces one
or more plots. Plotters do not compute — the intermediate already
carries the result. Plotters do not validate data — the intermediate
already guarantees structural soundness.

---

## The pattern

Every plotter in this sub-package follows the same structure:

```python
plotter = EventResultVolumePlotter(volume, config)
plotter.plot_prevalence_bar("prevalence.png")
plotter.plot_count_distribution_bar("counts.png")
```

Constructor validates types only. All visual decisions live in the
config. Output path is validated at each plot method call.

---

## Plotters

### `EventResultVolumePlotter`

Plots event counts from an `EventResultVolume`.

```python
from eventus.visualizers.events import EventResultVolumePlotter
from eventus.visualizers.configs import EventResultVolumeConfig

config  = EventResultVolumeConfig.build_from_yaml("volume.yaml")
plotter = EventResultVolumePlotter(volume, config)
```

**Plot methods**

**`plot_prevalence_bar(path)`**

Three-bar chart showing % of cohort with any event, % with multiple
events, and % with none. Wilson confidence interval error bars are
drawn per bar when `config.bar.show_ci=True`. Percentage and count
labels are shown on each bar when `config.bar.show_pct_labels=True`.

```python
plotter.plot_prevalence_bar("prevalence.png")
```

**`plot_count_distribution_bar(path)`**

Discrete breakdown: one bar per integer count from n=0 up to
`config.count_bar.max_n - 1`, plus an overflow bar for n≥max_n.
Y-axis shows % of cohort (`show_as_pct=True`) or raw counts. Percentile
reference lines are snapped to the nearest bar centre.

```python
plotter.plot_count_distribution_bar("count_distribution.png")
```

---

### `EventResultTimingPlotter`

Plots nth-event timing from an `EventResultTiming`.

```python
from eventus.visualizers.events import EventResultTimingPlotter
from eventus.visualizers.configs import EventResultTimingConfig

config  = EventResultTimingConfig.build_from_yaml("timing.yaml")
plotter = EventResultTimingPlotter(timing, config)
```

**Plot methods**

**`plot_histogram(path)`**

Faceted histograms — one subplot per nth event up to `timing.max_n`,
stacked vertically and sharing the same x-axis scale. Each subplot
title shows the eligible denominator (entities with at least nth
events) and the percentage of the full cohort it represents.

The plotter resolves the histogram config for each nth via:
```python
config.histogram_per_n.get(nth, config.histogram)
```

This means you configure a base histogram for all nths and optionally
override specific ones — a different color for the second event, a
narrower range for the third.

```python
plotter.plot_histogram("timing.png")
```

---

### `EventResultShapePlotter`

Plots behavioral fingerprint statistics from an `EventResultShape`.

```python
from eventus.visualizers.events import EventResultShapePlotter
from eventus.visualizers.configs import EventResultShapeConfig

config  = EventResultShapeConfig.build_from_yaml("shape.yaml")
plotter = EventResultShapePlotter(shape, config)
```

**Plot methods**

**`plot_fingerprint(path)`**

Burstiness vs memory scatter plot — the behavioral fingerprint. Each
point is one entity. Quadrant reference lines at burstiness=0 and
memory=0 divide the space into four behavioral regions. Only entities
with n ≥ 4 events appear (memory requires at least 3 inter-event gaps).
The eligible count and percentage of cohort is shown in the subplot
title.

```python
plotter.plot_fingerprint("fingerprint.png")
```

Quadrant interpretation:

| Region | Burstiness | Memory | Pattern |
|---|---|---|---|
| Top-right | > 0 | > 0 | Bursty + persistent |
| Bottom-right | > 0 | < 0 | Bursty + alternating |
| Top-left | < 0 | > 0 | Regular + persistent |
| Bottom-left | < 0 | < 0 | Regular + alternating |

**`plot_center_of_mass(path)`**

Histogram of `center_of_mass` values across the cohort.
`center_of_mass` is normalized to [0, 1]: 0 = all events front-loaded,
0.5 = uniformly spread, 1 = all events back-loaded. Entities with 0
events (NaN) are excluded.

```python
plotter.plot_center_of_mass("center_of_mass.png")
```

**`plot_density(path)`**

Histogram of event density (`n / obs_duration_days`) across the cohort.
Entities with 0 events (NaN density) are excluded.

```python
plotter.plot_density("density.png")
```

**`plot_mean_gap_violin(path, violin_config=None)`**

Violin plot of mean inter-event gap across the cohort. Only entities
with at least 2 events appear (mean_gap requires at least one gap).
If `violin_config` is not provided, sensible defaults are used — one
teal violin, days on the y-axis, P25/P50/P75 lines.

```python
plotter.plot_mean_gap_violin("mean_gap.png")

# With explicit config
from eventus.visualizers.configs import ArraysViolinConfig
violin_cfg = ArraysViolinConfig.build_from_yaml("gap_violin.yaml")
plotter.plot_mean_gap_violin("mean_gap.png", violin_config=violin_cfg)
```

**`plot_mean_gap_violin_stratified(path, cohort_timeline, stratify_by, violin_config=None, max_groups=5)`**

Stratified violin of mean inter-event gap, grouped by a descriptor
column carried in the `CohortTimeline`. The descriptor column must be
declared in `EventSemantics.descriptor_cols` with `timeline != "none"`.

```python
plotter.plot_mean_gap_violin_stratified(
    path             = "gap_by_condition.png",
    cohort_timeline  = ct,
    stratify_by      = "icd10_condition",
)
```

Only groups with at least 2 valid `mean_gap` values are plotted. If
`violin_config` declares explicit `categories`, those keys determine
which groups are included and in what order. Otherwise all unique values
in `stratify_by` are included up to `max_groups` (default 5).

---

## Internal utils

| File | Contains |
|---|---|
| `event_result_plotter_utils.py` | Re-exports shared primitives from `plot_utils` and `histogram_utils` — event plotters import from here |
| `event_result_volume_plotter_utils.py` | `compute_prevalence()`, `compute_count_distribution()`, Wilson CI, bar drawing |
| `event_result_timing_plotter_utils.py` | `build_faceted_figure()`, `draw_nth_facet()` |
| `event_result_shape_plotter_utils.py` | `draw_fingerprint_scatter()`, `draw_distribution_histogram()` |

`event_result_plotter_utils.py` is a re-export façade — event plotters
import `validate_path`, `save_figure`, `apply_style`, `compute_bins`,
`draw_histogram`, `draw_percentile_lines`, and `resolve_x_limits` from
it, rather than importing directly from the parent module. This keeps
the import paths within the sub-package consistent and avoids coupling
the event plotters to the parent visualizers layout.

---

## Design notes

**One intermediate, one config, one plotter.** Each plotter class
accepts exactly one intermediate type. Type is checked at construction
and raises immediately with a clear message if the wrong object is
passed.

**Config defaults are always available.** Every plotter accepts `None`
as a config and substitutes the config class default. This makes
exploratory use frictionless — `EventResultVolumePlotter(volume).plot_prevalence_bar("out.png")`
works without any config setup.

**NaN means absent signal, not missing data.** Stats requiring a
minimum number of events (memory needs n ≥ 4, burstiness needs n ≥ 3,
mean_gap needs n ≥ 2) are NaN for entities below the threshold. Plotters
drop NaN values before drawing and report the eligible count in the
subplot title. This makes the denominator explicit rather than silent.
