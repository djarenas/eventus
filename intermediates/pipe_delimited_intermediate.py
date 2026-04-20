"""
pipe_delimited_intermediate.py
Base class for pipe-delimited intermediate DataFrames.
Universal handshake format between analysis classes and visualization classes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd

_ERROR_PREFIX = "[PipeDelimitedIntermediate] Error"

# Fixed column names
ENTITY_ID_COL    = "entity_id"
SPAN_START_COL   = "span_start"
SPAN_END_COL     = "span_end"
EVENT_STARTS_COL = "event_starts"
EVENT_ENDS_COL   = "event_ends"

_SPAN_PAIR   = {SPAN_START_COL, SPAN_END_COL}
_EVENT_PAIR  = {EVENT_STARTS_COL, EVENT_ENDS_COL}


class PipeDelimitedIntermediate:
    """
    A validated DataFrame wrapper that serves as the universal handshake
    format between analysis classes and visualization classes.

    One row per entity. All multi-value columns are pipe-delimited strings.

    Required columns:
        entity_id

    Optional paired columns (must have both or neither):
        span_start + span_end
        event_starts + event_ends

    Optional occurrence columns (any number):
        Any column prefixed with 'occ_' is treated as an occurrence column.
        Named by occurrence identity with spaces replaced by underscores,
        e.g. 'occ_hepatitis_b_vaccination'.
        Values are pipe-delimited date strings.

    Attributes
    ----------
    data : pd.DataFrame
        The validated intermediate DataFrame.
    entity_col : str
        Name of the entity identifier column (always 'entity_id').
    """

    def __init__(self, data: pd.DataFrame, entity_col: str = ENTITY_ID_COL) -> None:
        self._validate(data, entity_col)
        self.data       = data.reset_index(drop=True)
        self.entity_col = entity_col

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(data: pd.DataFrame, entity_col: str) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{_ERROR_PREFIX}: data must be a DataFrame, "
                f"got {type(data).__name__}"
            )
        if entity_col not in data.columns:
            raise ValueError(
                f"{_ERROR_PREFIX}: entity column '{entity_col}' not found in data"
            )
        if data[entity_col].isna().any():
            raise ValueError(
                f"{_ERROR_PREFIX}: entity column '{entity_col}' contains null values"
            )
        # Validate optional pairs
        cols = set(data.columns)
        for pair_name, pair in [("span", _SPAN_PAIR), ("event", _EVENT_PAIR)]:
            present = pair & cols
            if len(present) == 1:
                missing = pair - present
                raise ValueError(
                    f"{_ERROR_PREFIX}: '{list(present)[0]}' is present but "
                    f"'{list(missing)[0]}' is missing — "
                    f"{pair_name} columns must appear together"
                )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def has_spans(self) -> bool:
        return SPAN_START_COL in self.data.columns

    @property
    def has_events(self) -> bool:
        return EVENT_STARTS_COL in self.data.columns

    # Suffixes added by self_analyze() — not raw pipe-delimited columns
    _DERIVED_SUFFIXES = {
        "_n", "_first", "_last", "_time_to_first", "_recency_days",
        "_mean_gap", "_std_gap", "_cv_gap", "_min_gap", "_max_gap",
        "_burstiness", "_memory", "_density",
    }

    @property
    def occurrence_cols(self) -> list[str]:
        """
        Raw pipe-delimited occ_ columns only.
        Excludes derived stat columns added by self_analyze()
        e.g. occ_ed_visit_n, occ_ed_visit_burstiness.
        """
        return [
            c for c in self.data.columns
            if c.startswith("occ_")
            and not any(c.endswith(s) for s in self._DERIVED_SUFFIXES)
        ]

    @property
    def occurrence_identities(self) -> list[str]:
        """Returns occurrence identities from raw occ_ column names."""
        return [c[4:] for c in self.occurrence_cols]

    # ------------------------------------------------------------------ #
    # Class methods
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        entity_col: str = ENTITY_ID_COL,
    ) -> "PipeDelimitedIntermediate":
        """
        Build a PipeDelimitedIntermediate from an existing DataFrame.

        Parameters
        ----------
        data : pd.DataFrame
            Must contain at minimum the entity column.
        entity_col : str
            Name of the entity identifier column. Default 'entity_id'.
        """
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def identity_to_col(identity: str) -> str:
        """Convert an occurrence identity string to a column name."""
        return "occ_" + identity.lower().replace(" ", "_")

    @staticmethod
    def col_to_identity(col: str) -> str:
        """Convert an occurrence column name back to an identity string."""
        return col[4:].replace("_", " ")

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def self_validate(self) -> "pd.DataFrame":
        """
        Validate the content of all pipe-delimited date columns.

        Checks that all date strings are parseable, that paired columns
        have matching token counts, and that span_start <= span_end.

        Returns
        -------
        pd.DataFrame
            Rows that failed validation with a '_validation_reason' column.
            Empty DataFrame if all rows are valid.
        """
        from pipe_delimited_utils import validate_content
        return validate_content(self.data, self.entity_col)

    @classmethod
    def combine(cls, *intermediates) -> "PipeDelimitedIntermediate":
        """
        Combine two or more PipeDelimitedIntermediate objects into one.

        All intermediates must share the same entity_col and the same
        set of entities. Columns from each intermediate are merged — if
        a column exists in multiple intermediates the last one wins.

        Parameters
        ----------
        *intermediates : PipeDelimitedIntermediate
            Two or more intermediate objects to combine.

        Returns
        -------
        PipeDelimitedIntermediate
            A new base-class intermediate with all columns merged.

        Raises
        ------
        ValueError
            If entity_col values differ or entity sets differ.
        """
        if len(intermediates) < 2:
            raise ValueError(
                "[PipeDelimitedIntermediate] combine() requires at least 2 intermediates"
            )

        # Validate all inputs are PipeDelimitedIntermediate or subclasses
        for i, obj in enumerate(intermediates):
            if not isinstance(obj, PipeDelimitedIntermediate):
                raise TypeError(
                    f"[PipeDelimitedIntermediate] combine(): intermediates[{i}] "
                    f"must be a PipeDelimitedIntermediate or subclass, "
                    f"got {type(obj).__name__}"
                )

        entity_col = intermediates[0].entity_col
        for i, obj in enumerate(intermediates[1:], 1):
            if obj.entity_col != entity_col:
                raise ValueError(
                    f"[PipeDelimitedIntermediate] combine(): entity_col mismatch — "
                    f"intermediates[0] has '{entity_col}', "
                    f"intermediates[{i}] has '{obj.entity_col}'"
                )

        # Validate entity sets match
        base_entities = set(intermediates[0].data[entity_col])
        for i, obj in enumerate(intermediates[1:], 1):
            other_entities = set(obj.data[entity_col])
            only_in_base  = base_entities - other_entities
            only_in_other = other_entities - base_entities
            if only_in_base or only_in_other:
                raise ValueError(
                    f"[PipeDelimitedIntermediate] combine(): entity sets do not match. "
                    f"intermediates[0] has {len(only_in_base)} entities not in "
                    f"intermediates[{i}], and intermediates[{i}] has "
                    f"{len(only_in_other)} entities not in intermediates[0]. "
                    f"Make sure both analyzers used the same ObsPeriodPerEntity."
                )

        # Validate span boundaries match across all intermediates
        base = intermediates[0].data
        if SPAN_START_COL in base.columns and SPAN_END_COL in base.columns:
            for i, obj in enumerate(intermediates[1:], 1):
                if SPAN_START_COL not in obj.data.columns:
                    continue
                # Align on entity_col and compare span boundaries
                merged = base[[entity_col, SPAN_START_COL, SPAN_END_COL]].merge(
                    obj.data[[entity_col, SPAN_START_COL, SPAN_END_COL]],
                    on=entity_col,
                    suffixes=("_a", "_b"),
                )
                start_mismatch = (
                    pd.to_datetime(merged[f"{SPAN_START_COL}_a"]) !=
                    pd.to_datetime(merged[f"{SPAN_START_COL}_b"])
                )
                end_mismatch = (
                    pd.to_datetime(merged[f"{SPAN_END_COL}_a"]) !=
                    pd.to_datetime(merged[f"{SPAN_END_COL}_b"])
                )
                bad = merged[start_mismatch | end_mismatch]
                if not bad.empty:
                    examples = bad[entity_col].head(3).tolist()
                    raise ValueError(
                        f"[PipeDelimitedIntermediate] combine(): span boundaries "
                        f"do not match between intermediates[0] and "
                        f"intermediates[{i}] for {len(bad)} entities. "
                        f"Example entity IDs: {examples}. "
                        f"Make sure both analyzers used the same ObsPeriodPerEntity."
                    )

        # Start with first intermediate's data, merge rest in
        combined = intermediates[0].data.copy()
        for obj in intermediates[1:]:
            new_cols = [c for c in obj.data.columns if c != entity_col]
            combined = combined.merge(
                obj.data[[entity_col] + new_cols],
                on=entity_col,
                how="outer",
                suffixes=("", "_dup"),
            )
            # Drop any duplicate columns
            dup_cols = [c for c in combined.columns if c.endswith("_dup")]
            combined = combined.drop(columns=dup_cols)

        return cls(combined, entity_col)


    @classmethod
    def from_objects(
        cls,
        obs_period,
        events      = None,
        occurrences = None,
    ) -> "PipeDelimitedIntermediate":
        """
        Build a PipeDelimitedIntermediate directly from data objects.

        Runs the appropriate analyzers internally and combines the
        results. At least one of events or occurrences must be provided.

        Parameters
        ----------
        obs_period : ObsPeriodPerEntity
            The observation window for each entity. Required.
        events : Events | None
            A validated Events object. If provided, runs
            EventsWithinObsPeriodsAnalyzer.compute_event_coverage().
        occurrences : Occurrences | list[Occurrences] | None
            One or more validated Occurrences objects. If provided,
            runs OccurrencesWithinObsPeriodsAnalyzer.calc().
            Each must have an identity set.

        Returns
        -------
        PipeDelimitedIntermediate
            Combined intermediate ready for visualization.

        Examples
        --------
        >>> intermediate = PipeDelimitedIntermediate.from_objects(
        ...     obs_period  = obs,
        ...     events      = events,
        ...     occurrences = [ed_visits, vaccinations],
        ... )
        >>> StackedTimelinePlotter(intermediate, config).plot("out.png")
        """
        from data_objects.obs_period_per_entity import ObsPeriodPerEntity
        from data_objects.events import Events
        from data_objects.occurrences import Occurrences
        from analyzers.events_within_obs_periods_analyzer import (
            EventsWithinObsPeriodsAnalyzer
        )
        from analyzers.occurrences_within_obs_periods_analyzer import (
            OccurrencesWithinObsPeriodsAnalyzer
        )

        _ERR = "[PipeDelimitedIntermediate.from_objects] Error"

        # ── Validate obs_period ───────────────────────────────────────
        if not isinstance(obs_period, ObsPeriodPerEntity):
            raise TypeError(
                f"{_ERR}: obs_period must be an ObsPeriodPerEntity "
                f"object, got {type(obs_period).__name__}. "
                f"Use ObsPeriodPerEntity.from_calendar(), "
                f".from_age_window(), or .from_events() to build one."
            )

        # ── Validate events ───────────────────────────────────────────
        if events is not None and not isinstance(events, Events):
            raise TypeError(
                f"{_ERR}: events must be an Events object or None, "
                f"got {type(events).__name__}"
            )

        # ── Validate occurrences ──────────────────────────────────────
        if occurrences is not None:
            if isinstance(occurrences, Occurrences):
                occurrences = [occurrences]
            if not isinstance(occurrences, list) or not occurrences:
                raise TypeError(
                    f"{_ERR}: occurrences must be an Occurrences object, "
                    f"a non-empty list of Occurrences objects, or None"
                )
            for i, occ in enumerate(occurrences):
                if not isinstance(occ, Occurrences):
                    raise TypeError(
                        f"{_ERR}: occurrences[{i}] must be an Occurrences "
                        f"object, got {type(occ).__name__}"
                    )
                if not occ.semantics.identity:
                    raise ValueError(
                        f"{_ERR}: occurrences[{i}] has no identity set. "
                        f"Set identity in OccurrenceSemantics "
                        f"e.g. identity='ed_visit'"
                    )

        # ── At least one input required ───────────────────────────────
        if events is None and not occurrences:
            raise ValueError(
                f"{_ERR}: at least one of events or occurrences must "
                f"be provided."
            )

        # ── Validate entity_col consistency ───────────────────────────
        obs_entity_col = obs_period.semantics.entity_id_col
        if events is not None:
            if events.semantics.entity_id_col != obs_entity_col:
                raise ValueError(
                    f"{_ERR}: events.entity_id_col "
                    f"'{events.semantics.entity_id_col}' does not match "
                    f"obs_period.entity_id_col '{obs_entity_col}'"
                )
        if occurrences:
            for i, occ in enumerate(occurrences):
                if occ.semantics.entity_id_col != obs_entity_col:
                    raise ValueError(
                        f"{_ERR}: occurrences[{i}] "
                        f"(identity='{occ.semantics.identity}') "
                        f"entity_id_col '{occ.semantics.entity_id_col}' "
                        f"does not match obs_period.entity_id_col "
                        f"'{obs_entity_col}'"
                    )

        # ── Run analyzers ─────────────────────────────────────────────
        results = []

        if events is not None:
            results.append(
                EventsWithinObsPeriodsAnalyzer(events, obs_period)
                .compute_event_coverage()
            )

        if occurrences:
            results.append(
                OccurrencesWithinObsPeriodsAnalyzer(occurrences, obs_period)
                .calc()
            )

        # ── Combine ───────────────────────────────────────────────────
        if len(results) == 1:
            return results[0]

        return cls.combine(*results)

    def copy(self) -> "PipeDelimitedIntermediate":
        """Return a copy of this PipeDelimitedIntermediate."""
        return self.__class__(self.data.copy(), self.entity_col)

    def sample(self, n:int, random_state: int) -> "PipeDelimitedIntermediate":
        """Return a subset of the data as a PipeDelimitedIntermediate object"""
        if not isinstance(n, int):
            raise TypeError(f"{_ERROR_PREFIX} in sample(): n must be an integer, got {type(n)}")
        if n <= 0:
            raise ValueError(f"{_ERROR_PREFIX} in sample(): n must be greater than 0, got {n}")
        if not isinstance(random_state, int):
             raise TypeError(f"{_ERROR_PREFIX} in sample(): random_state must be an integer, got {type(n)}")
        data = self.data.copy().sample(n=n, random_state=random_state)
        return self.__class__(data, self.entity_col)

    def to_csv(self, path: str) -> None:
        """Save the intermediate DataFrame to CSV."""
        self.data.to_csv(path, index=False)
        print(f"Saved: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        parts = [f"PipeDelimitedIntermediate({len(self)} entities"]
        if self.has_spans:
            parts.append("spans=yes")
        if self.has_events:
            parts.append("events=yes")
        if self.occurrence_cols:
            parts.append(f"occurrences={self.occurrence_identities}")
        return ", ".join(parts) + ")"
