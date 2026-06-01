"""
run_vignette_02.py — Chapter 2: Descriptor Aggregation

Usage:
    python vignettes/chapter_02_descriptor_aggregation/run_vignette_02.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE   = pathlib.Path(__file__).parent
raw_df = pd.read_csv(HERE.parent / "data" / "ch02_03_nursing_facility_assessments.csv")

sem     = eventus.EpisodeSemantics.build_from_yaml(HERE / "configs" / "nursing_facility_semantics.yaml")
config  = eventus.EpisodesCleanerConfig.build_from_yaml(HERE / "configs" / "nursing_facility_cleaner.yaml")
cleaner = eventus.EpisodesCleaner(raw_df, sem, config)
episodes  = cleaner.clean()

cleaner.print_report()
print(episodes)
print(episodes.data.head(10))
