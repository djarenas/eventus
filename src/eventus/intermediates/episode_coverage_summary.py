"""
episode_coverage_summary.py
EpisodeCoverageSummary — structured summary of episode coverage analysis
for one identity within a CohortTimeline.

Produced by
-----------
CohortTimelineEpisodeAnalyzer.get_summary()
"""
from __future__ import annotations

_ERROR = "[EpisodeCoverageSummary] Error"

_REQUIRED_TIER1_KEYS = {"t1_total_entities", "t1_any_coverage", "t1_no_coverage"}


class EpisodeCoverageSummary:
    """
    I hold a structured summary of episode coverage analysis for one identity.

    Produced by
    -----------
    CohortTimelineEpisodeAnalyzer.get_summary()

    Properties
    ----------
    identity           : str   — episode identity
    n_total            : int   — total entities in the cohort
    n_with_any_coverage: int   — entities with at least one episode in obs period
    """

    _identity: str
    _tier1:    dict
    _tier2:    dict
    _tier3:    dict

    def __init__(
        self,
        identity: str,
        tier1:    dict,
        tier2:    dict,
        tier3:    dict,
    ) -> None:
        if not isinstance(identity, str) or not identity.strip():
            raise TypeError(
                f"{_ERROR} identity must be a non-empty string, "
                f"got {identity!r}"
            )
        for label, tier in [("tier1", tier1), ("tier2", tier2), ("tier3", tier3)]:
            if not isinstance(tier, dict):
                raise TypeError(
                    f"{_ERROR} {label} must be a dict, "
                    f"got {type(tier).__name__}"
                )

        missing = _REQUIRED_TIER1_KEYS - set(tier1.keys())
        if missing:
            raise ValueError(
                f"{_ERROR} tier1 is missing required keys: {sorted(missing)}."
            )

        self._identity = identity
        self._tier1    = tier1
        self._tier2    = tier2
        self._tier3    = tier3

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def n_total(self) -> int:
        return int(self._tier1["t1_total_entities"])

    @property
    def n_with_any_coverage(self) -> int:
        return int(self._tier1["t1_any_coverage"]["n"])

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        lines = [
            f"EpisodeCoverageSummary:",
            f"  identity : {self._identity}",
            f"  entities : {self.n_total:,}",
        ]

        lines.append("")
        lines.append("  coverage prevalence  (denominator: all entities)")
        lines.extend(self._format_section(self._tier1))

        lines.append("")
        lines.append("  coverage patterns    (denominator: entities with any coverage)")
        lines.extend(self._format_section(self._tier2))

        lines.append("")
        lines.append("  distributions        (denominator: entities with any coverage)")
        lines.extend(self._format_section(self._tier3))

        return "\n".join(lines)

    def _format_section(self, tier: dict) -> list[str]:
        """
        Render one tier dict as indented lines.
        Skips comment keys (starting with '#').
        """
        lines = []
        for key, val in tier.items():
            if key.startswith("#"):
                continue
            formatted = self._format_value(val)
            lines.append(f"    {key} : {formatted}")
        return lines

    def _format_value(self, val) -> str:
        """
        Render a value for display.
        - {"n": x, "pct": y}  →  "x (y%)"
        - {"mean": ..., "p25": ..., ...}  →  "mean=x  p25=y  p50=z ..."
        - None  →  "-"
        - everything else  →  str(val)
        """
        if val is None:
            return "-"
        if isinstance(val, dict):
            if "n" in val and "pct" in val:
                return f"{val['n']:,} ({val['pct']}%)"
            if "mean" in val:
                parts = []
                for k, v in val.items():
                    parts.append(f"{k}={v if v is not None else '-'}")
                return "  ".join(parts)
        return str(val)
