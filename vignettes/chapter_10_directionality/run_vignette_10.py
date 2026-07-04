"""
run_vignette_10.py — Chapter 10: Event Co-occurrence Directionality Analysis

Does one event tend to precede the other — or is the ordering random?

Runs three analyses:
  simul_5 — respiratory_infection → cardiovascular (directed signal)
  simul_4 — MI ↔ stroke (undirected — negative control for direction)
  simul_1 — cirrhosis → ED visit (directed, one-time exposure)

Usage:
    python vignettes/chapter_10_directionality/run_vignette_10.py

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

CONFIGS      = HERE / "configs"
CONFIGS_CH08 = HERE.parent / "chapter_08_coevents" / "configs"
CONFIGS_CH09 = HERE.parent / "chapter_09_gap_timing" / "configs"

# ── Full cohort obs period ────────────────────────────────────────────────────

all_ids = [f"D{str(i).zfill(4)}" for i in range(1, 5001)]

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)


def run_directionality_analysis(
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

    # Compute directionality
    analyzer = eventus.EventCoOccurrenceAnalyzer(
        cohort_timeline = ct,
        identity_a      = identity_a,
        identity_b      = identity_b,
    )

    directionality = analyzer.compute_directionality()
    print(directionality)

    # Compute the directionality test using the default uniform Monte Carlo null.
    # (Rotation and label_permutation are also available via null_method=...)
    dir_analyzer = eventus.EventCoOccurrenceDirectionalityAnalyzer(directionality)
    dir_test     = dir_analyzer.compute_test(
        null_method="uniform_monte_carlo", n_iterations=500
    )
    print(dir_test)

    # Plot
    from eventus.visualizers.event_cooccurrence.event_co_occurrence_directionality_plotter import (
        EventCoOccurrenceDirectionalityPlotter,
    )
    from eventus.visualizers.configs.event_co_occurrence_directionality_plot_config import (
        EventCoOccurrenceDirectionalityPlotConfig,
    )
    plotter = EventCoOccurrenceDirectionalityPlotter(
        dir_test,
        EventCoOccurrenceDirectionalityPlotConfig(),
    )
    safe_label = label.split("—")[0].strip().replace(" ", "_").lower()
    plotter.plot(str(OUTPUT_DIR / f"directionality_{safe_label}.png"))
    print(f"Figure saved: directionality_{safe_label}.png")


# ── simul_5 — respiratory_infection → cardiovascular (directed signal) ────────

run_directionality_analysis(
    event_a_path = HERE.parent / "data" / "ch10_simul5_respiratory_infections.csv",
    event_b_path = HERE.parent / "data" / "ch10_simul5_cardiovascular_events.csv",
    sem_a_path   = CONFIGS / "simul5_resp_semantics.yaml",
    sem_b_path   = CONFIGS / "simul5_cv_semantics.yaml",
    cfg_a_path   = CONFIGS / "simul5_cleaner.yaml",
    cfg_b_path   = CONFIGS / "simul5_cleaner.yaml",
    identity_a   = "respiratory_infection",
    identity_b   = "cardiovascular_event",
    label        = "simul_5 — respiratory_infection → cardiovascular (directed)",
)

# ── simul_4 — MI ↔ stroke (undirected — negative control for direction) ───────

run_directionality_analysis(
    event_a_path = HERE.parent / "data" / "ch09_10_simul4_mi_events.csv",
    event_b_path = HERE.parent / "data" / "ch09_10_simul4_stroke_events.csv",
    sem_a_path   = CONFIGS_CH09 / "simul4_mi_semantics.yaml",
    sem_b_path   = CONFIGS_CH09 / "simul4_stroke_semantics.yaml",
    cfg_a_path   = CONFIGS_CH09 / "simul4_cleaner.yaml",
    cfg_b_path   = CONFIGS_CH09 / "simul4_cleaner.yaml",
    identity_a   = "mi_event",
    identity_b   = "stroke_event",
    label        = "simul_4 — MI ↔ stroke (undirected)",
)

# ── simul_1 — cirrhosis → ED visit (directed, one-time exposure) ──────────────

run_directionality_analysis(
    event_a_path = HERE.parent / "data" / "ch08_11_simul1_cirrhosis_dx.csv",
    event_b_path = HERE.parent / "data" / "ch08_11_simul1_ed_visits.csv",
    sem_a_path   = CONFIGS_CH08 / "cirrhosis_ch08_semantics.yaml",
    sem_b_path   = CONFIGS_CH08 / "ed_ch08_semantics.yaml",
    cfg_a_path   = CONFIGS_CH08 / "cirrhosis_ch08_cleaner.yaml",
    cfg_b_path   = CONFIGS_CH08 / "ed_ch08_cleaner.yaml",
    identity_a   = "cirrhosis_diagnosis",
    identity_b   = "ed_visit",
    label        = "simul_1 — cirrhosis → ED visit (directed, one-time)",
)
