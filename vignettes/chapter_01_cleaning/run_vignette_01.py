"""
run_vignette_01.py — Chapter 1: Cleaning Hospitalization Claims

Usage:
    python vignettes/chapter_01_cleaning/run_vignette_01.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import pathlib
import pandas as pd
from eventus import EventSemantics, EventsCleaner, EventsCleanerConfig

HERE       = pathlib.Path(__file__).parent
raw_hosp_df = pd.read_csv(HERE.parent / "data" / "hospitalization_claims.csv")

sem    = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)

config  = EventsCleanerConfig.build_from_yaml(HERE / "configs" / "hospitalization_cleaner.yaml")
cleaner = EventsCleaner(raw_hosp_df, sem, config)
events  = cleaner.clean()

cleaner.print_report()
print(events)
