"""
run_vignette_09.py — Chapter 9: Event Co-occurrence Gap Analysis

Among patients who had both events, are the gaps shorter than
what independence would predict?

Runs twice:
  simul_4 — MI ↔ stroke (clustered timing, random directionality)
  simul_3 — pure null (two independent event streams)

Usage:
    python vignettes/chapter_09_gap_timing/run_vignette_09.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data_ch8x.py

See ch8-12_simulation_design.md for full simulation parameters.
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIGS = HERE / "configs"

# ── Full cohort obs period ────────────────────────────────────────────────────

all_ids = [f"D{str(i).zfill(4)}" for i in range(1, 5001)]

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)


def run_gap_analysis(
    event_a_path: pathlib.Path,
    event_b_path: pathlib.Path,
    sem_a_path:   pathlib.Path,
    sem_b_path:   pathlib.Path,
    cfg_a_path:   pathlib.Path,
    cfg_b_path:   pathlib.Path,
    identity_a:   str,
    identity_b:   str,
    label:        str,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    # Clean both streams
    raw_a   = pd.read_csv(event_a_path)
    sem_a   = eventus.EventSemantics.build_from_yaml(sem_a_path)
    cfg_a   = eventus.EventsCleanerConfig.build_from_yaml(cfg_a_path)
    clean_a = eventus.EventsCleaner(raw_a, sem_a, cfg_a).clean()

    raw_b   = pd.read_csv(event_b_path)
    sem_b   = eventus.EventSemantics.build_from_yaml(sem_b_path)
    cfg_b   = eventus.EventsCleanerConfig.build_from_yaml(cfg_b_path)
    clean_b = eventus.EventsCleaner(raw_b, sem_b, cfg_b).clean()

    # Filter to obs period
    clean_a = eventus.EventsFilter(clean_a).to_obs_period(obs).result
    clean_b = eventus.EventsFilter(clean_b).to_obs_period(obs).result

    # Assemble CohortTimeline
    ct = eventus.CohortTimeline.build_from_components(
        obs_period = obs,
        events     = [clean_a, clean_b],
    )

    # Compute gaps
    analyzer = eventus.EventCoOccurrenceAnalyzer(
        cohort_timeline = ct,
        identity_a      = identity_a,
        identity_b      = identity_b,
    )

    gaps = analyzer.compute_gaps()
    print(gaps)

    # Show distribution
    gap_col = "median_gap_a_to_nearest_b"
    vals = gaps.data[gap_col].dropna()
    if not vals.empty:
        print(f"\nDistribution of {gap_col} (n={len(vals):,} co-occurring entities):")
        print(f"  min    : {vals.min():.1f} days")
        print(f"  p25    : {vals.quantile(0.25):.1f} days")
        print(f"  median : {vals.median():.1f} days")
        print(f"  p75    : {vals.quantile(0.75):.1f} days")
        print(f"  max    : {vals.max():.1f} days")

    # Compute gap test
    gap_analyzer = eventus.EventCoOccurrenceGapAnalyzer(gaps)
    gap_test     = gap_analyzer.compute_test(n_permutations=500)
    print(gap_test)

    # Plot
    from eventus.visualizers.event_cooccurrence.event_co_occurrence_gap_plotter import (
        EventCoOccurrenceGapPlotter,
    )
    from eventus.visualizers.configs.event_co_occurrence_gap_plot_config import (
        EventCoOccurrenceGapPlotConfig,
    )
    plotter = EventCoOccurrenceGapPlotter(gap_test, EventCoOccurrenceGapPlotConfig())
    safe_label = label.split("—")[0].strip().replace(" ", "_").lower()
    plotter.plot(str(OUTPUT_DIR / f"gap_distributions_{safe_label}.png"))
    print(f"Figure saved: gap_distributions_{safe_label}.png")


# ── simul_4 — MI ↔ stroke (clustered, undirected) ────────────────────────────

run_gap_analysis(
    event_a_path = HERE.parent / "data" / "ch09_10_simul4_mi_events.csv",
    event_b_path = HERE.parent / "data" / "ch09_10_simul4_stroke_events.csv",
    sem_a_path   = CONFIGS / "simul4_mi_semantics.yaml",
    sem_b_path   = CONFIGS / "simul4_stroke_semantics.yaml",
    cfg_a_path   = CONFIGS / "simul4_cleaner.yaml",
    cfg_b_path   = CONFIGS / "simul4_cleaner.yaml",
    identity_a   = "mi_event",
    identity_b   = "stroke_event",
    label        = "simul_4 — MI ↔ stroke (clustered, undirected)",
)

# ── simul_1 — cirrhosis → ED visit (directed signal) ─────────────────────────

CONFIGS_CH08 = HERE.parent / "chapter_08_coevents" / "configs"

run_gap_analysis(
    event_a_path = HERE.parent / "data" / "ch08_11_simul1_cirrhosis_dx.csv",
    event_b_path = HERE.parent / "data" / "ch08_11_simul1_ed_visits.csv",
    sem_a_path   = CONFIGS_CH08 / "cirrhosis_ch08_semantics.yaml",
    sem_b_path   = CONFIGS_CH08 / "ed_ch08_semantics.yaml",
    cfg_a_path   = CONFIGS_CH08 / "cirrhosis_ch08_cleaner.yaml",
    cfg_b_path   = CONFIGS_CH08 / "ed_ch08_cleaner.yaml",
    identity_a   = "cirrhosis_diagnosis",
    identity_b   = "ed_visit",
    label        = "simul_1 — cirrhosis → ED visit (directed signal)",
)

# ── simul_3 — pure null ───────────────────────────────────────────────────────

run_gap_analysis(
    event_a_path = HERE.parent / "data" / "ch08_09_simul3_event_x.csv",
    event_b_path = HERE.parent / "data" / "ch08_09_simul3_event_y.csv",
    sem_a_path   = CONFIGS / "simul3_x_semantics.yaml",
    sem_b_path   = CONFIGS / "simul3_y_semantics.yaml",
    cfg_a_path   = CONFIGS / "simul3_cleaner.yaml",
    cfg_b_path   = CONFIGS / "simul3_cleaner.yaml",
    identity_a   = "simul3_event_x",
    identity_b   = "simul3_event_y",
    label        = "simul_3 — pure null",
)
