"""
run_vignette_07.py — Chapter 7: Event Timing Analysis

When did members have their first ED visit after turning 18?
How long between visits? Does the gap differ by diagnosis?

Runs twice — once on the null simulation (no signal) and once on the
signal simulation (conditionC visits ~2x more than conditionA).

Usage:
    python vignettes/chapter_07_event_timing/run_vignette_07.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
CH06       = HERE.parent / "chapter_06_events" / "configs"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

demog_df = pd.read_csv(HERE.parent / "data" / "ch04_07_member_demographics.csv")

sem    = eventus.EventSemantics.build_from_yaml(CH06 / "ed_semantics.yaml")
config = eventus.EventsCleanerConfig.build_from_yaml(CH06 / "ed_cleaner_with_consolidation.yaml")

timing_config    = eventus.EventResultTimingConfig.build_from_yaml(HERE / "configs" / "ed_visit_timing_config.yaml")
shape_config     = eventus.EventResultShapeConfig.build_from_yaml(HERE / "configs" / "ed_visit_shape_config.yaml")
gap_violin_config = eventus.ArraysViolinConfig.build_from_yaml(HERE / "configs" / "ed_visit_gap_violin_config.yaml")
stratified_config = eventus.ArraysViolinConfig.build_from_yaml(HERE / "configs" / "ed_visit_gap_stratified_config.yaml")

obs = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 21,
    entity_col = "patient_id",
    identity   = "age_18_to_21",
)

def run_analysis(data_file: str, label: str) -> None:
    print(f"\n{'='*56}")
    print(f"Running: {label}")
    print(f"{'='*56}")

    raw_df    = pd.read_csv(HERE.parent / "data" / data_file)
    ed_visits = eventus.EventsCleaner(raw_df, sem, config).clean()
    ed_visits = eventus.EventsFilter(ed_visits).to_obs_period(obs).result

    ct = eventus.CohortTimeline.build_from_components(
        obs_period  = obs,
        events = ed_visits,
    )

    analyzer = eventus.CohortTimelineEventAnalyzer(ct, "ed_visit")

    # ── Timing ───────────────────────────────────────────────────────────────
    timing_result = analyzer.compute_timing(max_n=3)
    print(timing_result)
    eventus.EventResultTimingPlotter(timing_result, timing_config).plot_histogram(
        str(OUTPUT_DIR / f"ed_visit_timing_{label}.png")
    )

    # ── Shape + gap violin ────────────────────────────────────────────────────
    shape_result = analyzer.compute_shape()
    print(shape_result)
    plotter = eventus.EventResultShapePlotter(shape_result, shape_config)
    plotter.plot_mean_gap_violin(
        path          = str(OUTPUT_DIR / f"ed_visit_gap_violin_{label}.png"),
        violin_config = gap_violin_config,
    )

    # ── Stratified by condition ───────────────────────────────────────────────
    plotter.plot_mean_gap_violin_stratified(
        path            = str(OUTPUT_DIR / f"ed_visit_gap_by_condition_{label}.png"),
        cohort_timeline = ct,
        stratify_by     = "icd10_condition",
        violin_config   = stratified_config,
    )

    # ── Stratified medians for README ─────────────────────────────────────────
    import numpy as np
    shape_data = shape_result.data[[ct.entity_col, "mean_gap"]].copy()
    shape_data["condition"] = ct.get_event_descriptor(
        "ed_visit", "icd10_condition"
    ).values
    print(f"\nStratified mean gap by condition ({label}):")
    for cond, grp in shape_data.groupby("condition"):
        vals = grp["mean_gap"].dropna()
        if len(vals) > 0:
            print(f"  {cond}: n={len(vals)}, median={np.median(vals):.0f}d, mean={vals.mean():.0f}d")

run_analysis("ch07_ed_visits_agewindow_null.csv",   "null")
run_analysis("ch07_ed_visits_agewindow_signal.csv", "signal")

print(f"\nAll outputs saved to: {OUTPUT_DIR}")
