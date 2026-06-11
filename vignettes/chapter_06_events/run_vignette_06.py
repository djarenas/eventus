"""
run_vignette_06.py — Chapter 6: Cleaning and Analyzing ED Visit Events

Usage:
    python vignettes/chapter_06_events/run_vignette_06.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
CH04       = HERE.parent / "chapter_04_observation_periods" / "configs"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Step 1 — Load and clean ED visits ────────────────────────────────────────

raw_df    = pd.read_csv(HERE.parent / "data" / "ch01_06_ed_visits.csv")
sem       = eventus.EventSemantics.build_from_yaml(HERE / "configs" / "ed_semantics.yaml")
config    = eventus.EventsCleanerConfig.build_from_yaml(HERE / "configs" / "ed_cleaner_with_consolidation.yaml")
cleaner   = eventus.EventsCleaner(raw_df, sem, config)
ed_visits = cleaner.clean()

cleaner.print_report()
print(ed_visits)

# ── Step 2 — Load clean coverage episodes ──────────────────────────────────────

cov_raw    = pd.read_csv(HERE.parent / "data" / "ch04_06_medicaid_coverage.csv")
cov_sem    = eventus.EpisodeSemantics.build_from_yaml(CH04 / "medicaid_coverage_semantics.yaml")
cov_config = eventus.EpisodesCleanerConfig.build_from_yaml(CH04 / "medicaid_coverage_cleaner.yaml")
cov_episodes = eventus.EpisodesCleaner(cov_raw, cov_sem, cov_config).clean()

# ── Step 3 — Define observation period ───────────────────────────────────────

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = cov_episodes.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# ── Step 4 — Filter both to obs period ───────────────────────────────────────

cov_episodes = eventus.EpisodesFilter(cov_episodes).to_obs_period(obs, clip=True).result
ed_visits  = eventus.EventsFilter(ed_visits).to_obs_period(obs).result

print(f"\nCoverage periods in 2022 : {len(cov_episodes):,}")
print(f"ED visits in 2022        : {len(ed_visits):,}")

# ── Step 5 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period  = obs,
    episodes      = cov_episodes,
    events = ed_visits,
)

print("cohort timeline object")
print(ct)
print([c for c in ct.data.columns if "ed_visit" in c])

# ── Step 6 — Compute event volume ───────────────────────────────────────

analyzer      = eventus.CohortTimelineEventAnalyzer(ct, "ed_visit")
volume_result = analyzer.compute_volume()

print(volume_result)

# ── Step 7 — Enrich and show distribution ────────────────────────────────────

ct_enriched = analyzer.enrich_with_volume()

print("\nED visit volume distribution — 2022 cohort:")
dist = (
    ct_enriched.data["evt_comp_ed_visit_n"]
    .fillna(0)
    .astype(int)
    .value_counts()
    .sort_index()
)
n_total = len(ct_enriched)
for n_visits, count in dist.items():
    label = f"{n_visits} visit{'s' if n_visits != 1 else ''}"
    pct   = round(100 * count / n_total, 1)
    print(f"  {label:<12} : {count:>4,}  ({pct}%)")

# ── Step 8 — Episode-event interaction ──────────────────────────────────────
# The CohortTimeline holds both coverage episodes and ED visits.
# EpisodeEventInteractionAnalyzer classifies each member's ED visits
# by where they fall relative to the coverage structure.

interaction_analyzer = eventus.EpisodeEventInteractionAnalyzer(
    ct, "medicaid_coverage", "ed_visit"
)
interaction_result = interaction_analyzer.compute_interaction()
print(interaction_result)

# ── Bonus A — Plot volume distribution ───────────────────────────────────────

vol_config = eventus.EventResultVolumeConfig.build_from_yaml(
    HERE / "configs" / "ed_visit_volume_config.yaml"
)
plotter = eventus.EventResultVolumePlotter(volume_result, vol_config)

plotter.plot_prevalence_bar(str(OUTPUT_DIR / "ed_visit_prevalence.png"))
plotter.plot_count_distribution_bar(str(OUTPUT_DIR / "ed_visit_count_distribution.png"))

print(f"\nBonus A outputs saved to: {OUTPUT_DIR}")

# ── Bonus B — ED visits ages 18-21 ───────────────────────────────────────────

demog_df  = pd.read_csv(HERE.parent / "data" / "ch04_07_member_demographics_age18_21.csv")
ed_age_df = pd.read_csv(HERE.parent / "data" / "ch07_ed_visits_agewindow_null.csv")

# Clean ED visits — same semantics, same cleaner
ed_age_visits = eventus.EventsCleaner(
    ed_age_df, sem, config
).clean()

# Age-based observation period — 18 to 21
obs_age = eventus.ObsPeriodPerEntity.construct_from_age_window(
    entity_df  = demog_df,
    dob_col    = "date_of_birth",
    age_start  = 18,
    age_end    = 21,
    entity_col = "patient_id",
    identity   = "age_18_to_21",
)

print(obs_age)

# Filter ED visits to the age window
ed_age_visits = eventus.EventsFilter(ed_age_visits).to_obs_period(obs_age).result
print(f"\nED visits within age 18-21 window: {len(ed_age_visits):,}")

# Assemble and analyze
ct_age = eventus.CohortTimeline.build_from_components(
    obs_period  = obs_age,
    events = ed_age_visits,
)

analyzer_age  = eventus.CohortTimelineEventAnalyzer(ct_age, "ed_visit")
volume_age    = analyzer_age.compute_volume()

print(volume_age)

# Plot
plotter_age = eventus.EventResultVolumePlotter(volume_age, vol_config)
plotter_age.plot_prevalence_bar(str(OUTPUT_DIR / "ed_visit_prevalence_age_18_21.png"))
plotter_age.plot_count_distribution_bar(str(OUTPUT_DIR / "ed_visit_count_distribution_age_18_21.png"))

print(f"\nBonus B outputs saved to: {OUTPUT_DIR}")
