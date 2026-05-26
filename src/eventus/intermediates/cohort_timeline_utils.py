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
    "comp",   # corrupts the evt_comp_ prefix: evt_comp_comp_x_n is unparseable
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

def eps_starts_col(identity: str) -> str:
    return f"eps_{identity}_starts"

def eps_ends_col(identity: str) -> str:
    return f"eps_{identity}_ends"

def eps_descriptor_col(identity: str, col: str) -> str:
    """Column name for a descriptor carried from an Episodes object."""
    return f"eps_{identity}_{col}"

def evt_col(identity: str) -> str:
    return f"evt_{identity}"

def evt_descriptor_col(identity: str, col: str) -> str:
    """Column name for a descriptor carried from an Events object."""
    return f"evt_{identity}_{col}"

def evt_comp_col(identity: str, stat: str) -> str:
    return f"evt_comp_{identity}_{stat}"

# ------------------------------------------------------------------ #
# Schema inference
# ------------------------------------------------------------------ #

def infer_episode_identities(columns: list[str]) -> list[str]:
    """
    Return sorted list of episode identities where both
    eps_{id}_starts AND eps_{id}_ends columns exist.
    """
    starts_ids = set()
    ends_ids   = set()
    for col in columns:
        if col.startswith("eps_") and col.endswith("_starts"):
            starts_ids.add(col[4:-7])
        if col.startswith("eps_") and col.endswith("_ends"):
            ends_ids.add(col[4:-5])
    return sorted(starts_ids & ends_ids)


def infer_episode_descriptor_cols(
    columns:    list[str],
    identities: list[str],
) -> dict[str, list[str]]:
    """
    Return a dict mapping each episode identity to its list of
    descriptor column names carried in the CohortTimeline.

    e.g. {"inpatient_hospitalization": ["hospital_id", "icd10_condition"]}

    Parameters
    ----------
    columns    : All column names in the CohortTimeline DataFrame.
    identities : Known episode identities from infer_episode_identities().
    """
    result = {identity: [] for identity in identities}
    for col in columns:
        if not col.startswith("eps_"):
            continue
        # Exclude _starts and _ends columns
        if col.endswith("_starts") or col.endswith("_ends"):
            continue
        suffix = col[4:]  # strip "eps_"
        for identity in identities:
            prefix = identity + "_"
            if suffix.startswith(prefix):
                descriptor = suffix[len(prefix):]
                result[identity].append(descriptor)
    return result


def infer_event_identities(columns: list[str]) -> list[str]:
    """
    Return sorted list of raw event identities.

    Raw event columns are evt_{identity} — the date pipe-delimited
    column. Excludes:
      - evt_comp_* computed columns
      - evt_{identity}_{descriptor} descriptor columns

    To distinguish evt_{identity} from evt_{identity}_{descriptor}, we
    build the set of all evt_* column suffixes and keep only those that
    are not a prefix of another evt_* column (i.e. no other column starts
    with evt_{suffix}_).
    """
    # All evt_* columns that are not evt_comp_*
    candidates = [
        col[4:] for col in columns
        if col.startswith("evt_")
        and not col.startswith("evt_comp_")
    ]

    # A candidate is a pure identity if no other candidate starts with it + "_"
    # e.g. "ed_visit" is kept because no candidate starts with "ed_visit_"
    # but "ed_visit_icd10_condition" would be filtered because... wait,
    # "ed_visit_icd10_condition" itself starts with "ed_visit_" which IS a known identity.
    # So: a candidate is a descriptor suffix if it starts with any other candidate + "_"

    candidate_set = set(candidates)
    identities = []
    for c in candidates:
        # Check if c starts with any other candidate followed by "_"
        is_descriptor = any(
            c.startswith(other + "_")
            for other in candidate_set
            if other != c
        )
        if not is_descriptor:
            identities.append(c)

    return sorted(set(identities))


def infer_event_descriptor_cols(
    columns:    list[str],
    identities: list[str],
) -> dict[str, list[str]]:
    """
    Return a dict mapping each event identity to its list of
    descriptor column names carried in the CohortTimeline.

    e.g. {"ed_visit": ["icd10_condition", "systolic_bp", "hospital_id"]}

    Parameters
    ----------
    columns    : All column names in the CohortTimeline DataFrame.
    identities : Known event identities from infer_event_identities().
    """
    result = {identity: [] for identity in identities}
    for col in columns:
        if not col.startswith("evt_") or col.startswith("evt_comp_"):
            continue
        suffix = col[4:]  # strip "evt_"
        for identity in identities:
            prefix = identity + "_"
            if suffix.startswith(prefix):
                descriptor = suffix[len(prefix):]
                result[identity].append(descriptor)
    return result


