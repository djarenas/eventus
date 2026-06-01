"""
run_vignette_08.py — Chapter 8: Event Co-occurrence Analysis

Do patients with a cirrhosis diagnosis also have ED visits?
Is that co-occurrence above what chance would predict?
How many days between diagnosis and first ED visit?

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

cirrh_raw_df = pd.read_csv(HERE.parent / "data" / "simulated_cirrhosis_dx_ch08.csv")
ed_raw_df    = pd.read_csv(HERE.parent / "data" / "simulated_ed_visits_ch08.csv")

print(f"Cirrhosis diagnoses (raw): {len(cirrh_raw_df):,} rows")
print(f"ED visits (raw)           : {len(ed_raw_df):,} rows")

# ── Step 2 — Clean both streams independently ─────────────────────────────────

cirrh_sem    = eventus.EventSemantics.build_from_yaml(CONFIGS / "cirrhosis_ch08_semantics.yaml")
cirrh_config = eventus.EventsCleanerConfig.build_from_yaml(CONFIGS / "cirrhosis_ch08_cleaner.yaml")
cirrh_cleaner = eventus.EventsCleaner(cirrh_raw_df, cirrh_sem, cirrh_config)
cirrhosis     = cirrh_cleaner.clean()
cirrh_cleaner.print_report()
print(cirrhosis)

ed_sem    = eventus.EventSemantics.build_from_yaml(CONFIGS / "ed_ch08_semantics.yaml")
ed_config = eventus.EventsCleanerConfig.build_from_yaml(CONFIGS / "ed_ch08_cleaner.yaml")
ed_cleaner = eventus.EventsCleaner(ed_raw_df, ed_sem, ed_config)
ed_visits  = ed_cleaner.clean()
ed_cleaner.print_report()
print(ed_visits)

# ── Step 3 — Define observation period ───────────────────────────────────────

# The observation period must cover the FULL patient pool — not just
# patients who appear in either event stream. Patients with neither
# event must be present in the CohortTimeline for the 2x2 table to
# be correct. Deriving all_ids from the event DataFrames silently
# drops them and produces a wrong "neither" cell.
all_ids = [f"D{str(i).zfill(4)}" for i in range(1, 801)]

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = all_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# ── Step 4 — Filter both to obs period ───────────────────────────────────────

cirrhosis = eventus.EventsFilter(cirrhosis).to_obs_period(obs).result
ed_visits = eventus.EventsFilter(ed_visits).to_obs_period(obs).result

print(f"\nCirrhosis diagnoses in 2022: {len(cirrhosis):,}")
print(f"ED visits in 2022           : {len(ed_visits):,}")

# ── Step 5 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    events     = [cirrhosis, ed_visits],
)

print(ct)

# ── Step 6 — Co-occurrence presence ──────────────────────────────────────────

analyzer = eventus.EventCoOccurrenceAnalyzer(
    cohort_timeline = ct,
    identity_a      = "cirrhosis_diagnosis",
    identity_b      = "ed_visit",
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
