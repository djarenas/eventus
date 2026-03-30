"""
occurrences_within_spans_analyzer.py
Analyzes occurrences within per-entity span windows.
Produces PipeDelimitedIntermediateOccurrences.
"""
from __future__ import annotations
import pandas as pd
from .validation_utils import validate_shared_entity_col

_ERROR_PREFIX = "[OccurrencesWithinSpansAnalyzer] Error"


class OccurrencesWithinSpansAnalyzer:
    """
    Filters occurrences to within each entity's span window and produces
    a PipeDelimitedIntermediateOccurrences with one row per entity.

    Multiple Occurrences objects can be passed — each gets its own
    occ_{identity} column in the result.

    Parameters
    ----------
    occurrences : Occurrences or list[Occurrences]
        One or more Occurrences objects. Each must have an identity set
        on its semantics.
    spans : EventsPerEntity
        One row per entity defining span_start and span_end.
    entity_col : str | None
        Entity identifier column. Defaults to spans.semantics.entity_id_col.
    """

    def __init__(
        self,
        occurrences,
        spans,
        entity_col: str | None = None,
    ) -> None:
        from .occurrences import Occurrences
        from .events_per_entity import EventsPerEntity

        # --- Normalize occurrences to list ---
        if isinstance(occurrences, Occurrences):
            occurrences = [occurrences]
        if not isinstance(occurrences, list) or not occurrences:
            raise TypeError(
                f"{_ERROR_PREFIX}: occurrences must be an Occurrences object "
                f"or a non-empty list of Occurrences objects"
            )
        for i, occ in enumerate(occurrences):
            if not isinstance(occ, Occurrences):
                raise TypeError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] must be an Occurrences object"
                )
            if not occ.semantics.identity:
                raise ValueError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] has no identity set. "
                    f"Set identity in OccurrenceSemantics."
                )

        # --- Validate spans ---
        if not isinstance(spans, EventsPerEntity):
            raise TypeError(
                f"{_ERROR_PREFIX}: spans must be an EventsPerEntity object"
            )

        # --- Resolve entity_col ---
        if entity_col is None:
            entity_col = spans.semantics.entity_id_col

        # --- Validate shared entity_col ---
        for i, occ in enumerate(occurrences):
            if occ.semantics.entity_id_col != entity_col:
                raise ValueError(
                    f"{_ERROR_PREFIX}: occurrences[{i}] (identity='{occ.semantics.identity}') "
                    f"has entity_id_col '{occ.semantics.entity_id_col}' "
                    f"but expected '{entity_col}'"
                )

        # --- Check for duplicate identities ---
        identities = [occ.semantics.identity for occ in occurrences]
        if len(identities) != len(set(identities)):
            dupes = [i for i in identities if identities.count(i) > 1]
            raise ValueError(
                f"{_ERROR_PREFIX}: duplicate occurrence identities: {list(set(dupes))}"
            )

        self._occurrences  = occurrences
        self._spans        = spans
        self._entity_col   = entity_col

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def calc(self):
        """
        Filter occurrences to within each entity's span and return
        a PipeDelimitedIntermediateOccurrences.

        Returns
        -------
        PipeDelimitedIntermediateOccurrences
            One row per entity. Each occurrence type gets its own
            occ_{identity} column with pipe-delimited dates within span.
            Entities with no occurrences in span get NA for that column.
        """
        from .pipe_delimited_intermediate_occurrences import (
            PipeDelimitedIntermediateOccurrences
        )
        from .pipe_delimited_intermediate import (
            SPAN_START_COL, SPAN_END_COL
        )

        entity_col     = self._entity_col
        span_start_col = self._spans.semantics.start_time_col
        span_end_col   = self._spans.semantics.end_time_col

        # Start from spans — one row per entity
        result = self._spans.data[[
            entity_col, span_start_col, span_end_col
        ]].copy().rename(columns={
            span_start_col: SPAN_START_COL,
            span_end_col:   SPAN_END_COL,
        })

        result[SPAN_START_COL] = pd.to_datetime(result[SPAN_START_COL]).dt.normalize()
        result[SPAN_END_COL]   = pd.to_datetime(result[SPAN_END_COL]).dt.normalize()
        result["span_duration_days"] = (
            result[SPAN_END_COL] - result[SPAN_START_COL]
        ).dt.days.astype(float)

        # Build span lookup for fast filtering
        span_lookup = result.set_index(entity_col)[[SPAN_START_COL, SPAN_END_COL]]

        # Add one occ_* column per occurrence type
        for occ in self._occurrences:
            identity = occ.semantics.identity
            date_col = occ.semantics.date_col
            occ_col  = f"occ_{identity.lower().replace(' ', '_')}"

            occ_data = occ.data.copy()
            occ_data[date_col] = pd.to_datetime(occ_data[date_col]).dt.normalize()

            # Join span boundaries onto occurrences
            occ_merged = occ_data.merge(
                span_lookup.rename(columns={
                    SPAN_START_COL: "_span_start",
                    SPAN_END_COL:   "_span_end",
                }),
                left_on=entity_col,
                right_index=True,
                how="inner",
            )

            # Filter to within span
            in_span = occ_merged[
                (occ_merged[date_col] >= occ_merged["_span_start"]) &
                (occ_merged[date_col] <= occ_merged["_span_end"])
            ].copy()

            # Pipe-join dates per entity
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
                result = result.merge(
                    pipe_col, on=entity_col, how="left"
                )
            else:
                result[occ_col] = pd.NA

        return PipeDelimitedIntermediateOccurrences(
            result.reset_index(drop=True),
            entity_col,
        )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        ids = [occ.semantics.identity for occ in self._occurrences]
        return (
            f"OccurrencesWithinSpansAnalyzer(\n"
            f"  identities : {ids}\n"
            f"  entity_col : '{self._entity_col}'\n"
            f"  n_spans    : {len(self._spans)}\n"
            f")"
        )
