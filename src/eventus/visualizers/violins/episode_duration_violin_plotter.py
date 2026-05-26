"""
episode_duration_violin_plotter.py
EpisodeDurationViolinPlotter — violin plot of episode durations from an
EpisodeDurationResult.

Delegates all drawing to ArraysViolinPlotter.
This class is responsible for:
  - validating the EpisodeDurationResult against stratify_by
  - calling result.build_arrays(stratify_by) to extract arrays
  - passing clean arrays + config to ArraysViolinPlotter
"""
from __future__ import annotations

from eventus.intermediates.episode_duration_result import EpisodeDurationResult
from eventus.visualizers.configs.arrays_violin_config import ArraysViolinConfig
from eventus.visualizers.violins.arrays_violin_plotter import ArraysViolinPlotter

_ERROR = "[EpisodeDurationViolinPlotter] Error"


class EpisodeDurationViolinPlotter:
    """
    Violin plot of episode durations from an EpisodeDurationResult.

    If stratify_by is None, one violin is drawn for the full cohort
    under the key 'all_data'.

    If stratify_by is set, one violin per unique category value is
    drawn, plus 'all_data' as the first violin. The stratify_by column
    must have been included in descriptor_cols when running
    EpisodeDurationAnalyzer.

    Drawing is handled entirely by ArraysViolinPlotter. Pass an
    ArraysViolinConfig to control colors, labels, bandwidth, percentile
    lines, and axis bounds.

    Parameters
    ----------
    result : EpisodeDurationResult
        Produced by EpisodeDurationAnalyzer.calc().
    config : ArraysViolinConfig | None
        Plot configuration. Uses ArraysViolinConfig() defaults if not
        provided.
    stratify_by : str | None
        Column name in result.data to stratify by. Must be present in
        result.descriptor_cols. Default None — one violin for all data.

    Raises
    ------
    TypeError
        If result or config are the wrong type.
    ValueError
        If stratify_by is set but not in result.descriptor_cols.
        If stratify_by is in descriptor_cols but not in result.data —
        this indicates a framework bug and should be reported.

    Examples
    --------
    >>> # No stratification
    >>> result  = EpisodeDurationAnalyzer(episodes).calc()
    >>> config  = ArraysViolinConfig()
    >>> plotter = EpisodeDurationViolinPlotter(result, config)
    >>> plotter.plot("durations.png")

    >>> # Stratified by hospital
    >>> result = EpisodeDurationAnalyzer(
    ...     episodes,
    ...     descriptor_cols=["hospital_id"],
    ... ).calc()
    >>> config  = ArraysViolinConfig.build_from_yaml("duration_violin.yaml")
    >>> plotter = EpisodeDurationViolinPlotter(result, config, stratify_by="hospital_id")
    >>> plotter.plot("durations_by_hospital.png")
    """

    def __init__(
        self,
        result:      EpisodeDurationResult,
        config:      ArraysViolinConfig | None = None,
        stratify_by: str | None                = None,
    ) -> None:

        # ── Type checks ───────────────────────────────────────────────
        if not isinstance(result, EpisodeDurationResult):
            raise TypeError(
                f"{_ERROR}: result must be an EpisodeDurationResult, "
                f"got {type(result).__name__}"
            )

        if config is None:
            config = ArraysViolinConfig()
        if not isinstance(config, ArraysViolinConfig):
            raise TypeError(
                f"{_ERROR}: config must be an ArraysViolinConfig, "
                f"got {type(config).__name__}"
            )

        if stratify_by is not None and (
            not isinstance(stratify_by, str) or not stratify_by.strip()
        ):
            raise TypeError(
                f"{_ERROR}: stratify_by must be a non-empty string or None, "
                f"got {stratify_by!r}"
            )

        # ── Validate stratify_by ──────────────────────────────────────
        if stratify_by is not None:

            # Case 1 — not in descriptor_cols: user error
            if stratify_by not in result.descriptor_cols:
                raise ValueError(
                    f"{_ERROR}: stratify_by='{stratify_by}' is not in "
                    f"EpisodeDurationResult.descriptor_cols "
                    f"{result.descriptor_cols}. "
                    f"Include '{stratify_by}' in descriptor_cols when "
                    f"running EpisodeDurationAnalyzer."
                )

            # Case 2 — in descriptor_cols but not in data: framework bug
            if stratify_by not in result.data.columns:
                raise ValueError(
                    f"{_ERROR}: stratify_by='{stratify_by}' is in "
                    f"EpisodeDurationResult.descriptor_cols but not in "
                    f"EpisodeDurationResult.data. "
                    f"This should not happen — please report this as a bug."
                )

        self._result      = result
        self._config      = config
        self._stratify_by = stratify_by

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def plot(self, path: str) -> None:
        """
        Save the violin plot to a file.

        Parameters
        ----------
        path : str
            Output file path. Must end in .png, .jpg, or .jpeg.
            Parent directory must exist.
        """
        arrays  = self._result.build_arrays(stratify_by=self._stratify_by)
        plotter = ArraysViolinPlotter(arrays, self._config)
        plotter.plot(path)

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EpisodeDurationViolinPlotter(\n"
            f"  identity     : {self._result.identity!r}\n"
            f"  n_episodes     : {self._result.n_episodes:,}\n"
            f"  n_entities   : {self._result.n_entities:,}\n"
            f"  stratify_by  : {self._stratify_by!r}\n"
            f")"
        )
