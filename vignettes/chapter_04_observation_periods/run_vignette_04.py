"""
run_vignette_04.py — Chapter 4: Handling Observation Periods
Main: Fixed calendar observation period (2022)

Usage:
    python vignettes/chapter_04_observation_periods/run_vignette_04.py

Generate synthetic data first if needed:
    python vignettes/data/generate_vignette_data.py
"""
import eventus
import pathlib
import pandas as pd

HERE = pathlib.Path(__file__).parent

# ── Step 1 — Load and clean coverage data ────────────────────────────────────

raw_df  = pd.read_csv(HERE.parent / "data" / "simulated_medicaid_coverage.csv")
sem     = eventus.EventSemantics.build_from_yaml(HERE / "configs" / "medicaid_coverage_semantics.yaml")
config  = eventus.EventsCleanerConfig.build_from_yaml(HERE / "configs" / "medicaid_coverage_cleaner.yaml")
cleaner = eventus.EventsCleaner(raw_df, sem, config)
events  = cleaner.clean()

cleaner.print_report()
print(events)

# ── Step 2 — Define observation period ───────────────────────────────────────

obs = eventus.ObsPeriodPerEntity.construct_from_calendar(
    entity_ids = events.data["patient_id"].unique(),
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "calendar_2022",
)

# ── Step 3 — Filter events to obs period ─────────────────────────────────────

events = eventus.EventsFilter(events).to_obs_period(obs, clip=True).result
print(f"\nCoverage periods after filtering to 2022: {len(events):,}")

# ── Step 4 — Assemble CohortTimeline ─────────────────────────────────────────

ct = eventus.CohortTimeline.build_from_components(
    obs_period = obs,
    events     = events,
)

# ── Step 5 — Enrich with coverage analysis ───────────────────────────────────

analyzer = eventus.CohortTimelineEventAnalyzer(ct, "medicaid_coverage")
ct_enriched = analyzer.enrich_with_event_coverage()

# ── Step 6 — Coverage summary ─────────────────────────────────────────────────

summary = analyzer.get_summary()
print(summary)