def infer_computed_event_identities(
    columns:              list[str],
    event_identities: list[str],
) -> list[str]:
    """
    Return sorted list of event identities that have been computed
    (i.e. have at least one evt_comp_{identity}_{stat} column present).

    Matches against known event_identities to correctly handle
    multi-fragment stat names (e.g. "time_to_1", "mean_gap").
    """
    return sorted({
        identity
        for col in columns
        if col.startswith("evt_comp_")
        for identity in event_identities
        if col[9:].startswith(identity + "_")
    })


def infer_computed_episode_identities(
    columns:          list[str],
    episode_identities: list[str],
) -> list[str]:
    """
    Return sorted list of episode identities that have been computed
    (i.e. have at least one eps_comp_{identity}_{stat} column present).

    Matches against known episode_identities to correctly handle
    multi-fragment stat names (e.g. "active_days", "first_start").
    """
    return sorted({
        identity
        for col in columns
        if col.startswith("eps_comp_")
        for identity in episode_identities
        if col[9:].startswith(identity + "_")
    })

# ------------------------------------------------------------------ #
# Identity name validation
# ------------------------------------------------------------------ #

def validate_identity_name(identity: str) -> None:
    """
    Raise if identity contains reserved fragments that would corrupt the
    evt_comp_ column namespace. Warn if fragments may cause ambiguity.

    Checks whole fragments only (split on "_") so "computer_time" is safe
    while "comp_time" correctly raises on "comp".
    """
    fragments = set(identity.split("_"))

    hard_conflicts = fragments & _RESERVED_IDENTITY_FRAGMENTS_ERROR
    if hard_conflicts:
        raise ValueError(
            f"{_ERROR} event identity '{identity}' contains reserved "
            f"fragment(s) {sorted(hard_conflicts)} which would corrupt the "
            f"evt_comp_ column namespace. Consider renaming the identity."
        )

    soft_conflicts = fragments & _RESERVED_IDENTITY_FRAGMENTS_WARN
    if soft_conflicts:
        warnings.warn(
            f"{_ERROR} event identity '{identity}' contains reserved "
            f"fragment(s) {sorted(soft_conflicts)} which may cause "
            f"evt_comp_ columns to be ambiguous when inferred. "
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


def validate_episode_cols(columns: list[str]) -> None:
    starts_ids = set()
    ends_ids   = set()
    for col in columns:
        if col.startswith("eps_") and col.endswith("_starts"):
            starts_ids.add(col[4:-7])
        if col.startswith("eps_") and col.endswith("_ends"):
            ends_ids.add(col[4:-5])

    unpaired_starts = starts_ids - ends_ids
    unpaired_ends   = ends_ids   - starts_ids

    if unpaired_starts:
        raise ValueError(
            f"{_ERROR} Episode identities have '_starts' but no '_ends': "
            f"{sorted(unpaired_starts)}. Episode columns must be paired."
        )
    if unpaired_ends:
        raise ValueError(
            f"{_ERROR} Episode identities have '_ends' but no '_starts': "
            f"{sorted(unpaired_ends)}. Episode columns must be paired."
        )

    known_identities    = starts_ids & ends_ids
    computed_identities = infer_computed_episode_identities(columns, list(known_identities))
    orphaned = [i for i in computed_identities if i not in known_identities]
    if orphaned:
        raise ValueError(
            f"{_ERROR} Computed episode identities have no corresponding "
            f"eps_{{identity}}_starts/ends columns: {orphaned}. "
            f"Every eps_comp_{{identity}}_* column requires a matching "
            f"eps_{{identity}}_starts and eps_{{identity}}_ends column."
        )


def validate_event_cols(columns: list[str]) -> None:
    known_identities    = set(infer_event_identities(columns))
    computed_identities = infer_computed_event_identities(columns, list(known_identities))
    orphaned = [i for i in computed_identities if i not in known_identities]
    if orphaned:
        raise ValueError(
            f"{_ERROR} Computed event identities have no corresponding "
            f"evt_{{identity}} column: {orphaned}. "
            f"Every evt_comp_{{identity}}_* column requires a matching "
            f"evt_{{identity}} column."
        )


def validate_no_duplicate_identities(
    episode_identities:      list[str],
    event_identities: list[str],
) -> None:
    if len(episode_identities) != len(set(episode_identities)):
        dupes = sorted(set(i for i in episode_identities
                           if episode_identities.count(i) > 1))
        raise ValueError(
            f"{_ERROR} Duplicate episode identities: {dupes}."
        )
    if len(event_identities) != len(set(event_identities)):
        dupes = sorted(set(i for i in event_identities
                           if event_identities.count(i) > 1))
        raise ValueError(
            f"{_ERROR} Duplicate event identities: {dupes}."
        )


def validate_at_least_one_layer(
    has_obs_period:        bool,
    episode_identities:      list[str],
    event_identities: list[str],
) -> None:
    if not has_obs_period and not episode_identities and not event_identities:
        raise ValueError(
            f"{_ERROR} At least one layer must be present: an observation "
            f"period, at least one episode identity, or at least one event "
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


def build_entity_spine(episodes_list: list, evt_list: list, entity_col: str) -> pd.DataFrame:
    """
    Build a minimal entity spine when no obs period is provided.
    Uses the first available episodes or events object.
    """
    source = episodes_list[0] if episodes_list else evt_list[0]
    return (
        source.data[[entity_col]]
        .drop_duplicates()
        .reset_index(drop=True)
        .copy()
    )


def attach_episode_columns(
    result:      pd.DataFrame,
    evt:         object,
    entity_col:  str,
) -> pd.DataFrame:
    """
    Pipe-delimit starts, ends, and descriptor columns for one Episodes
    object and merge into result.

    Produces:
      eps_{identity}_starts       — pipe-delimited start dates (always)
      eps_{identity}_ends         — pipe-delimited end dates (always)
      eps_{identity}_{col}        — pipe-delimited also_defined_by columns
      eps_{identity}_{col}        — aggregated descriptor columns
                                    per DescriptorColConfig.timeline:
                                    "sequence" — pipe-delimit in episode order
                                    "unique"   — unique values, sorted
                                    "average"  — mean across episodes (numeric)
                                    "none"     — not carried
    """
    identity  = evt.semantics.identity
    start_col = evt.semantics.start_time_col
    end_col   = evt.semantics.end_time_col
    starts_out = eps_starts_col(identity)
    ends_out   = eps_ends_col(identity)

    also_defined_by = evt.semantics.also_defined_by or []
    descriptor_cols = evt.semantics.descriptor_cols or {}

    eps_data = evt.data.copy()
    eps_data[start_col] = pd.to_datetime(eps_data[start_col]).dt.normalize()
    eps_data[end_col]   = pd.to_datetime(eps_data[end_col]).dt.normalize()
    eps_sorted = eps_data.sort_values([entity_col, start_col])

    # ── Starts and ends ───────────────────────────────────────────────────
    starts_pipe = (
        eps_sorted.groupby(entity_col)[start_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(starts_out)
    )
    ends_pipe = (
        eps_sorted.groupby(entity_col)[end_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(ends_out)
    )
    result = result.merge(starts_pipe, on=entity_col, how="left")
    result = result.merge(ends_pipe,   on=entity_col, how="left")

    # ── also_defined_by columns — always sequence, always atomic ─────────
    for col in also_defined_by:
        if col not in eps_data.columns:
            continue
        out = eps_descriptor_col(identity, col)
        pipe_col = (
            eps_sorted.groupby(entity_col)[col]
            .apply(lambda s: " | ".join(str(v) for v in s))
            .rename(out)
        )
        result = result.merge(pipe_col, on=entity_col, how="left")

    # ── descriptor_cols — aggregated per timeline rule ────────────────────
    for col, cfg in descriptor_cols.items():
        if col not in eps_data.columns:
            continue
        if cfg.timeline == "none":
            continue

        out = eps_descriptor_col(identity, col)

        if cfg.timeline == "sequence":
            pipe_col = (
                eps_sorted.groupby(entity_col)[col]
                .apply(lambda s: " | ".join(
                    str(v) for v in s if pd.notna(v)
                ))
                .rename(out)
            )
            result = result.merge(pipe_col, on=entity_col, how="left")

        elif cfg.timeline == "unique":
            pipe_col = (
                eps_sorted.groupby(entity_col)[col]
                .apply(lambda s: " | ".join(
                    sorted(set(
                        str(v).strip()
                        for v in s
                        if pd.notna(v) and str(v).strip()
                    ))
                ))
                .rename(out)
            )
            result = result.merge(pipe_col, on=entity_col, how="left")

        elif cfg.timeline == "average":
            import numpy as np
            avg_col = (
                eps_sorted.groupby(entity_col)[col]
                .apply(lambda s: float(np.mean(
                    [float(v) for v in s if pd.notna(v)]
                )) if s.notna().any() else float("nan"))
                .rename(out)
            )
            result = result.merge(avg_col, on=entity_col, how="left")

    return result


def attach_event_columns(
    result:     pd.DataFrame,
    occ:        object,
    entity_col: str,
) -> pd.DataFrame:
    """
    Pipe-delimit event dates and descriptor columns for one
    Events object and merge into result.

    Produces:
      evt_{identity}              — pipe-delimited dates (always)
      evt_{identity}_{col}        — pipe-delimited also_defined_by columns
      evt_{identity}_{col}        — aggregated descriptor columns
                                    per DescriptorColConfig.timeline:
                                    "sequence" — pipe-delimit in visit order
                                    "unique"   — unique values, sorted
                                    "average"  — mean across visits (numeric)
                                    "none"     — not carried
    """
    identity  = occ.semantics.identity
    date_col  = occ.semantics.date_col
    out_col   = evt_col(identity)

    also_defined_by = occ.semantics.also_defined_by or []
    descriptor_cols = occ.semantics.descriptor_cols or {}

    evt_data = occ.data.copy()
    evt_data[date_col] = pd.to_datetime(evt_data[date_col]).dt.normalize()
    evt_sorted = evt_data.sort_values([entity_col, date_col])

    # ── Dates ────────────────────────────────────────────────────────────
    pipe_dates = (
        evt_sorted.groupby(entity_col)[date_col]
        .apply(lambda s: " | ".join(d.strftime("%Y-%m-%d") for d in s))
        .rename(out_col)
    )
    result = result.merge(pipe_dates, on=entity_col, how="left")

    # ── also_defined_by columns — always sequence, always atomic ─────────
    for col in also_defined_by:
        if col not in evt_data.columns:
            continue
        out = evt_descriptor_col(identity, col)
        pipe_col = (
            evt_sorted.groupby(entity_col)[col]
            .apply(lambda s: " | ".join(str(v) for v in s))
            .rename(out)
        )
        result = result.merge(pipe_col, on=entity_col, how="left")

    # ── descriptor_cols — aggregated per timeline rule ────────────────────
    for col, cfg in descriptor_cols.items():
        if col not in evt_data.columns:
            continue
        if cfg.timeline == "none":
            continue

        out = evt_descriptor_col(identity, col)

        if cfg.timeline == "sequence":
            pipe_col = (
                evt_sorted.groupby(entity_col)[col]
                .apply(lambda s: " | ".join(
                    str(v) for v in s if pd.notna(v)
                ))
                .rename(out)
            )
            result = result.merge(pipe_col, on=entity_col, how="left")

        elif cfg.timeline == "unique":
            pipe_col = (
                evt_sorted.groupby(entity_col)[col]
                .apply(lambda s: " | ".join(
                    sorted(set(
                        str(v).strip()
                        for v in s
                        if pd.notna(v) and str(v).strip()
                    ))
                ))
                .rename(out)
            )
            result = result.merge(pipe_col, on=entity_col, how="left")

        elif cfg.timeline == "average":
            import numpy as np
            avg_col = (
                evt_sorted.groupby(entity_col)[col]
                .apply(lambda s: float(np.mean(
                    [float(v) for v in s if pd.notna(v)]
                )) if s.notna().any() else float("nan"))
                .rename(out)
            )
            result = result.merge(avg_col, on=entity_col, how="left")

    return result


def attach_evt_comp_columns(
    data:       pd.DataFrame,
    stats_df:   pd.DataFrame,
    identity:   str,
) -> pd.DataFrame:
    """
    Attach computed event stat columns (evt_comp_{identity}_{stat})
    to data. Overwrites any existing columns with the same names.
    """
    result = data.copy()
    for stat_col in stats_df.columns:
        result[evt_comp_col(identity, stat_col)] = stats_df[stat_col].values
    return result


def validate_components(
    obs_period:  object,
    episodes_list: list,
    evt_list:    list,
) -> None:
    """
    Type, identity, and name checks on raw components before assembly.
    """
    from eventus.data_objects.episodes import Episodes
    from eventus.data_objects.events import Events
    from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

    if obs_period is not None and not isinstance(obs_period, ObsPeriodPerEntity):
        raise TypeError(
            f"{_ERROR} obs_period must be an ObsPeriodPerEntity object, "
            f"got {type(obs_period).__name__}"
        )
    for i, evt in enumerate(episodes_list):
        if not isinstance(evt, Episodes):
            raise TypeError(
                f"{_ERROR} episodes[{i}] must be an Episodes object, "
                f"got {type(evt).__name__}"
            )
        if not evt.semantics.identity:
            raise ValueError(
                f"{_ERROR} episodes[{i}] has no identity. "
                f"Set identity in EpisodeSemantics."
            )
    for i, o in enumerate(evt_list):
        if not isinstance(o, Events):
            raise TypeError(
                f"{_ERROR} events[{i}] must be an Events object, "
                f"got {type(o).__name__}"
            )
        if not o.semantics.identity:
            raise ValueError(
                f"{_ERROR} events[{i}] has no identity. "
                f"Set identity in EventSemantics."
            )
        validate_identity_name(o.semantics.identity)


def resolve_entity_col(obs_period, episodes_list: list, evt_list: list) -> str:
    if obs_period is not None:
        return obs_period.semantics.entity_id_col
    if episodes_list:
        return episodes_list[0].semantics.entity_id_col
    return evt_list[0].semantics.entity_id_col


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
