"""
run_vignette_05.py — Chapter 5: Stacked Timeline Visualization

Visualizes the age 18-25 Medicaid coverage from Chapter 4 Bonus A
as a stacked timeline. Each member has a different observation window.

Usage:
    python vignettes/chapter_05_stacked_timeline/run_vignette_05.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIGS = HERE / "configs"
CH04    = HERE.parent / "chapter_04_observation_periods" / "configs"

# ── Re-run Chapter 4 Bonus A pipeline ────────────────────────────────────────

demog_df = pd.read_csv(HERE.parent / "data" / "ch04_07_member_demographics.csv")
raw_df   = pd.read_csv(HERE.parent / "data" / "ch04_05_medicaid_coverage_agewindow.csv")

sem     = eventus.EpisodeSemantics.build_from_yaml(CH04 / "medicaid_coverage_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml(CH04 / "medicaid_coverage_cleaner.yaml")
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

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes     = episodes,
)

print(ct)

# ── Sample 50 for visualization ───────────────────────────────────────────────
# The full CohortTimeline has 500 members with variable-length windows.
# We sample 50 with a fixed seed — reproducible, representative.
# The analysis in Chapter 4 used the full cohort.
# This is a display decision, not an analytical one.

ct_sample = ct.sample_subset(n=50, random_seed=42)
print(f"Sampled {len(ct_sample)} members for visualization")

# ── Plot stacked timeline ─────────────────────────────────────────────────────

timeline_config = eventus.StackedTimelineConfig.build_from_yaml(
    CONFIGS / "stacked_timeline_age_window_config.yaml"
)

plotter = eventus.StackedTimelinePlotter(ct_sample, timeline_config)
plotter.plot(str(OUTPUT_DIR / "age_window_coverage_timeline.png"))

print(f"\nOutput saved to: {OUTPUT_DIR / 'age_window_coverage_timeline.png'}")
