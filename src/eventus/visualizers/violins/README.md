# eventus.visualizers.violins

Violin plotters for episode duration and coverage analysis. All plotters
in this sub-package delegate drawing entirely to `ArraysViolinPlotter`
— the one class that knows how to draw a violin from a
`{key: np.ndarray}` dict. The higher-level plotters are responsible for
building those arrays from their respective intermediates and for
applying any domain-specific logic (unit conversion, coverage-specific
tick labels) before handing off.

---

## The pattern

```
Intermediate / data source
    ↓
Higher-level plotter      — builds arrays, validates, delegates
    ↓
ArraysViolinPlotter       — validates arrays, draws, saves
    ↓
plot.png
```

This means `ArraysViolinPlotter` can also be used directly whenever
you have pre-built arrays — from `EpisodeDurationResult.build_arrays()`,
from `EventResultShapePlotter.plot_mean_gap_violin()`, or from any
custom array you build yourself.

---

## Plotters

### `ArraysViolinPlotter`

The core violin plotter. Receives a `{key: np.ndarray}` dict and an
`ArraysViolinConfig` and draws one violin per key.

```python
from eventus.visualizers.violins import ArraysViolinPlotter
from eventus.visualizers.configs import ArraysViolinConfig

arrays = {
    "all_data":   durations_all,
    "Hospital_A": durations_a,
    "Hospital_B": durations_b,
}
config  = ArraysViolinConfig.build_from_yaml("violin.yaml")
plotter = ArraysViolinPlotter(arrays, config)
plotter.plot("durations.png")
```

**Construction validation**

The constructor validates every array before any drawing happens:

- All keys must be non-empty strings
- All values must be convertible to 1-D numeric arrays
- NaN and inf values are dropped automatically; a warning is issued if
  more than 20% of values are dropped from any array
- Arrays with fewer than 2 finite values are skipped with a warning
- Arrays where all values are identical produce a warning (violin
  degenerates to a line)
- Config keys not present in arrays are skipped with a warning
- Array keys not in config categories are auto-colored from the default
  palette with a warning

**Plot order**

Config-defined order comes first, then any extra keys not in the config,
appended alphabetically. Define `categories` in the config to control
order explicitly — first defined is leftmost violin.

**`plot(path)`**

```python
plotter.plot("output.png")
```

Path must end in `.png`, `.jpg`, or `.jpeg`. Parent directory must exist.

---

### `EpisodeDurationViolinPlotter`

Violin plot of episode durations from an `EpisodeDurationResult`.
Delegates all drawing to `ArraysViolinPlotter`. Uses
`ArraysViolinConfig` for all visual settings.

```python
from eventus.visualizers.violins import EpisodeDurationViolinPlotter
from eventus.visualizers.configs import ArraysViolinConfig

config  = ArraysViolinConfig.build_from_yaml("duration_violin.yaml")
plotter = EpisodeDurationViolinPlotter(result, config)
plotter.plot("durations.png")
```

**Stratification**

Pass `stratify_by` to split durations by a descriptor column. The
column must have been included in `descriptor_cols` when running
`EpisodeDurationAnalyzer`.

```python
# Analyzer must carry the column through
result = EpisodeDurationAnalyzer(
    episodes,
    descriptor_cols=["hospital_id"],
).calc()

plotter = EpisodeDurationViolinPlotter(
    result,
    config,
    stratify_by="hospital_id",
)
plotter.plot("durations_by_hospital.png")
```

`build_arrays(stratify_by)` is called on the result internally — one
array per unique category value, plus `"all_data"` always first. The
config's `categories` dict controls colors and display labels per key.
Missing keys are auto-colored with a warning.

**`plot(path)`**

```python
plotter.plot("durations.png")
```

---

### `EpisodeCoverageViolinPlotter`

Violin plots from a `CohortTimeline` that already has episode coverage
analysis columns. The timeline must have been enriched with
`CohortTimelineEpisodeAnalyzer.enrich_with_episode_coverage()` first.
Uses `ArraysViolinConfig` for all visual settings.

```python
from eventus.visualizers.violins import EpisodeCoverageViolinPlotter
from eventus.visualizers.configs import ArraysViolinConfig

# Enrich timeline first
ct      = CohortTimelineEpisodeAnalyzer(ct, "inpatient_hospitalization").enrich_with_episode_coverage()
config  = ArraysViolinConfig.build_from_yaml("coverage_violin.yaml")
plotter = EpisodeCoverageViolinPlotter(ct, identity="inpatient_hospitalization", config=config)
```

**Plot methods**

**`plot_total(path)`**

Two-violin plot: `active_days` vs `inactive_days`. Both metrics include
all entities — zero is valid and meaningful (an entity with no episodes
has 0 active days).

```python
plotter.plot_total("total_coverage.png")
```

**`plot_inactive_breakdown(path)`**

Up to three violins showing the breakdown of inactive days:
- `inactive_days_before_first_episode` — gap before coverage begins
- `inactive_days_after_last_episode` — gap after coverage ends
- `inactive_days_middle` — gaps between episodes

Each violin is filtered to entities where that metric > 0. Metrics with
no positive values are silently omitted.

```python
plotter.plot_inactive_breakdown("inactive_breakdown.png")
```

**Unit conversion**

Both methods read `config.labels.units` and convert day values
automatically. Valid units: `"days"` (default, no conversion),
`"months"` (÷ 30.44), `"years"` (÷ 365.25).

```python
config = ArraysViolinConfig.build_from_dict({
    "labels": {"title": "Coverage duration", "units": "months"},
})
```

**Tick labels**

`EpisodeCoverageViolinPlotter` adds coverage-specific tick labels that
show the key name, n, and percentage of the total cohort — e.g.
`"active_days\nn=487 (97.4%)"`. This is different from
`ArraysViolinPlotter`'s default tick labels, which show key name and n
only.

---

## Internal utils

| File | Contains |
|---|---|
| `arrays_violin_plotter_utils.py` | Re-exports shared primitives from `violin_utils.py` (in this subfolder) — `draw_violin_body`, `draw_box`, `draw_points`, `draw_percentile_lines`, `compute_widths`, `apply_y_bounds`, `build_tick_labels` |
| `episode_coverage_violin_plotter_utils.py` | `build_total_arrays()`, `build_breakdown_arrays()`, `resolve_divisor()`, `apply_unit_conversion()`, plus re-export of `build_tick_labels_with_pct` |

The shared drawing primitives all live in
`eventus.visualizers.violins.violin_utils`. The utils files in this
sub-package are re-export façades that keep import paths within the
sub-package consistent.

---

## Design notes

**`ArraysViolinPlotter` is the only class that draws.** Higher-level
plotters build arrays and delegate. This means the drawing logic is
tested once in one place, and new violin use cases only require building
the right arrays.

**Config defaults are always available.** Every plotter accepts `None`
as a config and substitutes `ArraysViolinConfig()` defaults. This makes
exploratory use frictionless.

**`EpisodeCoverageViolinPlotter` uses `ArraysViolinConfig`, not a
dedicated config class.** The coverage-specific behavior (unit
conversion, percentage tick labels) is handled in the plotter itself,
not in a separate config hierarchy. `ArraysViolinConfig` provides all
the visual control needed.
