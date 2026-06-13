"""Vignette-pinned test for episode duration analysis (Chapter 3).

The nursing-facility cohort yields 227 episodes across 200 residents with
a median stay of 113 days (mean 112), stratifiable by facility.
"""
from __future__ import annotations

import pandas as pd

import eventus


def test_ch03_episode_duration(asset, data_dir):
    # Chapter 3 reuses the Chapter 2 cleaned nursing-facility episodes.
    sem = eventus.EpisodeSemantics.build_from_yaml(
        asset("chapter_02_descriptor_aggregation", "configs", "nursing_facility_semantics.yaml")
    )
    config = eventus.EpisodesCleanerConfig.build_from_yaml(
        asset("chapter_02_descriptor_aggregation", "configs", "nursing_facility_cleaner.yaml")
    )
    raw = pd.read_csv(data_dir / "ch02_03_nursing_facility_assessments.csv")
    episodes = eventus.EpisodesCleaner(raw, sem, config).clean()

    result = eventus.EpisodeDurationAnalyzer(
        episodes, descriptor_cols=["facility_id"]
    ).calc()

    assert result.n_episodes == 227
    assert result.n_entities == 200

    durations = result.data["duration_days"]
    assert float(durations.median()) == 113.0
    assert round(float(durations.mean()), 0) == 112.0
    # Stratification descriptor survived into the result.
    assert "facility_id" in result.data.columns
