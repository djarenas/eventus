# events object already built from Vignette 1.
# If it exists, it is structurally sound — guaranteed by the constructor.

from eventus import (
    EventSemantics,
    ObsPeriodPerEntity,
    EventsWithinObsPeriodsAnalyzer,
    StackedTimelinePlotter,
    StackedTimelineConfig,
)

# ── Semantics ─────────────────────────────────────────────────────────────
sem = EventSemantics(
    entity_id_col  = "patient_id",
    start_time_col = "admit_date",
    end_time_col   = "discharge_date",
    identity       = "inpatient_hospitalization",
)

# ── Observation period — fixed calendar year ──────────────────────────────
obs = ObsPeriodPerEntity.from_calendar(
    entity_ids = patient_ids,
    start      = "2022-01-01",
    end        = "2022-12-31",
    entity_col = "patient_id",
    identity   = "medicaid_2022",
)

# ── Plot ──────────────────────────────────────────────────────────────────
config = StackedTimelineConfig.build_from_yaml("timeline_config.yaml")

StackedTimelinePlotter.from_objects(
    obs_period = obs,
    events     = events,
    config     = config,
).plot("timeline_2022.png")
