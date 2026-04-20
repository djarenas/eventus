"""
pipe_delimited_intermediate_occurrences.py
Child of PipeDelimitedIntermediate for occurrence analysis results.
Produced by OccurrencesWithinObsPeriodsAnalyzer.calc().
"""
from __future__ import annotations
import pandas as pd
import yaml

from .pipe_delimited_intermediate import PipeDelimitedIntermediate

_ERROR_PREFIX = "[PipeDelimitedIntermediateOccurrences] Error"

_ANALYZED_SUFFIXES = (
    "_n", "_first", "_last", "_time_to_first", "_recency_days",
    "_mean_gap", "_std_gap", "_cv_gap", "_min_gap", "_max_gap",
    "_burstiness", "_memory", "_density",
)


class PipeDelimitedIntermediateOccurrences(PipeDelimitedIntermediate):
    """
    Result of OccurrencesWithinObsPeriodsAnalyzer.calc().
    Inherits from PipeDelimitedIntermediate.

    Holds one row per entity with:
    - span_start, span_end (optional but typical)
    - occ_{identity} columns — pipe-delimited occurrence dates within span
    - After self_analyze(): occ_{identity}_count, occ_{identity}_mean_gap_days,
      occ_{identity}_burstiness, etc. for each identity

    Multiple occurrence types are stored as separate occ_* columns.
    """

    def __init__(self, data: pd.DataFrame, entity_col: str = "entity_id") -> None:
        super().__init__(data, entity_col)
        self._validate_has_occ_cols()

    def _validate_has_occ_cols(self) -> None:
        base_occ = [c for c in self.data.columns
                    if c.startswith("occ_") and
                    not any(c.endswith(s) for s in _ANALYZED_SUFFIXES)]
        if not base_occ:
            raise ValueError(
                f"{_ERROR_PREFIX}: data must have at least one occ_* column "
                f"(pipe-delimited occurrence dates)"
            )

    # ------------------------------------------------------------------ #
    # Classmethod override
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataframe(
        cls,
        data: pd.DataFrame,
        entity_col: str = "entity_id",
    ) -> "PipeDelimitedIntermediateOccurrences":
        """Build from an existing DataFrame."""
        return cls(data, entity_col)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def is_analyzed(self) -> bool:
        """True if self_analyze() has been called (default stats present)."""
        base_occ = [c for c in self.data.columns
                    if c.startswith("occ_") and
                    not any(c.endswith(s) for s in _ANALYZED_SUFFIXES)]
        if not base_occ:
            return False
        return all(
            f"{col}_n" in self.data.columns
            for col in base_occ
        )

    @property
    def identities(self) -> list[str]:
        """List of occurrence identities in this intermediate."""
        return [
            c[4:] for c in self.data.columns
            if c.startswith("occ_") and
            not any(c.endswith(s) for s in _ANALYZED_SUFFIXES)
        ]

    def _require_analyzed(self, method_name: str) -> None:
        if not self.is_analyzed:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires analysis columns. "
                f"Call .self_analyze() first."
            )

    # ------------------------------------------------------------------ #
    # self_analyze
    # ------------------------------------------------------------------ #

    def self_analyze(
        self,
        extras = None,
    ) -> "PipeDelimitedIntermediateOccurrences":
        """
        Compute statistics for all occ_* columns.
        Returns a new enriched intermediate — original is unchanged.

        Default statistics (always computed):
            occ_{identity}_n              count of occurrences in period
            occ_{identity}_first          date of first occurrence
            occ_{identity}_last           date of last occurrence
            occ_{identity}_time_to_first  days from obs_start to first
            occ_{identity}_recency_days   days from last to obs_end

        Optional extras — pass as list or "all":
            "mean_gap"    mean inter-occurrence gap in days
            "std_gap"     std of inter-occurrence gaps
            "cv_gap"      coefficient of variation of gaps
            "min_gap"     shortest inter-occurrence gap
            "max_gap"     longest inter-occurrence gap
            "burstiness"  Goh-Barabasi B (requires >= 3 occurrences)
            "memory"      Goh-Barabasi M (requires >= 4 occurrences)
            "density"     occurrences per day in observation period

        Parameters
        ----------
        extras : list[str] | str | None
            Additional statistics to compute. Use "all" for everything.
            Default None computes only the default set.

        Returns
        -------
        PipeDelimitedIntermediateOccurrences
            New enriched intermediate.

        Examples
        --------
        >>> enriched = result.self_analyze()
        >>> enriched = result.self_analyze(extras=["burstiness", "memory"])
        >>> enriched = result.self_analyze(extras="all")
        """
        from .occurrences_self_analyze_utils import (
            validate_extras, analyze_occurrence_column
        )
        from .pipe_delimited_intermediate import SPAN_START_COL, SPAN_END_COL

        extras_list = validate_extras(extras)

        data = self.data.copy()
        obs_start = pd.to_datetime(data[SPAN_START_COL]).dt.normalize()
        obs_end   = pd.to_datetime(data[SPAN_END_COL]).dt.normalize()

        for occ_col in self.occurrence_cols:
            identity = occ_col[4:]   # strip "occ_"
            stats_df = analyze_occurrence_column(
                series    = data[occ_col],
                obs_start = obs_start,
                obs_end   = obs_end,
                extras    = extras_list,
            )
            # Add computed columns with identity prefix
            for stat_name in stats_df.columns:
                col_name = f"occ_{identity}_{stat_name}"
                data[col_name] = stats_df[stat_name].values

        return PipeDelimitedIntermediateOccurrences(data, self.entity_col)

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def full_summary(self, percentiles: list[int] = [25, 50, 75]) -> dict:
        """Full summary dict for all occurrence identities."""
        self._require_analyzed("full_summary")
        from .pipe_delimited_intermediate_occurrences_utils import calc_occ_summary
        return calc_occ_summary(self.data, self.entity_col, percentiles)

    def print_summary(self, percentiles: list[int] = [25, 50, 75]) -> None:
        """Print full summary as YAML to stdout."""
        print(yaml.dump(self.full_summary(percentiles),
                        sort_keys=False, allow_unicode=True))

    def save_summary(self, path: str, percentiles: list[int] = [25, 50, 75]) -> None:
        """Write full summary as YAML to file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.full_summary(percentiles), f,
                      sort_keys=False, allow_unicode=True)
        print(f"Summary saved to: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        analyzed = "analyzed" if self.is_analyzed else "not analyzed"
        return (
            f"PipeDelimitedIntermediateOccurrences(\n"
            f"  entities   : {len(self)}\n"
            f"  identities : {self.identities}\n"
            f"  status     : {analyzed}\n"
            f")"
        )
