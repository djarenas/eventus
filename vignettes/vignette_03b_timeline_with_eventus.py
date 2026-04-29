# events object already built from Vignette 1.
# If it exists, it is structurally sound — guaranteed by the constructor.

from eventus import (
    EventSemantics,
    ObsPeriodPerEntity,
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

# ── Observation period — age 65 to 66 ────────────────────────────────────
obs = ObsPeriodPerEntity.from_age_window(
    entity_df  = demographics_df,
    dob_col    = "date_of_birth",
    age_start  = 65,
    age_end    = 66,
    entity_col = "patient_id",
    age_unit   = "years",
    identity   = "age_65_to_66",
)

# ── Plot ──────────────────────────────────────────────────────────────────
config = StackedTimelineConfig.build_from_yaml("timeline_config.yaml")

StackedTimelinePlotter.from_objects(
    obs_period = obs,
    events     = events,
    config     = config,
).plot("timeline_age_65_to_66.png")
