"""
pipe_delimited_intermediate_occurrences.py
Child of PipeDelimitedIntermediate for occurrence analysis results.
Produced by OccurrencesWithinSpansAnalyzer.calc().
"""
from __future__ import annotations
import pandas as pd
import yaml

from .pipe_delimited_intermediate import PipeDelimitedIntermediate

_ERROR_PREFIX = "[PipeDelimitedIntermediateOccurrences] Error"

_ANALYZED_SUFFIXES = (
    "_count", "_first", "_last", "_recency_days",
    "_mean_gap_days", "_std_gap_days", "_min_gap_days",
    "_max_gap_days", "_density", "_burstiness", "_cv",
)


class PipeDelimitedIntermediateOccurrences(PipeDelimitedIntermediate):
    """
    Result of OccurrencesWithinSpansAnalyzer.calc().
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
        """True if analysis columns have been computed for all occ_* columns."""
        base_occ = [c for c in self.data.columns
                    if c.startswith("occ_") and
                    not any(c.endswith(s) for s in _ANALYZED_SUFFIXES)]
        if not base_occ:
            return False
        return all(
            f"{col}_count" in self.data.columns
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

    def self_analyze(self) -> "PipeDelimitedIntermediateOccurrences":
        """
        Compute analysis columns for all occ_* columns.
        Returns a new enriched instance.

        Adds for each occ_{identity}:
        - occ_{identity}_count
        - occ_{identity}_first, occ_{identity}_last
        - occ_{identity}_recency_days
        - occ_{identity}_mean_gap_days, occ_{identity}_std_gap_days
        - occ_{identity}_min_gap_days, occ_{identity}_max_gap_days
        - occ_{identity}_density
        - occ_{identity}_burstiness
        - occ_{identity}_cv
        """
        from .pipe_delimited_intermediate_occurrences_utils import compute_occ_analysis
        enriched = compute_occ_analysis(self.data, self.entity_col)
        return PipeDelimitedIntermediateOccurrences(enriched, self.entity_col)

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
