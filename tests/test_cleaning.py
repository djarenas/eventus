"""Vignette-pinned tests for the cleaning pipeline (Chapters 1 and 2).

Asserts the exact cleaning-report figures reported in the manuscript:
Chapter 1 reduces 11,500 raw hospitalization rows to 2,297 clean episodes
across 793 entities; Chapter 2 collapses the nursing-facility assessments
to 227 episodes across 200 residents.
"""
from __future__ import annotations

import pandas as pd

import eventus


def test_ch01_hospitalization_cleaning(asset, data_dir):
    sem = eventus.EpisodeSemantics.build_from_yaml(
        asset("chapter_01_cleaning", "configs", "hospitalization_semantics.yaml")
    )
    config = eventus.EpisodesCleanerConfig.build_from_yaml(
        asset("chapter_01_cleaning", "configs", "hospitalization_cleaner.yaml")
    )
    raw = pd.read_csv(data_dir / "ch01_hospitalization_claims.csv")

    cleaner = eventus.EpisodesCleaner(raw, sem, config)
    episodes = cleaner.clean()
    report = cleaner.calc_report()

    assert report["total_input_rows"] == 11_500
    assert len(episodes.data) == 2_297
    assert episodes.data[sem.entity_id_col].nunique() == 793
    assert len(cleaner.rejected) == 9_136
    # Row accounting: clean + rejected + merged-away == input. Interval
    # merging collapses some surviving rows into others, so clean + rejected
    # falls short of the input by exactly the number merged away (67 here).
    merged_away = report["total_input_rows"] - len(episodes.data) - len(cleaner.rejected)
    assert merged_away == 67
    assert len(episodes.data) + len(cleaner.rejected) + merged_away == report["total_input_rows"]
    # The report must expose merged-away explicitly (combined, not discarded),
    # not leave it as a silent gap the reader has to infer by subtraction.
    assert report["totals"]["merged_away"]["count"] == 67


def test_ch01_event_consolidation_accounting(asset, data_dir):
    """Events consolidation is reported as a distinct category, not as
    rejection, and the report reconciles: rejected + consolidated + clean."""
    sem = eventus.EventSemantics.build_from_yaml(
        asset("chapter_06_events", "configs", "ed_semantics.yaml")
    )
    config = eventus.EventsCleanerConfig.build_from_yaml(
        asset("chapter_06_events", "configs", "ed_cleaner_with_consolidation.yaml")
    )
    raw = pd.read_csv(data_dir / "ch01_06_ed_visits.csv")

    cleaner = eventus.EventsCleaner(raw, sem, config)
    events = cleaner.clean()

    n_input = 5_459
    n_clean = len(events.data)
    n_rejected = len(cleaner.rejected)
    consolidated_away = n_input - n_clean - n_rejected

    assert n_rejected == 2_069
    assert consolidated_away == 35           # combined, not rejected
    assert n_clean + n_rejected + consolidated_away == n_input
    # The DataFrame report surfaces consolidation as its own "merged" action.
    qr = cleaner.quality_report_df()
    merged_rows = qr[qr["action"] == "merged"]
    assert int(merged_rows["n"].sum()) == 35


def test_ch02_nursing_facility_aggregation(asset, data_dir):
    sem = eventus.EpisodeSemantics.build_from_yaml(
        asset("chapter_02_descriptor_aggregation", "configs", "nursing_facility_semantics.yaml")
    )
    config = eventus.EpisodesCleanerConfig.build_from_yaml(
        asset("chapter_02_descriptor_aggregation", "configs", "nursing_facility_cleaner.yaml")
    )
    raw = pd.read_csv(data_dir / "ch02_03_nursing_facility_assessments.csv")

    episodes = eventus.EpisodesCleaner(raw, sem, config).clean()

    assert len(episodes.data) == 227
    assert episodes.data[sem.entity_id_col].nunique() == 200
