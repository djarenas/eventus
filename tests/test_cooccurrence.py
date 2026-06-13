"""Vignette-pinned tests for event co-occurrence (Chapters 8-10), the
cirrhosis-diagnosis x ED-visit signal simulation (simul_1).

These exercise the full two-stream pipeline: clean two event streams,
clip to a shared observation period, assemble a CohortTimeline, and run
presence, gap-timing, and directionality analysis. The permutation tests
default to seed=42, so the gap ratios and directionality statistics are
reproducible and pinned here.

Numbers match the manuscript: among 5,000 patients, 56 have both events,
the prevalence ratio is 1.71 (Fisher p approximately 1.3e-06), the gap
ratios are 0.369 (cirrhosis->ED) and 0.466 (ED->cirrhosis), and the
directionality test gives direction_ratio 1.50 with fraction_a_first 74.5%.
"""
from __future__ import annotations

import pandas as pd
import pytest

import eventus

COHORT_SIZE = 5_000
ENTITY_COL = "patient_id"


@pytest.fixture
def simul1_analyzer(asset, data_dir):
    """Build the EventCoOccurrenceAnalyzer for the simul_1 signal cohort."""
    configs = asset("chapter_08_coevents", "configs")
    all_ids = [f"D{str(i).zfill(4)}" for i in range(1, COHORT_SIZE + 1)]

    obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
        entity_ids=all_ids,
        start="2022-01-01",
        end="2022-12-31",
        entity_col=ENTITY_COL,
        identity="calendar_2022",
    )

    def clean_stream(csv_name, sem_yaml, cfg_yaml):
        raw = pd.read_csv(data_dir / csv_name)
        sem = eventus.EventSemantics.build_from_yaml(configs / sem_yaml)
        cfg = eventus.EventsCleanerConfig.build_from_yaml(configs / cfg_yaml)
        cleaned = eventus.EventsCleaner(raw, sem, cfg).clean()
        return eventus.EventsFilter(cleaned).to_obs_period(obs).result

    stream_a = clean_stream(
        "ch08_11_simul1_cirrhosis_dx.csv",
        "cirrhosis_ch08_semantics.yaml",
        "cirrhosis_ch08_cleaner.yaml",
    )
    stream_b = clean_stream(
        "ch08_11_simul1_ed_visits.csv",
        "ed_ch08_semantics.yaml",
        "ed_ch08_cleaner.yaml",
    )

    ct = eventus.CohortTimeline.build_from_components(
        obs_period=obs, events=[stream_a, stream_b]
    )
    return eventus.EventCoOccurrenceAnalyzer(
        cohort_timeline=ct,
        identity_a="cirrhosis_diagnosis",
        identity_b="ed_visit",
    )


def test_ch08_presence(simul1_analyzer):
    p = simul1_analyzer.compute_presence()
    assert p.n_with_a == 90
    assert p.n_with_b == 1_847
    assert p.n_with_both == 56
    assert p.n_with_neither == 3_119
    # The four cells partition the full cohort.
    assert p.n_with_both + (p.n_with_a - p.n_with_both) + (p.n_with_b - p.n_with_both) + p.n_with_neither == COHORT_SIZE
    assert p.prevalence_ratio == pytest.approx(1.706, abs=0.01)
    assert p.fisher_exact_p < 1e-5


def test_ch09_gap_timing(simul1_analyzer):
    gaps = simul1_analyzer.compute_gaps()
    test = eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(n_permutations=500)
    assert test.n_co_occurring == 56
    # Seeded (seed=42): ratios are reproducible. Both directions show
    # observed gaps well under the independence null (ratio < 1).
    assert test.gap_ratio_a_to_b == pytest.approx(0.369, abs=0.02)
    assert test.gap_ratio_b_to_a == pytest.approx(0.466, abs=0.02)


def test_ch10_directionality(simul1_analyzer):
    directionality = simul1_analyzer.compute_directionality()
    test = eventus.EventCoOccurrenceDirectionalityAnalyzer(directionality).compute_test(
        n_permutations=500
    )
    assert test.n_co_occurring == 56
    # Seeded (seed=42): cirrhosis precedes ED in ~74.5% of co-occurring patients.
    assert test.fraction_a_first == pytest.approx(0.745, abs=0.02)
    assert test.direction_ratio == pytest.approx(1.498, abs=0.03)
    assert test.wilcoxon_p == pytest.approx(0.049, abs=0.01)
