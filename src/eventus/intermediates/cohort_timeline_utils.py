"""
cohort_timeline_utils.py
Validation, schema inference, and assembly utilities for CohortTimeline.
No class state — only data inputs and outputs.
"""
from __future__ import annotations
import warnings
import pandas as pd

_ERROR = "[CohortTimeline]"

# ------------------------------------------------------------------ #
# Column name constants
# ------------------------------------------------------------------ #

OBS_START_COL    = "obs_start"
OBS_END_COL      = "obs_end"
OBS_DURATION_COL = "obs_duration_days"

# ------------------------------------------------------------------ #
# Reserved identity fragment sets
#
# Split identities on "_" and check whole fragments only.
# "computer_time" → ["computer", "time"] — safe
# "comp_time"     → ["comp", "time"]     — correctly raises
# ------------------------------------------------------------------ #

_RESERVED_IDENTITY_FRAGMENTS_ERROR = {
    "comp",   # corrupts the occ_comp_ prefix: occ_comp_comp_x_n is unparseable
}

_RESERVED_IDENTITY_FRAGMENTS_WARN = {
    "n", "first", "last", "time", "to", "recency", "days",
    "mean", "gap", "std", "cv", "min", "max",
    "burstiness", "memory", "density", "center", "mass",
    "starts", "ends", "within", "vs",  # cross_comp relationship keywords
}

# ------------------------------------------------------------------ #
# Column name helpers
# ------------------------------------------------------------------ #

def evt_starts_col(identity: str) -> str:
    return f"evt_{identity}_starts"

def evt_ends_col(identity: str) -> str:
    return f"evt_{identity}_ends"

def occ_col(identity: str) -> str:
    return f"occ_{identity}"

def occ_comp_col(identity: str, stat: str) -> str:
    return f"occ_comp_{identity}_{stat}"

# ------------------------------------------------------------------ #
# Schema inference
# ------------------------------------------------------------------ #

def infer_event_identities(columns: list[str]) -> list[str]:
    """
    Return sorted list of event identities where both
    evt_{id}_starts AND evt_{id}_ends columns exist.
    """
    starts_ids = set()
    ends_ids   = set()
    for col in columns:
        if col.startswith("evt_") and col.endswith("_starts"):
            starts_ids.add(col[4:-7])
        if col.startswith("evt_") and col.endswith("_ends"):
            ends_ids.add(col[4:-5])
    return sorted(starts_ids & ends_ids)


def infer_occurrence_identities(columns: list[str]) -> list[str]:
    """
    Return sorted list of raw occurrence identities.
    Raw occurrence columns are occ_{identity} — excludes occ_comp_ columns.
    """
    return sorted(
        col[4:] for col in columns
        if col.startswith("occ_")
        and not col.startswith("occ_comp_")
    )


def infer_computed_occurrence_identities(columns: list[str]) -> list[str]:
    """
    Return sorted list of occurrence identities that have been computed
    (i.e. have at least one occ_comp_{identity}_{stat} column present).

    Parses identity as everything between "occ_comp_" prefix and the
    final "_{stat}" suffix. Relies on stat names being a closed set —
    identity names must not collide with reserved fragments.
    """
    return sorted({
        "_".join(col[9:].split("_")[:-1])  # strip "occ_comp_" and trailing stat
        for col in columns
        if col.startswith("occ_comp_")
    })

# ------------------------------------------------------------------ #
# Identity name validation
# ------------------------------------------------------------------ #

def validate_identity_name(identity: str) -> None:
    """
    Raise if identity contains reserved fragments that would corrupt the
    occ_comp_ column namespace. Warn if fragments may cause ambiguity.

    Checks whole fragments only (split on "_") so "computer_time" is safe
    while "comp_time" correctly raises on "comp".
    """
    fragments = set(identity.split("_"))

    hard_conflicts = fragments & _RESERVED_IDENTITY_FRAGMENTS_ERROR
    if hard_conflicts:
        raise ValueError(
            f"{_ERROR} occurrence identity '{identity}' contains reserved "
            f"fragment(s) {sorted(hard_conflicts)} which would corrupt the "
            f"occ_comp_ column namespace. Consider renaming the identity."
        )

    soft_conflicts = fragments & _RESERVED_IDENTITY_FRAGMENTS_WARN
    if soft_conflicts:
        warnings.warn(
            f"{_ERROR} occurrence identity '{identity}' contains reserved "
            f"fragment(s) {sorted(soft_conflicts)} which may cause "
            f"occ_comp_ columns to be ambiguous when inferred. "
            f"Consider renaming the identity.",
            UserWarning,
            stacklevel=3,
        )

