# Plot Configuration System

## Design Philosophy

The system is built around two principles:

**1. Trust through construction.** If a config object exists, it is valid. All validation happens at construction time via `__post_init__`, so downstream plotting code never needs to defensive-check its inputs.

**2. Concept honesty.** Each class represents exactly one real concept. Classes do not absorb neighboring concerns for convenience. A labels class knows about labels. A style class knows about style. An axis class knows about axis behavior. This makes the hierarchy predictable and extensible.

---

## Architecture

### The 3-Layer Design

```
BasePlotConfig                          ← abstract base, enforces shared structure
    ↓ inherits
Concrete configs                        ← one per plot type
    ↓ composed of
Section dataclasses                     ← small, single-concern, validated
```

Each **concrete config** (e.g. `HistogramPlotConfig`) inherits from `BasePlotConfig` and composes section dataclasses for its own concerns (labels, axes, style, bins, etc.).

Each **section dataclass** (e.g. `HistogramStyleConfig`) is a plain validated dataclass. It knows nothing about YAML or its parent config — it just holds and validates data.

### `BasePlotConfig` — shared structure

`BasePlotConfig` does three things:
1. Enforces that every concrete config has a `general: CanvasConfig` section
2. Owns `build_from_yaml`, `build_from_dict`, `to_yaml`, `to_dict` — inherited for free by all concrete configs
3. Runs base validation in `__post_init__`; concrete configs call `super().__post_init__()` first, then add their own cross-section checks

```python
@dataclass
class BasePlotConfig:
    general: CanvasConfig = field(default_factory=CanvasConfig)

    def __post_init__(self):
        if not isinstance(self.general, CanvasConfig):
            raise TypeError(...)

    @classmethod
    def build_from_yaml(cls, path): ...

    @classmethod
    def build_from_dict(cls, data): ...

    def to_yaml(self, path): ...

    def to_dict(self): ...
```

### `CanvasConfig` — canvas fields

Lives under the `general:` key in every YAML. Represents the physical canvas that every plot is drawn on — nothing more.

| Field       | Type                    | Default        | Description             |
|-------------|-------------------------|----------------|-------------------------|
| `figsize`   | `tuple[float, float]`   | `(12.0, 7.0)`  | Figure width and height |
| `dpi`       | `int`                   | `120`          | Render resolution       |
| `font_size` | `int`                   | `12`           | Base font size          |

### Labels hierarchy

Three honest concepts, three classes. None bleeds into another.

```
BasePlotLabels                      ← "what is this plot called"
├── title:    str | None
└── subtitle: str | None
        ↓
AxisLabels(BasePlotLabels)          ← "what are the axes called"
├── xlabel:   str | None
└── ylabel:   str | None
        ↓
HistogramLabels(AxisLabels)         ← no extras yet
BarLabels(AxisLabels)               ← no extras yet
ScatterLabels(AxisLabels)           ← no extras yet
LineLabels(AxisLabels)              ← no extras yet
BoxLabels(AxisLabels)
└── group_label:    str | None
HeatmapLabels(AxisLabels)
└── colorbar_label: str | None
```

Plots without axes (e.g. a future pie chart) compose `BasePlotLabels` directly and never see `AxisLabels`. The hierarchy follows what plots actually have in common, not what is convenient to share.

### `AxisConfig` — axis display behavior

A separate concept from labels. `AxisLabels` answers "what are the axes called." `AxisConfig` answers "how do the axes behave visually." Composed into any concrete config that has axes; omitted by plots that don't.

| Field             | Type                | Default | Description                               |
|-------------------|---------------------|---------|-------------------------------------------|
| `x_ticks`         | `list[float]\|None` | `None`  | Explicit tick locations; `None` = auto    |
| `y_ticks`         | `list[float]\|None` | `None`  | Explicit tick locations; `None` = auto    |
| `x_tick_rotation` | `float`             | `0.0`   | Tick label rotation in degrees            |
| `y_tick_rotation` | `float`             | `0.0`   | Tick label rotation in degrees            |
| `x_tick_format`   | `str\|None`         | `None`  | Format string e.g. `"{:.0f}"`, `"%Y-%m"` |
| `y_tick_format`   | `str\|None`         | `None`  | Format string                             |

