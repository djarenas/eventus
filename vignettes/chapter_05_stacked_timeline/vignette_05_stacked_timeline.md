# Chapter 5 — Stacked Timeline Visualization

## Vignette: Visualizing Age-Based Coverage Periods

You know from Chapter 4 that 13.6% of members had no Medicaid
coverage during their 18-25 window, that only 3.5% were continuously
covered for the full seven years, and that 31.9% had gaps. A table
of statistics tells you what happened. It cannot show you the pattern.

Which members had gaps early in their window? Which had gaps late?
Which were barely enrolled at all? Which had fragmented coverage
across the full seven years? A stacked timeline answers all of these
at once — one bar per member, colored by coverage status.

Before you write a single line of plotting code, you need to answer
a question that sounds simple: *"How do I plot observation periods
that are different lengths for every member?"*

---

### The four problems

**Problem 1 — Each member has a different observation window.**
In a standard time series plot, every row shares the same x-axis.
Here, one member's bar spans 2001-2008 (ages 18-25), another's spans
2006-2013, another's spans 2018-2025. A single shared x-axis cannot
represent this correctly. The bars need to be aligned to each
member's personal window, not to a calendar.

**Problem 2 — Four segment types require consistent color coding.**
Each bar has up to four segments: days before the first coverage
period, active coverage periods, gaps between coverage periods, and
days after the last coverage period. These color decisions are
scientific choices — the gap color signals a lapse, the before/after
color signals out-of-window time. If these colors are hardcoded in a
script, they are invisible to any collaborator reading the output.

**Problem 3 — Plotting 500 members produces an unreadable figure.**
The full cohort has 500 members. A meaningful visualization needs a
representative sample. Which 50? With what seed? That is a
reproducibility decision. A script that samples with
`random.sample()` on line 47 has made that decision silently.

**Problem 4 — Every visual decision is buried in the script.**
Colors, font sizes, tick intervals, sample size, random seed — all
hardcoded across dozens of lines. When a collaborator asks for a
different color scheme, you hunt. When a reviewer asks for monthly
ticks instead of quarterly, you edit and hope nothing else breaks.
When you rerun the analysis six months later — are you using the
same colors? The same sample? If those decisions live in your script,
the answer is "probably, unless someone edited it."

---

> ### The script-based alternative
>
> We implemented a matplotlib equivalent. The script is at
> `vignettes/without_eventus/without_eventus_stacked_timeline.py`.
> It required **165 lines** and has one critical limitation that
> cannot be fixed without significant additional work: **the x-axis
> shows normalized time [0, 1], not real dates.** Mapping normalized
> positions back to actual calendar dates for a cohort where every
> member has a different observation window requires per-member date
> reconstruction that is not straightforward in matplotlib. eventus
> handles this automatically with `x_axis: auto`.
>
> | Feature | Without eventus | With eventus | Notes |
> |---|:---:|:---:|---|
> | Renders a plot | ✓ | ✓ | 165 lines vs 3 lines |
> | Calendar and normalized x-axis | ✗ | ✓ | Our attempt did not cover both vs switches between calendar and normalized |
> | Variable-length obs periods | ✓ | ✓ | Manual normalization vs `x_axis: auto` |
> | Four-segment color coding | ✓ | ✓ | Hardcoded constants vs versioned YAML |
> | Reproducible sample | ✓ | ✓ | Hardcoded seed vs `sample_subset(random_seed=42)` |
> | Change a color | ✗ | ✓ | Edit the script vs change one word in YAML |
> | Change tick interval | ✗ | ✓ | Edit the script vs change one number in YAML |
> | Visual decisions versioned | ✗ | ✓ | Hardcoded throughout vs config YAML |
> | Validation on bad input | ✗ | ✓ | Silent wrong plot vs raises with message |
> | Reusable for new cohort | ✗ | ✓ | Rewrite vs change config |

---

## The eventus solution

### Step 1 — Reuse the Chapter 4 pipeline

No new cleaning. No new semantics. The `CohortTimeline` from
Chapter 4 Bonus A is the input — the pipeline is identical up to
the plot call.

```python
demog_df = pd.read_csv("data/simulated_member_demographics.csv")
raw_df   = pd.read_csv("data/simulated_medicaid_coverage_agewindow.csv")

sem     = eventus.EpisodeSemantics.build_from_yaml("configs/medicaid_coverage_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml("configs/medicaid_coverage_cleaner.yaml")
episodes  = eventus.EpisodesCleaner(raw_df, sem, config).clean()

obs = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 25,
    entity_col = "patient_id",
    identity   = "age_18_to_25",
)

episodes = eventus.EpisodesFilter(episodes).to_obs_period(obs, clip=True).result
ct     = eventus.CohortTimeline.build_from_components(obs_period=obs, episodes=episodes)
```

