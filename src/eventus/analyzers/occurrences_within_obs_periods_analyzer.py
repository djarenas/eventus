"""
occurrences_within_obs_periods_analyzer.py
OccurrencesWithinObsPeriodsAnalyzer — filters occurrences to within
each entity's observation period and produces a
PipeDelimitedFormatOccurrences.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[OccurrencesWithinObsPeriodsAnalyzer] Error"


class OccurrencesWithinObsPeriodsAnalyzer:
    """
    Filters occurrences to within each entity's observation period.

    Accepts one or more Occurrences objects. Each produces its own
    pipe-delimited column in the output pipe_delimited_format, named
    occ_{identity} — for example occ_ed_visit or occ_hepatitis_b.

    Parameters
    ----------
    occurrences : Occurrences or list[Occurrences]
        One or more validated Occurrences objects. Each must have an
        identity set on its OccurrenceSemantics.
    obs_period : ObsPeriodPerEntity
        One row per entity defining their observation window.
    entity_col : str | None
        Entity identifier column. Defaults to
        obs_period.semantics.entity_id_col.

    Examples
    --------
    >>> result = OccurrencesWithinObsPeriodsAnalyzer(
    ...     occurrences = ed_visits,
    ...     obs_period  = obs,
    ... ).calc()

    >>> # Multiple occurrence types
    >>> result = OccurrencesWithinObsPeriodsAnalyzer(
    ...     occurrences = [ed_visits, vaccinations],
    ...     obs_period  = obs,
    ... ).calc()
    """

    def __init__(
        self,
        occurrences,
        obs_period,
        entity_col: str | None = None,
    ) -> None:
        from eventus.data_objects.occurrences import Occurrences
        from eventus.data_objects.obs_period_per_entity import ObsPeriodPerEntity

        # Normalize to list
        if isinstance(occurrences, Occurrences):
            occurrences = [occurrences]
        if not isinstance(occurrences, list) or not occurrences:
            raise TypeError(
                f"{_ERROR_PREFIX}: occurrences must be an Occurrences "
                f"object or a non-empty list of Occurrences objects"
            )

        # Validate each occurrences object
        for i, occ in enumerate(occurrences):
            if not isinstance(occ, Occurrences):
                raise TypeError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] must be an "
                    f"Occurrences object, got {type(occ).__name__}"
                )
            if not occ.semantics.identity:
                raise ValueError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] has no identity. "
                    f"Set identity in OccurrenceSemantics "
                    f"e.g. identity='ed_visit'"
                )

        # Validate obs_period
        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERROR_PREFIX}: obs_period must be an "
                f"ObsPeriodPerEntity object, "
                f"got {type(obs_period).__name__}. "
                f"Use ObsPeriodPerEntity.from_calendar(), "
                f".from_age_window(), or .from_events() to build one."
            )

        # Resolve entity_col
        if entity_col is None:
            entity_col = obs_period.semantics.entity_id_col

        # Validate entity_col matches across all occurrences
        for i, occ in enumerate(occurrences):
            if occ.semantics.entity_id_col != entity_col:
                raise ValueError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] "
                    f"(identity='{occ.semantics.identity}') "
                    f"has entity_id_col '{occ.semantics.entity_id_col}' "
                    f"but expected '{entity_col}'"
                )

        # Check for duplicate identities
        identities = [occ.semantics.identity for occ in occurrences]
        if len(identities) != len(set(identities)):
            dupes = list(set(i for i in identities if identities.count(i) > 1))
            raise ValueError(
                f"{_ERROR_PREFIX}: duplicate occurrence identities: {dupes}. "
                f"Each Occurrences object must have a unique identity."
            )

        self._occurrences = occurrences
        self._obs_period  = obs_period
        self._entity_col  = entity_col

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def calc(self):
        """
        Filter occurrences to within each entity's observation period.

        Returns
        -------
        PipeDelimitedFormatOccurrences
            One row per entity. Each occurrence type gets its own
            occ_{identity} column with pipe-delimited dates.
            Entities with no occurrences in period get NA.
        """
        from eventus.pipe_delimited_format.pipe_delimited_format_occurrences import (
            PipeDelimitedFormatOccurrences
        )
        from eventus.pipe_delimited_format.pipe_delimited_format import (
            SPAN_START_COL, SPAN_END_COL
        )

        entity_col     = self._entity_col
        span_start_col = self._obs_period.semantics.start_time_col
        span_end_col   = self._obs_period.semantics.end_time_col

        # Start from obs_period — one row per entity
        result = self._obs_period.data[[
            entity_col, span_start_col, span_end_col
        ]].copy().rename(columns={
            span_start_col: SPAN_START_COL,
            span_end_col:   SPAN_END_COL,
        })

        result[SPAN_START_COL] = (
            pd.to_datetime(result[SPAN_START_COL]).dt.normalize()
        )
        result[SPAN_END_COL] = (
            pd.to_datetime(result[SPAN_END_COL]).dt.normalize()
        )
        result["span_duration_days"] = (
            result[SPAN_END_COL] - result[SPAN_START_COL]
        ).dt.days.astype(float)

        span_lookup = result.set_index(entity_col)[
            [SPAN_START_COL, SPAN_END_COL]
        ]

        # Add one occ_{identity} column per occurrence type
        for occ in self._occurrences:
            identity = occ.semantics.identity
            date_col = occ.semantics.date_col
            occ_col  = f"occ_{identity}"   # identity already alphanumeric+underscore

            occ_data          = occ.data.copy()
            occ_data[date_col] = pd.to_datetime(
                occ_data[date_col]
            ).dt.normalize()

            # Join span boundaries onto occurrences
            occ_merged = occ_data.merge(
                span_lookup.rename(columns={
                    SPAN_START_COL: "_span_start",
                    SPAN_END_COL:   "_span_end",
                }),
                left_on     = entity_col,
                right_index = True,
                how         = "inner",
            )

            # Filter to within observation period
            in_span = occ_merged[
                (occ_merged[date_col] >= occ_merged["_span_start"]) &
                (occ_merged[date_col] <= occ_merged["_span_end"])
            ].copy()

            if not in_span.empty:
                pipe_col = (
                    in_span
                    .sort_values([entity_col, date_col])
                    .groupby(entity_col)[date_col]
                    .apply(lambda dates: " | ".join(
                        d.strftime("%Y-%m-%d") for d in dates
                    ))
                    .rename(occ_col)
                )
                result = result.merge(pipe_col, on=entity_col, how="left")
            else:
                result[occ_col] = pd.NA

        return PipeDelimitedFormatOccurrences(
            result.reset_index(drop=True),
            entity_col,
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        identities = [occ.semantics.identity for occ in self._occurrences]
        return (
            f"OccurrencesWithinObsPeriodsAnalyzer(\n"
            f"  occurrences : {identities}\n"
            f"  obs_period  : {len(self._obs_period):,} entities "
            f"(identity='{self._obs_period.identity}')\n"
            f"  entity_col  : '{self._entity_col}'\n"
            f")"
        )
