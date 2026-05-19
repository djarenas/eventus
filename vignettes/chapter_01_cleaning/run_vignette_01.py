"""
run_vignette_01.py — Chapter 1: Cleaning Hospitalization Claims

Usage:
    python vignettes/chapter_01_cleaning/run_vignette_01.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE        = pathlib.Path(__file__).parent
raw_hosp_df = pd.read_csv(HERE.parent / "data" / "hospitalization_claims.csv")

sem     = eventus.EventSemantics.build_from_yaml(HERE / "configs" / "hospitalization_semantics.yaml")
config  = eventus.EventsCleanerConfig.build_from_yaml(HERE / "configs" / "hospitalization_cleaner.yaml")
cleaner = eventus.EventsCleaner(raw_hosp_df, sem, config)
events  = cleaner.clean()

cleaner.print_report()
print(events)
