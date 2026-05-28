"""
run_vignette_08.py — Chapter 8: Event Co-occurrence Analysis

Do ED visits and hospitalizations co-occur in the same patient?
Is that co-occurrence above what chance would predict?
How long between an ED visit and the nearest hospitalization?

Usage:
    python vignettes/chapter_08_coevent/run_vignette_08.py

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

# ── Step 1 — Load raw data ────────────────────────────────────────────────────

ed_raw_df   = pd.read_csv(HERE.parent / "data" / "simulated_ed_visits_ch08.csv")
hosp_raw_df = pd.read_csv(HERE.parent / "data" / "simulated_hospitalizations_ch08.csv")

print(f"ED visits (raw)        : {len(ed_raw_df):,} rows")
print(f"Hospitalizations (raw) : {len(hosp_raw_df):,} rows")

# ── Step 2 — Clean both streams independently ─────────────────────────────────

ed_sem    = eventus.EventSemantics.build_from_yaml(CONFIGS / "ed_ch08_semantics.yaml")
ed_config = eventus.EventsCleanerConfig.build_from_yaml(CONFIGS / "ed_ch08_cleaner.yaml")
ed_cleaner = eventus.EventsCleaner(ed_raw_df, ed_sem, ed_config)
ed_visits  = ed_cleaner.clean()
ed_cleaner.print_report()
print(ed_visits)

hosp_sem    = eventus.EpisodeSemantics.build_from_yaml(CONFIGS / "hosp_ch08_semantics.yaml")
hosp_config = eventus.EpisodesCleanerConfig.build_from_yaml(CONFIGS / "hosp_ch08_cleaner.yaml")
hosp_cleaner = eventus.EpisodesCleaner(hosp_raw_df, hosp_sem, hosp_config)
hospitalizations = hosp_cleaner.clean()
hosp_cleaner.print_report()
print(hospitalizations)

# ── Step 3 — Define observation period ───────────────────────────────────────

all_ids = list(set(
    ed_visits.data["patient_id"].tolist() +
    hospitalizations.data["patient_id"].tolist()
))

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# ── Step 4 — Filter both to obs period ───────────────────────────────────────

ed_visits       = eventus.EventsFilter(ed_visits).to_obs_period(obs).result
hospitalizations = eventus.EpisodesFilter(hospitalizations).to_obs_period(obs, clip=True).result

print(f"\nED visits in 2022       : {len(ed_visits):,}")
print(f"Hospitalizations in 2022: {len(hospitalizations):,}")

# ── Step 5 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    episodes   = hospitalizations,
    events     = ed_visits,
)

print(ct)

# ── Step 6 — Co-occurrence presence ──────────────────────────────────────────

analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline  = ct,
    event_identity_a = "ed_visit",
    event_identity_b = "inpatient_hospitalization",
)

presence = analyzer.compute_presence(within_days=0)
print(presence)

# ── Step 7 — Association ──────────────────────────────────────────────────────

assoc = presence.association
print(assoc)
print(assoc.contingency_table)
print(f"\nDisclaimer: {assoc.disclaimer}")

# ── Step 8 — Gaps ────────────────────────────────────────────────────────────

gaps = analyzer.compute_gaps()
print(gaps)

print(f"\nOutputs saved to: {OUTPUT_DIR}")
