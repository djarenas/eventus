"""
run_vignette_08.py — Chapter 8: Event Co-occurrence Presence Analysis

Do cirrhosis diagnoses and ED visits co-occur above chance in a
5,000-patient Medicaid cohort?

Runs twice:
  simul_1 — cirrhosis → ED visit (full signal)
  simul_4 — pure null (two independent event streams)

The contrast between simul_1 and simul_4 validates that the analyzer
correctly detects signal when present and correctly returns null when not.

Usage:
    python vignettes/chapter_08_coevent/run_vignette_08.py

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

# ── Full cohort obs period — shared by both analyses ──────────────────────────
# Declared explicitly from the full 5,000-patient pool — not derived from
# either event stream. Patients with neither event must be present in the
# CohortTimeline for the 2x2 table to be correct.

all_ids = [f"D{str(i).zfill(4)}" for i in range(1, 5001)]

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)


def run_presence_analysis(
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

    # Clean both streams independently
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

    # Compute presence
    analyzer = eventus.EventCoOccurrenceAnalyzer(
        cohort_timeline = ct,
        identity_a      = identity_a,
        identity_b      = identity_b,
    )

    presence = analyzer.compute_presence()
    print(presence)

    assoc = presence.association
    print(assoc)


# ── simul_1 — cirrhosis → ED visit (full signal) ──────────────────────────────

run_presence_analysis(
    event_a_path = HERE.parent / "data" / "ch08_11_simul1_cirrhosis_dx.csv",
    event_b_path = HERE.parent / "data" / "ch08_11_simul1_ed_visits.csv",
    sem_a_path   = CONFIGS / "cirrhosis_ch08_semantics.yaml",
    sem_b_path   = CONFIGS / "ed_ch08_semantics.yaml",
    cfg_a_path   = CONFIGS / "cirrhosis_ch08_cleaner.yaml",
    cfg_b_path   = CONFIGS / "ed_ch08_cleaner.yaml",
    identity_a   = "cirrhosis_diagnosis",
    identity_b   = "ed_visit",
    label        = "simul_1 — cirrhosis → ED visit (signal)",
)

# ── simul_4 — pure null ───────────────────────────────────────────────────────

run_presence_analysis(
    event_a_path = HERE.parent / "data" / "ch08_09_simul3_event_x.csv",
    event_b_path = HERE.parent / "data" / "ch08_09_simul3_event_y.csv",
    sem_a_path   = CONFIGS / "simul3_x_semantics.yaml",
    sem_b_path   = CONFIGS / "simul3_y_semantics.yaml",
    cfg_a_path   = CONFIGS / "simul3_cleaner.yaml",
    cfg_b_path   = CONFIGS / "simul3_cleaner.yaml",
    identity_a   = "simul3_event_x",
    identity_b   = "simul3_event_y",
    label        = "simul_3 — pure null (two independent event streams)",
)