# ------------------------------------------------------------------ #
# Validation
# ------------------------------------------------------------------ #

def validate_entity_col(data: pd.DataFrame, entity_col: str) -> None:
    if entity_col not in data.columns:
        raise ValueError(
            f"{_ERROR} entity_col '{entity_col}' not found in DataFrame. "
            f"Available columns: {sorted(data.columns.tolist())}"
        )
    if data[entity_col].isnull().any():
        n = int(data[entity_col].isnull().sum())
        raise ValueError(
            f"{_ERROR} entity_col '{entity_col}' has {n} null value(s). "
            f"Every entity must be identified."
        )
    if data[entity_col].duplicated().any():
        dupes = data[entity_col][data[entity_col].duplicated()].tolist()
        raise ValueError(
            f"{_ERROR} entity_col '{entity_col}' is not unique. "
            f"Duplicate values: {dupes[:10]}"
            f"{'...' if len(dupes) > 10 else ''}. "
            f"CohortTimeline requires one row per entity."
        )


def validate_obs_period_cols(columns: list[str]) -> None:
    has_start = OBS_START_COL in columns
    has_end   = OBS_END_COL   in columns
    if has_start and not has_end:
        raise ValueError(
            f"{_ERROR} '{OBS_START_COL}' present but '{OBS_END_COL}' missing. "
            f"Observation period columns must be paired."
        )
    if has_end and not has_start:
        raise ValueError(
            f"{_ERROR} '{OBS_END_COL}' present but '{OBS_START_COL}' missing. "
            f"Observation period columns must be paired."
        )


def validate_event_cols(columns: list[str]) -> None:
    starts_ids = set()
    ends_ids   = set()
    for col in columns:
        if col.startswith("evt_") and col.endswith("_starts"):
            starts_ids.add(col[4:-7])
        if col.startswith("evt_") and col.endswith("_ends"):
            ends_ids.add(col[4:-5])

    unpaired_starts = starts_ids - ends_ids
    unpaired_ends   = ends_ids   - starts_ids

    if unpaired_starts:
        raise ValueError(
            f"{_ERROR} Event identities have '_starts' but no '_ends': "
            f"{sorted(unpaired_starts)}. Event columns must be paired."
        )
    if unpaired_ends:
        raise ValueError(
            f"{_ERROR} Event identities have '_ends' but no '_starts': "
            f"{sorted(unpaired_ends)}. Event columns must be paired."
        )


def validate_no_duplicate_identities(
    event_identities:      list[str],
    occurrence_identities: list[str],
) -> None:
    if len(event_identities) != len(set(event_identities)):
        dupes = sorted(set(i for i in event_identities
                           if event_identities.count(i) > 1))
        raise ValueError(
            f"{_ERROR} Duplicate event identities: {dupes}."
        )
    if len(occurrence_identities) != len(set(occurrence_identities)):
        dupes = sorted(set(i for i in occurrence_identities
                           if occurrence_identities.count(i) > 1))
        raise ValueError(
            f"{_ERROR} Duplicate occurrence identities: {dupes}."
        )


def validate_at_least_one_layer(
    has_obs_period:        bool,
    event_identities:      list[str],
    occurrence_identities: list[str],
) -> None:
    if not has_obs_period and not event_identities and not occurrence_identities:
        raise ValueError(
            f"{_ERROR} At least one layer must be present: an observation "
            f"period, at least one event identity, or at least one occurrence "
            f"identity."
        )

# ------------------------------------------------------------------ #
# Assembly helpers for build_from_components
# ------------------------------------------------------------------ #

def build_obs_period_df(obs_period, entity_col: str) -> pd.DataFrame:
    """
    Extract and normalize the obs period into a spine DataFrame with
    obs_start, obs_end, obs_duration_days columns.
    """
    obs_start_col = obs_period.semantics.start_time_col
    obs_end_col   = obs_period.semantics.end_time_col

    result = obs_period.data[[entity_col, obs_start_col, obs_end_col]].copy()
    result = result.rename(columns={
        obs_start_col: OBS_START_COL,
        obs_end_col:   OBS_END_COL,
    })
    result[OBS_START_COL]    = pd.to_datetime(result[OBS_START_COL]).dt.normalize()
    result[OBS_END_COL]      = pd.to_datetime(result[OBS_END_COL]).dt.normalize()
    result[OBS_DURATION_COL] = (
        result[OBS_END_COL] - result[OBS_START_COL]
    ).dt.days.astype(float)
    return result.reset_index(drop=True)