### Style hierarchy

`alpha` is the only truly universal style field. `color` and `show_grid` apply to axis-based plots. Edge-drawn plots (bars, histograms) add `edgecolor`. Plots that diverge significantly branch directly off the base.

```
BaseStyleConfig
└── alpha: float
        ↓
AxisStyleConfig(BaseStyleConfig)        ← axis-based plots
├── color:     str
└── show_grid: bool
        ↓
EdgeStyleConfig(AxisStyleConfig)        ← plots that draw bars/patches
└── edgecolor: str
        ↓
HistogramStyleConfig(EdgeStyleConfig)   ← no extras yet
BarStyleConfig(EdgeStyleConfig)         ← no extras yet

ScatterStyleConfig(AxisStyleConfig)
├── marker:     str
└── markersize: float

LineStyleConfig(AxisStyleConfig)
├── linewidth:  float
└── linestyle:  str

HeatmapStyleConfig(BaseStyleConfig)     ← branches off base directly
├── cmap:  str                          ← no single color, no show_grid
└── alpha: float  (inherited)
```

---

## File Layout

```
plot_config/
├── README.md
├── base_plot_config.py         ← BasePlotConfig, CanvasConfig, BasePlotLabels,
│                                  AxisLabels, AxisConfig, BaseStyleConfig,
│                                  AxisStyleConfig, EdgeStyleConfig
├── plot_config_utils.py        ← validation helpers, _DEFAULT_PALETTE
├── bins_config.py              ← BinsConfig + spec variants (standalone, reusable)
├── histogram_plot_config.py    ← HistogramPlotConfig + its section dataclasses
├── scatter_plot_config.py      ← ScatterPlotConfig + its section dataclasses
├── bar_plot_config.py          ← BarPlotConfig + its section dataclasses
├── line_plot_config.py         ← LinePlotConfig + its section dataclasses
├── box_plot_config.py          ← BoxPlotConfig + its section dataclasses
└── heatmap_plot_config.py      ← HeatmapPlotConfig + its section dataclasses
```

Each plot type owns its section dataclasses in its own file. Base classes live in `base_plot_config.py`. Concrete subclasses live alongside the config that uses them.

---

## For Users: Writing YAML Configs

Every concrete config maps directly to a YAML structure. Top-level keys are section names. Every plot has a `general` section. All sections are optional — omitting one uses its defaults entirely.

### Example — Histogram

```yaml
general:
  figsize: [10, 5]
  dpi: 150
  font_size: 12

bins:
  type: uniform
  n_bins: 10
  min: 0
  max: 365

labels:
  title: "Duration Distribution"
  xlabel: "Duration (days)"
  ylabel: "Count"

axes:
  x_tick_rotation: 45
  x_tick_format: "{:.0f}"

style:
  color: "#028090"
  edgecolor: "#FFFFFF"
  alpha: 0.85
  show_grid: true

percentile_lines:
  show: true
  values: [25, 50, 75, 90]
  color: "#333333"
  linestyle: dashed
  show_labels: true

stratification:
  style: overlay
  max_categories: 10
  colors:
    H01: "#028090"
    H02: "#E05C40"
```

### Loading and saving

```python
# Load from YAML
config = HistogramPlotConfig.build_from_yaml("my_config.yaml")

# Build from dict
config = HistogramPlotConfig.build_from_dict({
    "general": {"figsize": [10, 5], "dpi": 150},
    "bins": {"type": "uniform", "n_bins": 10, "min": 0, "max": 365},
    "style": {"color": "#028090"},
})

# Build with all defaults
config = HistogramPlotConfig()

# Save to YAML
config.to_yaml("output_config.yaml")
```

### Validation rules

Construction raises `ValueError` immediately on any of the following:

- `general.figsize` values are not both `> 0`
- `general.dpi` or `general.font_size` are `<= 0`
- Any `color` or `edgecolor` is not a valid hex string (`#RGB` or `#RRGGBB`)
- `alpha` is outside `[0.0, 1.0]`
- `bins.n_bins <= 0`
- `bins.min >= bins.max` when both are provided
- `bins.min <= 0` for `log` type
- `bins.edges` has fewer than 2 values or is not strictly increasing
- `percentile_lines.values` contains values outside `[0, 100]`
- `stratification.max_categories < 2`
- Any enum-like field (e.g. `linestyle`, `stratification.style`) receives an unknown value

