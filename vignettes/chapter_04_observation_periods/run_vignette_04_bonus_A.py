"""
run_vignette_04_bonus_A.py — Chapter 4, Bonus A: Age-Based Observation Periods
"I am only interested in coverage for 18-25 year olds"

Usage:
    python vignettes/chapter_04_observation_periods/run_vignette_04_bonus_A.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE = pathlib.Path(__file__).parent

# ── Step 1 — Load demographics and coverage data ──────────────────────────────

demog_df = pd.read_csv(HERE.parent / "data" / "ch04_07_member_demographics_clean.csv")
raw_df   = pd.read_csv(HERE.parent / "data" / "ch04_05_medicaid_coverage_agewindow.csv")

print(f"Members with demographics : {len(demog_df):,}")
print(f"Coverage rows (2018-2025) : {len(raw_df):,}")

# ── Step 2 — Clean coverage data ─────────────────────────────────────────────

sem     = eventus.EpisodeSemantics.build_from_yaml(HERE / "configs" / "medicaid_coverage_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml(HERE / "configs" / "medicaid_coverage_cleaner.yaml")
cleaner = eventus.EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()

cleaner.print_report()


# ... After cleaning the data 

# ── Step 3 — Define age-based observation periods ────────────────────────────
# Each member's obs period = their 18th birthday to their 25th birthday.
# Members who turned 25 before 2018 or turn 18 after 2025 will have
# zero-length or out-of-range windows.
# Note: using ch04_07_member_demographics_clean.csv — all DOBs 1995-2003,
# no future observation periods, no warnings expected.

obs = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 25,
    entity_col = "patient_id",
    identity   = "age_18_to_25",
)

print(obs)

# ── Step 4 — Filter episodes to obs period ─────────────────────────────────────

episodes = eventus.EpisodesFilter(episodes).to_obs_period(obs, clip=True).result
print(f"\nCoverage periods after filtering to age 18-25 window: {len(episodes):,}")

# ── Step 5 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes     = episodes,
)

print(ct)

# ── Step 6 — Enrich and summarize ────────────────────────────────────────────

from eventus.analyzers import CohortTimelineEpisodeAnalyzer

analyzer = CohortTimelineEpisodeAnalyzer(ct, "medicaid_coverage")
ct_enriched = analyzer.enrich_with_episode_coverage()
summary     = analyzer.get_summary()
print(summary)