def build_entity_spine(events_list: list, occ_list: list, entity_col: str) -> pd.DataFrame:
    """
    Build a minimal entity spine when no obs period is provided.
    Uses the first available events or occurrences object.
    """
    source = events_list[0] if events_list else occ_list[0]
    return (
        source.data[[entity_col]]
        .drop_duplicates()
        .reset_index(drop=True)
        .copy()
    )


def attach_event_columns(
    result:      pd.DataFrame,
    evt:         object,
    entity_col:  str,
) -> pd.DataFrame:
    """
    Pipe-delimit starts and ends for one Events object and merge into result.
    """
    identity   = evt.semantics.identity
    start_col  = evt.semantics.start_time_col
    end_col    = evt.semantics.end_time_col
    starts_out = evt_starts_col(identity)
    ends_out   = evt_ends_col(identity)

    evt_data = evt.data.copy()
    evt_data[start_col] = pd.to_datetime(evt_data[start_col]).dt.normalize()
    evt_data[end_col]   = pd.to_datetime(evt_data[end_col]).dt.normalize()
    evt_sorted = evt_data.sort_values([entity_col, start_col])

    starts_pipe = (
        evt_sorted.groupby(entity_col)[start_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(starts_out)
    )
    ends_pipe = (
        evt_sorted.groupby(entity_col)[end_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(ends_out)
    )

    result = result.merge(starts_pipe, on=entity_col, how="left")
    result = result.merge(ends_pipe,   on=entity_col, how="left")
    return result


def attach_occurrence_columns(
    result:     pd.DataFrame,
    occ:        object,
    entity_col: str,
) -> pd.DataFrame:
    """
    Pipe-delimit occurrence dates for one Occurrences object and merge into result.
    """
    identity = occ.semantics.identity
    date_col = occ.semantics.date_col
    out_col  = occ_col(identity)

    occ_data = occ.data.copy()
    occ_data[date_col] = pd.to_datetime(occ_data[date_col]).dt.normalize()

    pipe_col = (
        occ_data.sort_values([entity_col, date_col])
        .groupby(entity_col)[date_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(out_col)
    )

    return result.merge(pipe_col, on=entity_col, how="left")


def attach_occ_comp_columns(
    data:       pd.DataFrame,
    stats_df:   pd.DataFrame,
    identity:   str,
) -> pd.DataFrame:
    """
    Attach computed occurrence stat columns (occ_comp_{identity}_{stat})
    to data. Overwrites any existing columns with the same names.
    """
    result = data.copy()
    for stat_col in stats_df.columns:
        result[occ_comp_col(identity, stat_col)] = stats_df[stat_col].values
    return result


def validate_components(
    obs_period:  object,
    events_list: list,
    occ_list:    list,
) -> None:
    """
    Type, identity, and name checks on raw components before assembly.
    """
    from eventus.data_objects.events import Events
    from eventus.data_objects.occurrences import Occurrences
    from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

    if obs_period is not None and not isinstance(obs_period, ObsPeriodPerEntity):
        raise TypeError(
            f"{_ERROR} obs_period must be an ObsPeriodPerEntity object, "
            f"got {type(obs_period).__name__}"
        )
    for i, evt in enumerate(events_list):
        if not isinstance(evt, Events):
            raise TypeError(
                f"{_ERROR} events[{i}] must be an Events object, "
                f"got {type(evt).__name__}"
            )
        if not evt.semantics.identity:
            raise ValueError(
                f"{_ERROR} events[{i}] has no identity. "
                f"Set identity in EventSemantics."
            )
    for i, o in enumerate(occ_list):
        if not isinstance(o, Occurrences):
            raise TypeError(
                f"{_ERROR} occurrences[{i}] must be an Occurrences object, "
                f"got {type(o).__name__}"
            )
        if not o.semantics.identity:
            raise ValueError(
                f"{_ERROR} occurrences[{i}] has no identity. "
                f"Set identity in OccurrenceSemantics."
            )
        validate_identity_name(o.semantics.identity)


def resolve_entity_col(obs_period, events_list: list, occ_list: list) -> str:
    if obs_period is not None:
        return obs_period.semantics.entity_id_col
    if events_list:
        return events_list[0].semantics.entity_id_col
    return occ_list[0].semantics.entity_id_col


def normalize_to_list(obj, expected_type, label: str) -> list:
    """
    Accept a single instance or a list. Raise clearly if wrong type.
    """
    if obj is None:
        return []
    if isinstance(obj, expected_type):
        return [obj]
    if isinstance(obj, list):
        return obj
    raise TypeError(
        f"{_ERROR} {label} must be a {expected_type.__name__} or list, "
        f"got {type(obj).__name__}"
    )
