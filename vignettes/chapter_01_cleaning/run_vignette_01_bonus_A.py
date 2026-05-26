"""
run_vignette_01_bonus_A.py — Bonus A: Cleaning ED Visit Records

Usage:
    python vignettes/chapter_01_cleaning/run_vignette_01_bonus_A.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE      = pathlib.Path(__file__).parent
raw_ed_df = pd.read_csv(HERE.parent / "data" / "simulated_ed_visits.csv")

sem       = eventus.EventSemantics.build_from_yaml(HERE / "configs" / "ed_semantics.yaml")
config    = eventus.EventsCleanerConfig.build_from_yaml(HERE / "configs" / "ed_cleaner.yaml")
cleaner   = eventus.EventsCleaner(raw_ed_df, sem, config)
ed_visits = cleaner.clean()

cleaner.print_report()
print(ed_visits)
