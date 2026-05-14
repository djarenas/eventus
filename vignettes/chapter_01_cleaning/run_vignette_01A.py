"""
run_vignette_01A.py — Bonus A: Cleaning ED Visit Records

Usage:
    python vignettes/chapter_01_cleaning/run_vignette_01A.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import pathlib
import pandas as pd
from eventus import OccurrenceSemantics, OccurrencesCleaner, OccurrencesCleanerConfig

HERE      = pathlib.Path(__file__).parent
raw_ed_df = pd.read_csv(HERE.parent / "data" / "ed_visits.csv")

sem    = OccurrenceSemantics(
    entity_id_col = "patient_id",
    date_col      = "ed_visit_date",
    identity      = "ed_visit",
)

config    = OccurrencesCleanerConfig.build_from_yaml(HERE / "configs" / "ed_cleaner.yaml")
cleaner   = OccurrencesCleaner(raw_ed_df, sem, config)
ed_visits = cleaner.clean()

cleaner.print_report()
print(ed_visits)
