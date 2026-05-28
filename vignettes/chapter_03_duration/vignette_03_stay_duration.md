# Chapter 3 — Distribution of Episode Durations

## Vignette: Stay Duration Analysis

You have 227 clean nursing facility stays across 200 residents. Your
clinical collaborator asks: *"How long were the stays?"* You reach for
matplotlib. Before you write a single line of plotting code, you need to
answer a question that sounds trivial: *"What exactly am I plotting, and
will I be able to reproduce it?"*

---

### The four problems

**Problem 1 — Bin width is a scientific choice.** A 7-day bin aligns
with clinical discharge patterns. A 30-day bin hides variation. A 1-day
bin shows noise. That choice belongs in your methods section — not buried
in `bins=range(0, 200, 7)` on line 34 of a script.

**Problem 2 — Percentile lines require decisions too.** Which
percentiles — 25th, 50th, 75th, 90th? Do you label them? At what font
size? A script that hardcodes `np.percentile(durations, [25, 50, 75])`
has made all of these choices silently.

**Problem 3 — The KDE bandwidth is a choice.** Scott's rule and
Silverman's rule produce different curves. That choice is invisible in
a script.

**Problem 4 — Stratification multiplies the problem.** When your
collaborator asks for duration by facility, you need consistent bins,
consistent colors, and consistent percentile lines across both
facilities. A script hardcoded for the unstratified case has to be
rewritten.

---

In eventus, every visual decision lives in a versioned YAML config file.
The config file is the complete, reproducible record of what was plotted
and how.

---

> ### The script-based alternative
>
> A matplotlib script implementing the same three outputs — histogram,
> KDE, and stratified violin — would produce correct figures. The gap
> is not correctness. It is that every visual decision (bin width, KDE
> bandwidth, percentile values, category colors) would live as
> hardcoded values in the source code, invisible to any collaborator
> reading the output. Changing the bandwidth from Scott's rule to
> Silverman's requires finding the right line. Adding a third facility
> requires rewriting the violin loop. Running a sensitivity analysis
> across two bandwidth choices requires maintaining two versions of the
> script.
>
> Unlike Chapters 1 and 2, no comparison script was implemented here.
> The structural argument is about reproducibility and extensibility —
> not correctness or line count — and a script that draws correct
> histograms makes that case better than one that doesn't.

---

## The eventus solution

### Step 1 — Compute durations

`EpisodeDurationAnalyzer` accepts the `Episodes` object directly — it
does not need a `CohortTimeline`. Duration is a property of individual
episodes, not observation periods.

```python
import eventus

result = eventus.EpisodeDurationAnalyzer(
    episodes,
    descriptor_cols = ["facility_id"],
).calc()

print(result)
```

```
EpisodeDurationResult:
  identity     : nursing_facility_stay
  n_episodes   : 227
  n_entities   : 200
  mean_duration  : 112.0 days
  median_duration: 113.0 days
```

`descriptor_cols=["facility_id"]` tells the analyzer to carry
`facility_id` into the result for downstream stratification. No join
required later — the result already has what it needs.

### Step 2 — Histogram and KDE

Every visual decision lives in a versioned YAML config file.

```yaml
# configs/duration_plot_config.yaml

canvas:
  figsize: [10, 5]
  dpi: 120
  font_size: 12

histogram:
  bins:
    strategy: uniform
    n_bins: 30
    min: 0
    max: 200
  style:
    color: "#028090"
    alpha: 0.75
    show_grid: true
  percentile_lines:
    show: true
    values: [25, 50, 75, 90]
    show_labels: true

kde:
  style:
    bandwidth: scott
    color: "#028090"
    fill_alpha: 0.15
  percentiles:
    show: true
    values: [25, 50, 75, 90]
    show_labels: true
```

```python
hist_config = eventus.EpisodeDurationPlotConfig.build_from_yaml(
    "configs/duration_plot_config.yaml"
)
plotter = eventus.EpisodeDurationHistogramPlotter(result, hist_config)

plotter.plot_histogram("output/duration_histogram.png")
plotter.plot_kde("output/duration_kde.png")
```

The histogram and KDE are separate plot methods driven by the same
config file. Changing the bandwidth from `scott` to `silverman` is one
word. Running both as a sensitivity analysis requires two config files
and zero code changes.

*Figure 1. KDE of nursing facility stay duration (n=227 episodes).
Bimodal distribution with peaks near 80 and 115 days.
Dashed lines: P25, P50, P75, P90.*

### Step 3 — Stratified violin by facility

When your collaborator asks "does duration differ by facility?", adding
stratification requires one argument to the plotter and a matching
violin config. No code rewrite. No new data join.

```yaml
# configs/duration_violin_config.yaml

canvas:
  figsize: [10, 7]
  dpi: 120
  font_size: 12

labels:
  title: "Stay duration by facility"
  units: days

axes:
  y_min: 0

style:
  bandwidth: scott
  show_box: true
  show_points: false

percentiles:
  show: true
  values: [25, 50, 75]
  linestyle: dashed
  show_labels: true

categories:
  all_data:
    color: "#AAAAAA"
    label: All residents
  Facility_A:
    color: "#028090"
    label: Facility A
  Facility_B:
    color: "#E05C40"
    label: Facility B
```

```python
violin_config = eventus.ArraysViolinConfig.build_from_yaml(
    "configs/duration_violin_config.yaml"
)

eventus.EpisodeDurationViolinPlotter(
    result,
    violin_config,
    stratify_by = "facility_id",
).plot("output/duration_violin_by_facility.png")
```

*Figure 2. Stay duration stratified by facility.
All residents (n=227, P50=113 days),
Facility A (n=123, P50=110 days),
Facility B (n=104, P50=114.5 days).
Dashed lines: P25, P50, P75.*

The `stratify_by` argument names the column in `result.data` to group
by — declared in `descriptor_cols` when the analyzer was run. The
config declares one color and label per category. Missing categories
are auto-colored with a warning.

---

## What this demonstrated

- **Visual decisions are scientific decisions** — bin width, KDE
  bandwidth, percentile lines all belong in a versioned config file,
  not in plotting code. The YAML file is the complete, reproducible
  record of what was plotted and how.

- **Adding stratification requires one argument** — `stratify_by`
  on the plotter, plus a config that declares the categories. No data
  joins. No code rewrite. The descriptor column was declared in
  `descriptor_cols` when the analyzer ran and carried forward
  automatically.

- **`EpisodeDurationAnalyzer` works directly from `Episodes`** —
  duration is a property of individual episodes, not observation
  periods. No `CohortTimeline` needed for this analysis.

- **Sensitivity analysis is one config file** — want to know whether
  your conclusions change with a different bandwidth or bin width?
  Write a second config file. Run the same code. Compare.

---

*The next chapter introduces observation periods — what is each
member's window, and what happened inside it?*
