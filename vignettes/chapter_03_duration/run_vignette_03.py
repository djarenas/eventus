"""
run_vignette_03.py — Chapter 3: Stay Duration Analysis

Usage:
    python vignettes/chapter_03_stay_duration/run_vignette_03.py

Requires Chapter 2 data — generate first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Re-run Chapter 2 cleaning to get clean episodes ────────────────────────────

raw_df  = pd.read_csv(HERE.parent / "data" / "nursing_facility_assessments.csv")
sem     = eventus.EpisodeSemantics.build_from_yaml(HERE.parent / "chapter_02_descriptor_aggregation" / "configs" / "nursing_facility_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml(HERE.parent / "chapter_02_descriptor_aggregation" / "configs" / "nursing_facility_cleaner.yaml")
episodes  = eventus.EpisodesCleaner(raw_df, sem, config).clean()

# ── Step 1 — Compute durations ────────────────────────────────────────────────

result = eventus.EpisodeDurationAnalyzer(
    episodes,
    descriptor_cols = ["facility_id"],
).calc()

print(result)

# ── Step 2 — Histogram and KDE ────────────────────────────────────────────────

hist_config = eventus.EpisodeDurationPlotConfig.build_from_yaml(HERE / "configs" / "duration_plot_config.yaml")
plotter     = eventus.EpisodeDurationHistogramPlotter(result, hist_config)

plotter.plot_histogram(str(OUTPUT_DIR / "duration_histogram.png"))
plotter.plot_kde(str(OUTPUT_DIR / "duration_kde.png"))

# ── Step 3 — Violin stratified by facility ───────────────────────────────────

violin_config = eventus.ArraysViolinConfig.build_from_yaml(HERE / "configs" / "duration_violin_config.yaml")

eventus.EpisodeDurationViolinPlotter(
    result,
    violin_config,
    stratify_by = "facility_id",
).plot(str(OUTPUT_DIR / "duration_violin_by_facility.png"))

print(f"\nOutputs saved to: {OUTPUT_DIR}")
