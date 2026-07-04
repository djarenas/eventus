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


# --------------------------------------------------------------------------- #
# Null-model options (uniform_monte_carlo, rotation, label_permutation)
# --------------------------------------------------------------------------- #

NULL_METHODS = ["uniform_monte_carlo", "rotation", "label_permutation"]


def test_gap_default_null_method_is_uniform_monte_carlo(simul1_analyzer):
    """Default null_method is uniform_monte_carlo and is reported honestly."""
    gaps = simul1_analyzer.compute_gaps()
    test = eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(n_permutations=200)
    assert test.null_method == "uniform_monte_carlo"


@pytest.mark.parametrize("null_method", NULL_METHODS)
def test_gap_all_null_methods_run(simul1_analyzer, null_method):
    """All three gap nulls run, report their own method, and give finite p-values."""
    gaps = simul1_analyzer.compute_gaps()
    test = eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(
        n_permutations=200, null_method=null_method
    )
    assert test.null_method == null_method
    assert test.n_co_occurring == 56
    assert 0.0 <= test.ks_p_a_to_b <= 1.0
    assert 0.0 <= test.ks_p_b_to_a <= 1.0


@pytest.mark.parametrize("null_method", NULL_METHODS)
def test_directionality_all_null_methods_run(simul1_analyzer, null_method):
    """All three directionality nulls run and report their own method."""
    directionality = simul1_analyzer.compute_directionality()
    test = eventus.EventCoOccurrenceDirectionalityAnalyzer(directionality).compute_test(
        n_permutations=200, null_method=null_method
    )
    assert test.null_method == null_method
    assert test.n_co_occurring == 56


def test_n_iterations_alias(simul1_analyzer):
    """n_iterations overrides n_permutations when both are given."""
    gaps = simul1_analyzer.compute_gaps()
    test = eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(
        n_permutations=999, n_iterations=150
    )
    assert test.n_permutations == 150


def test_invalid_null_method_raises(simul1_analyzer):
    gaps = simul1_analyzer.compute_gaps()
    with pytest.raises(ValueError):
        eventus.EventCoOccurrenceGapAnalyzer(gaps).compute_test(null_method="bogus")


def test_rotation_preserves_burstiness_vs_uniform_monte_carlo():
    """
    Discrimination test: on data where each type is bursty but A and B are
    temporally independent, the uniform Monte Carlo null can register a
    proximity signal that the rotation null (which preserves each type's own
    clustering) does not. This is the whole point of offering the rotation
    null, so we guard it here.

    Construction: 400 entities over a 0-3650 day window. Each entity has a
    tight cluster of A events and a tight cluster of B events, each placed
    at an INDEPENDENT random location — so within-type burstiness is high
    but there is no genuine A-B relationship.
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(7)
    n_entities = 400
    window_days = 3650
    start = pd.Timestamp("2010-01-01")

    def cluster(center, k):
        # k events within +/- 5 days of an independent center, clipped to window
        pts = np.clip(center + rng.integers(-5, 6, size=k), 0, window_days)
        return sorted(start + pd.to_timedelta(np.unique(pts), unit="D"))

    rows = []
    for i in range(n_entities):
        a_center = rng.integers(0, window_days)
        b_center = rng.integers(0, window_days)   # independent of a_center
        dates_a = cluster(a_center, 6)
        dates_b = cluster(b_center, 6)
        obs_start = start
        obs_end   = start + pd.Timedelta(days=window_days)
        a_off = [float((d - obs_start).days) for d in dates_a]
        b_off = [float((d - obs_start).days) for d in dates_b]
        gaps_ab = [min(abs((d - t).days) for t in dates_b) for d in dates_a]
        gaps_ba = [min(abs((d - t).days) for t in dates_a) for d in dates_b]
        rows.append({
            "entity_id": f"E{i}",
            "obs_start": obs_start,
            "obs_end":   obs_end,
            "n_a": len(dates_a),
            "n_b": len(dates_b),
            "median_gap_a_to_nearest_b": float(np.median(gaps_ab)),
            "median_gap_b_to_nearest_a": float(np.median(gaps_ba)),
            "a_offsets": a_off,
            "b_offsets": b_off,
        })

    data = pd.DataFrame(rows)
    summary = eventus.EventCoOccurrenceGapSummary(
        data=data, entity_col="entity_id",
        identity_a="A", identity_b="B",
    )
    analyzer = eventus.EventCoOccurrenceGapAnalyzer(summary)

    mc  = analyzer.compute_test(n_permutations=300, null_method="uniform_monte_carlo", seed=1)
    rot = analyzer.compute_test(n_permutations=300, null_method="rotation",    seed=1)

    # A and B are temporally independent, so a well-specified null should give
    # gap_ratio ~ 1 (no signal). The rotation null preserves each type's own
    # clustering and lands near 1; the uniform Monte Carlo null misspecifies
    # the marginal timing and produces a spurious ratio far from 1. We assert
    # rotation is markedly closer to 1 than uniform_monte_carlo.
    assert abs(rot.gap_ratio_a_to_b - 1.0) < abs(mc.gap_ratio_a_to_b - 1.0)
