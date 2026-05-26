"""
episode_duration_analyzer.py
EpisodeDurationAnalyzer — computes episode durations from a validated
Episodes object and produces an EpisodeDurationResult.
"""
from __future__ import annotations
import pandas as pd

from eventus.data_objects.episodes import Episodes

_ERROR_PREFIX = "[EpisodeDurationAnalyzer] Error"


class EpisodeDurationAnalyzer:
    """
    Computes episode durations from a validated Episodes object.

    Each row in the result represents one episode with its duration in days.
    Optional descriptor columns from Episodes.data are carried through to
    the result — these may have nulls, which is by design.

    Parameters
    ----------
    episodes : Episodes
        A validated Episodes object. Must be structurally sound —
        use EpisodesCleaner first if your data is messy.
    descriptor_cols : list[str] | str | None
        Columns in episodes.data to carry through to the result as
        per-episode descriptors (e.g. "bmi_at_admission", "hospital_id").
        Pass "all" to carry every column beyond the required three.
        Pass a list to be explicit. Default None — lean output only.
        Nulls in descriptor columns are allowed.

    Examples
    --------
    >>> # Plain durations — lean output
    >>> analyzer = EpisodeDurationAnalyzer(episodes)
    >>> result   = analyzer.calc()

    >>> # With descriptors — explicit
    >>> analyzer = EpisodeDurationAnalyzer(
    ...     episodes,
    ...     descriptor_cols=["bmi_at_admission", "hospital_id"],
    ... )
    >>> result = analyzer.calc()

    >>> # With descriptors — carry everything
    >>> analyzer = EpisodeDurationAnalyzer(episodes, descriptor_cols="all")
    >>> result   = analyzer.calc()
    """

    def __init__(
        self,
        episodes:          Episodes,
        descriptor_cols: list[str] | str | None = None,
    ) -> None:
        if not isinstance(episodes, Episodes):
            raise TypeError(
                f"{_ERROR_PREFIX}: episodes must be an Episodes object, "
                f"got {type(episodes).__name__}"
            )

        # ── Resolve descriptor_cols ───────────────────────────────────
        resolved = self._resolve_descriptor_cols(
            descriptor_cols, episodes
        )

        self._episodes          = episodes
        self._descriptor_cols = resolved
        self._result          = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def calc(self) -> "EpisodeDurationResult":
        """
        Compute durations and return an EpisodeDurationResult.

        Returns
        -------
        EpisodeDurationResult
            One row per episode. Always contains entity_col and
            duration_days. Contains descriptor columns if specified.
        """
        from eventus.intermediates.episode_duration_result import EpisodeDurationResult
        from .episodes_duration_utils import compute_durations

        df = compute_durations(
            data            = self._episodes.data,
            entity_col      = self._episodes.semantics.entity_id_col,
            start_col       = self._episodes.semantics.start_time_col,
            end_col         = self._episodes.semantics.end_time_col,
            identity        = self._episodes.semantics.identity,
            descriptor_cols = self._descriptor_cols,
        )

        self._result = EpisodeDurationResult(
            data            = df,
            entity_col      = self._episodes.semantics.entity_id_col,
            identity        = self._episodes.semantics.identity,
            descriptor_cols = self._descriptor_cols,
        )
        return self._result

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _resolve_descriptor_cols(
        self,
        descriptor_cols: list[str] | str | None,
        episodes:          Episodes,
    ) -> list[str]:
        """
        Resolve descriptor_cols to a validated list of column names.

        "all"  → every column in episodes.data beyond the required three
        list   → validated explicitly against episodes.data
        None   → empty list
        """
        core_cols = {
            episodes.semantics.entity_id_col,
            episodes.semantics.start_time_col,
            episodes.semantics.end_time_col,
        }

        if descriptor_cols is None:
            return []

        if descriptor_cols == "all":
            return [
                c for c in episodes.data.columns
                if c not in core_cols
            ]

        if isinstance(descriptor_cols, str):
            # single string that isn't "all"
            descriptor_cols = [descriptor_cols]

        if not isinstance(descriptor_cols, list):
            raise TypeError(
                f"{_ERROR_PREFIX}: descriptor_cols must be a list, "
                f"'all', or None, got {type(descriptor_cols).__name__}"
            )

        # Validate all specified columns exist
        missing = [
            c for c in descriptor_cols
            if c not in episodes.data.columns
        ]
        if missing:
            raise ValueError(
                f"{_ERROR_PREFIX}: descriptor_cols not found in "
                f"Episodes.data: {missing}. "
                f"Available columns: {sorted(episodes.data.columns.tolist())}"
            )

        # Warn if any core columns were accidentally included
        overlap = [c for c in descriptor_cols if c in core_cols]
        if overlap:
            import warnings
            warnings.warn(
                f"[EpisodeDurationAnalyzer] descriptor_cols includes core "
                f"column(s) {overlap} — they will be ignored since they "
                f"are already present in the result.",
                UserWarning,
                stacklevel=3,
            )
            descriptor_cols = [c for c in descriptor_cols if c not in core_cols]

        return list(descriptor_cols)

    def _require_calc(self, method_name: str) -> None:
        if self._result is None:
            raise ValueError(
                f"{_ERROR_PREFIX}: .{method_name}() requires calling "
                f".calc() first."
            )

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        sid    = self._episodes.semantics.identity
        status = "calculated" if self._result is not None else "not yet calculated"
        desc   = self._descriptor_cols if self._descriptor_cols else "none"
        return (
            f"EpisodeDurationAnalyzer(\n"
            f"  identity        : {sid!r}\n"
            f"  episodes          : {len(self._episodes):,} rows\n"
            f"  descriptor_cols : {desc}\n"
            f"  status          : {status}\n"
            f")"
        )