A `UserWarning` (not an error) is issued when:

- `percentile_lines.show=False` but `values` or `show_labels` are configured
- A stratification category has no assigned color (auto-assigned from palette with warning)

---

## `BinsConfig` Reference

`BinsConfig` is standalone (`bins_config.py`) and can be imported by any plot config that needs binning.

### Bin types

| Type      | Key params               | When to use                                        |
|-----------|--------------------------|----------------------------------------------------|
| `auto`    | —                        | "I don't care, matplotlib figure it out"           |
| `uniform` | `n_bins`, `min?`, `max?` | "Give me ~10 bins between 0 and 365"               |
| `log`     | `n_bins`, `min?`, `max?` | Data spans orders of magnitude; `min` must be `>0` |
| `custom`  | `edges: list[float]`     | Full control; N edges produce N−1 bins             |

`uniform` is the primary workhorse. `min` and `max` are optional — when omitted they fall back to the data range at plot time. `n_bins` is a target, not a guarantee; matplotlib may adjust slightly for clean boundaries.

### Friendly constructors

```python
BinsConfig.auto()
BinsConfig.uniform(n_bins=10, min=0, max=365)
BinsConfig.uniform(n_bins=20)                    # min/max from data
BinsConfig.log(n_bins=20, min=1, max=10_000)
BinsConfig.custom(edges=[0, 10, 25, 50, 100, 365])

# From dict — used internally by build_from_dict / YAML loading
BinsConfig.from_dict({"type": "uniform", "n_bins": 10, "min": 0, "max": 365})
BinsConfig.from_dict(None)                       # → BinsConfig.auto()
```

### Relationship to `AxisConfig` ticks

Bin edges and tick locations are **independent concerns**:

- `BinsConfig` controls where bars are cut — a data/computation concern.
- `AxisConfig.x_ticks` controls what numbers appear on the axis — a display concern.

You may have bins every 7 days but ticks every 30. Or use `custom` edges and set `x_ticks` to a subset of those edges for a clean aligned look. Neither field affects the other.

---

## For Developers: Adding a New Plot Config

Follow these steps to add a new plot type. `HistogramPlotConfig` is the reference implementation.

**1. Create `<name>_plot_config.py`**

**2. Define section dataclasses** for this plot's specific concerns. Subclass from the right base:

- Labels: `AxisLabels` for anything with x/y axes; `BasePlotLabels` for plots without
- Style: `EdgeStyleConfig` → bars/patches, `AxisStyleConfig` → lines/scatter, `BaseStyleConfig` → heatmap/other
- Single-section validation stays in the section's own `__post_init__`
- Cross-section validation goes in the concrete config's `__post_init__`

**3. Define the concrete config**, inheriting `BasePlotConfig`:

```python
@dataclass
class MyPlotConfig(BasePlotConfig):
    # --- Inherited from BasePlotConfig ---
    # general: CanvasConfig      ← figsize, dpi, font_size

    # --- Own fields ---
    labels: MyLabels   = field(default_factory=MyLabels)
    axes:   AxisConfig = field(default_factory=AxisConfig)
    style:  MyStyle    = field(default_factory=MyStyle)

    _PREFIX: ClassVar[str] = "MyPlotConfig"   # used in all error messages

    def __post_init__(self):
        super().__post_init__()               # always call this first
        # cross-section validation here if needed
```

**4. Checklist before merging:**
- [ ] All fields have defaults (required for dataclass inheritance to work)
- [ ] `__post_init__` calls `super().__post_init__()` as its first line
- [ ] Every constrained field raises `ValueError` with a `[PREFIX]` message on bad input
- [ ] `build_from_yaml`, `build_from_dict`, and `to_yaml` work without modification (inherited — verify, don't rewrite)
- [ ] Constructing with zero arguments produces a valid object
- [ ] Labels and style subclasses are the most specific honest fit — not over-inheriting
- [ ] Added an example YAML block to this README