### Step 2 — Sample for visualization

```python
ct_sample = ct.sample_subset(n=50, random_seed=42)
```

This is a display decision, not an analytical decision. The analysis
in Chapter 4 used the full 500-member cohort. The visualization uses
50. These decisions live in different places — and `random_seed=42`
means the sample is identical every time the script runs.

### Step 3 — Configure

Every visual decision lives in the YAML. The x-axis mode, the color
for each segment type, the bar height, the legend placement — all
versioned, all human-readable.

```yaml
# configs/stacked_timeline_age_window_config.yaml

canvas:
  figsize:   [16, 8]
  dpi:       150

labels:
  title: "Medicaid Coverage Ages 18-25 (n=50 sample)"

layout:
  row_height:       0.5
  bar_height_ratio: 0.95

x_axis:
  mode:     auto      # handles variable-length obs periods automatically
  unit:     months
  interval: 3

poi:
  color_before:    "#FAFAF9"   # before 18th birthday — light grey
  color_middle:    "#F6C3A4"   # gap in coverage — orange
  color_after:     "#FAFAF9"   # after 25th birthday — light grey
  color_no_episodes: "#FAF9F9"   # never covered — near white

episodes:
  - identity: medicaid_coverage
    color:    "#9FC0F6"        # active coverage — blue
    alpha:    0.85
    label:    "Medicaid Coverage"
```

During development, using `mode: calendar` instead of `mode: auto`
raised immediately:

```
ValueError: [StackedTimelinePlotter] Error: x_axis='calendar' requires
all entities to have the same observation period. Found 50 different
obs_start values. Use x_axis='auto' or x_axis='normalized' instead.
```

The error named the problem, gave the exact count, and named the
two valid alternatives. A matplotlib script would have silently
drawn something wrong.

### Step 4 — Plot

```python
timeline_config = eventus.StackedTimelineConfig.build_from_yaml(
    "configs/stacked_timeline_age_window_config.yaml"
)

plotter = eventus.StackedTimelinePlotter(ct_sample, timeline_config)
plotter.plot("output/age_window_coverage_timeline.png")
```

The plot shows — in one figure — continuous members (solid blue
bars), gapped members (blue bars broken by orange), partially
covered members (short bars), and uncovered members (near-white
bars). The variation that Chapter 4 described in statistics is
visible as a pattern.

---

## What this demonstrated

- **`x_axis: auto` solves Problem 1** — variable-length observation
  periods are handled automatically. Each bar is aligned to its
  member's personal window. Calendar mode raises immediately if
  periods differ, before drawing anything.

- **The YAML solves Problem 2** — every color choice is declared,
  named, and versioned. `color_middle: "#F6C3A4"` means "this orange
  color represents a coverage gap." A collaborator reading the config
  knows that. A collaborator reading a script with hardcoded hex
  values does not.

- **`sample_subset()` solves Problem 3** — the display decision is
  explicit, reproducible, and separate from the analytical decision.
  Change `n=50` to `n=100` and you get a different sample. Change
  `random_seed` and you get a different sample. Both changes are
  deliberate and documented.

- **The YAML solves Problem 4** — every visual decision is one line
  in a config file. Change the gap color from orange to red: one
  word. Change tick interval from quarterly to monthly: one number.
  Change the sample size: one number. Change the title for the paper
  revision: one line. None of these require touching the analysis
  code. None require hunting through matplotlib. None risk breaking
  something else. Six months from now, the config file is the
  complete, human-readable record of every visual decision that was
  made — and it is version-controlled alongside the data and the
  analysis.

- **165 lines vs 3 lines — and the 165 lines cannot show real dates.**
  The matplotlib script produces a plot with a normalized x-axis
  [0, 1]. Mapping normalized positions back to actual calendar dates
  for a heterogeneous cohort is a significant additional problem that
  the script does not solve. The escalating complexity across
  vignettes — ~150 lines in Chapter 1, ~275 lines in Chapter 4,
  165 lines with a fundamental limitation in Chapter 5 — is itself
  the argument. At some point the script-based paradigm does not
  produce a worse version of the same thing. It produces something
  different.

---

*Chapter 6 — Full pipeline: combining episodes, events, and
observation periods into a single cohort analysis.
See `vignette_06_full_pipeline.md`.*
