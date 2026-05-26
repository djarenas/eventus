"""
run_vignette_08.py — Chapter 8: Event-Episode Co-event Analysis

Explores the temporal relationship between ED visits (events)
and hospitalizations (episodes) in a 2022 Medicaid cohort.

Scientific questions:
  - What proportion of ED visits happen during a hospitalization?
  - How many days from an ED visit to the next hospitalization?
  - How many days from hospital discharge to the next ED visit?

Usage:
    python vignettes/chapter_08_coevent/run_vignette_08.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE       = pathlib.Path(__file__).parent
DATA_DIR   = HERE.parent / "data"
CONFIGS    = HERE / "configs"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Step 1 — Clean hospitalizations ──────────────────────────────────────────

hosp_raw    = pd.read_csv(DATA_DIR / "simulated_hospitalizations_ch08.csv")
hosp_sem    = eventus.EpisodeSemantics.build_from_yaml(CONFIGS / "hospitalization_semantics_ch08.yaml")
hosp_config = eventus.EpisodesCleanerConfig.build_from_yaml(CONFIGS / "hospitalization_cleaner_ch08.yaml")
hosp_cleaner = eventus.EpisodesCleaner(hosp_raw, hosp_sem, hosp_config)
hospitalizations = hosp_cleaner.clean()

hosp_cleaner.print_report()
print(hospitalizations)

# ── Step 2 — Clean ED visits ──────────────────────────────────────────────────

ed_raw    = pd.read_csv(DATA_DIR / "simulated_ed_visits_ch08.csv")
ed_sem    = eventus.EventSemantics.build_from_yaml(CONFIGS / "ed_semantics_ch08.yaml")
ed_config = eventus.EventsCleanerConfig.build_from_yaml(CONFIGS / "ed_cleaner_ch08.yaml")
ed_cleaner = eventus.EventsCleaner(ed_raw, ed_sem, ed_config)
ed_visits = ed_cleaner.clean()

ed_cleaner.print_report()
print(ed_visits)

# ── Step 3 — Define observation period ───────────────────────────────────────

all_entity_ids = set(hospitalizations.data["patient_id"]) | set(ed_visits.data["patient_id"])

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = list(all_entity_ids),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# ── Step 4 — Filter to obs period ─────────────────────────────────────────────

hospitalizations = eventus.EpisodesFilter(hospitalizations).to_obs_period(obs, clip=True).result
ed_visits        = eventus.EventsFilter(ed_visits).to_obs_period(obs).result

print(f"\nHospitalizations in 2022 : {len(hospitalizations):,}")
print(f"ED visits in 2022        : {len(ed_visits):,}")

# ── Step 5 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period  = obs,
    episodes      = hospitalizations,
    events = ed_visits,
)

print(ct)

# ── Step 6 — Stacked timeline sample ─────────────────────────────────────────

timeline_config = eventus.StackedTimelineConfig.build_from_yaml(
    CONFIGS / "stacked_timeline_ch08_config.yaml"
)
ct_sample = ct.sample_subset(n=50, random_seed=42)
eventus.StackedTimelinePlotter(ct_sample, timeline_config).plot(
    str(OUTPUT_DIR / "stacked_timeline_ch08.png")
)

# ── Step 7 — Co-event analysis ──────────────────────────────────────────

analyzer = eventus.EventEpisodeAnalyzer(ct, "ed_visit", "inpatient_hospitalization")
result   = analyzer.compute()

print(result)

# ── Step 8 — Plot gap distributions ──────────────────────────────────────────

violin_config = eventus.ArraysViolinConfig.build_from_yaml(
    CONFIGS / "coevent_violin_config.yaml"
)

# occ → next episode (ED visit to next hospitalization)
evt_to_evt = result.data["mean_days_evt_to_episode"].dropna().values
# episode → next occ (discharge to next ED visit)
eps_to_occ = result.data["mean_days_episode_to_occ"].dropna().values

arrays = {
    "ED → next\nhospitalization": evt_to_evt,
    "Discharge → next\nED visit":  eps_to_occ,
}

eventus.ArraysViolinPlotter(arrays, violin_config).plot(
    str(OUTPUT_DIR / "coevent_gaps_violin.png")
)

print(f"\nOutputs saved to: {OUTPUT_DIR}")
