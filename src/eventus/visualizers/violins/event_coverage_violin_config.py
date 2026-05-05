"""
event_coverage_violin_config.py
EventCoverageViolinConfig — violin plot config for EventCoverageViolinPlotter.

Metrics keys are short names corresponding to evt_{identity}_* analysis
columns produced by CohortTimelineEventAnalyzer.compute_coverage().
Requires an identity field so the plotter knows which event identity's
columns to look for in the CohortTimeline.
"""
from __future__ import annotations
import yaml

from .base_violin_config import (
    BaseViolinConfig,
    CategoryConfig,
    StyleConfig,
    PercentilesConfig,
    LabelsConfig,
)

_ERROR_PREFIX = "[EventCoverageViolinConfig] Error"

_VALID_METRICS = {
    "active_days",
    "inactive_days",
    "inactive_days_before_first_event",
    "inactive_days_after_last_event",
    "inactive_days_middle",
}


class EventCoverageViolinConfig(BaseViolinConfig):
    """
    Violin plot configuration for EventCoverageViolinPlotter.

    Metrics keys are short names that map to evt_{identity}_* analysis
    columns in a CohortTimeline. The identity field must match the identity
    passed to CohortTimelineEventAnalyzer when compute_coverage() was called.

    Two plot methods:
    - plot_total()              — active_days vs inactive_days, full cohort
    - plot_inactive_breakdown() — four inactive metrics, filtered to > 0

    Raises at construction if:
    - identity is missing or not a string
    - any metric key is not in the valid set
    - metrics section is empty

    Examples
    --------
    >>> config = EventCoverageViolinConfig.build_from_yaml("config.yaml")
    >>> config = EventCoverageViolinConfig.build_with_defaults("inpatient_hospitalization")

    Example YAML
    ------------
    identity: inpatient_hospitalization

    metrics:
      active_days:
        color: "#4CAF50"
        label: "Hospitalized"
      inactive_days:
        color: "#9E9E9E"
        label: "Total inactive"
      inactive_days_before_first_event:
        color: "#607D8B"
        label: "Before first stay"
      inactive_days_after_last_event:
        color: "#BDBDBD"
        label: "After last stay"
      inactive_days_middle:
        color: "#F44336"
        label: "Gap between stays"

    style:
      figsize:     [12, 7]
      dpi:         150
      show_box:    true
      show_points: false

    percentiles:
      show:        true
      values:      [25, 50]
      linestyle:   dashed
      show_labels: true

    labels:
      duration_unit: days
    """

    _VALID_SECTIONS = {"identity", "metrics", "style", "percentiles", "labels"}

    def __init__(
        self,
        identity:    str,
        metrics:     dict              = None,
        style:       StyleConfig       = None,
        percentiles: PercentilesConfig = None,
        labels:      LabelsConfig      = None,
    ) -> None:
        super().__init__(
            stratify    = metrics,
            style       = style,
            percentiles = percentiles,
            labels      = labels,
        )
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(
                f"{_ERROR_PREFIX}: identity must be a non-empty string, "
                f"got {identity!r}"
            )
        self.identity = identity
        self._validate()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate(self) -> None:
        if not self.stratify:
            raise ValueError(
                f"{_ERROR_PREFIX}: metrics section is empty — "
                f"add at least one metric. "
                f"Valid metrics: {sorted(_VALID_METRICS)}"
            )
        invalid = set(self.stratify.keys()) - _VALID_METRICS
        if invalid:
            raise ValueError(
                f"{_ERROR_PREFIX}: invalid metric keys: {sorted(invalid)}. "
                f"Valid metrics: {sorted(_VALID_METRICS)}"
            )

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def metrics(self) -> dict:
        """Alias for stratify — metric col → CategoryConfig."""
        return self.stratify

    @property
    def breakdown_cols(self) -> list[str]:
        """Inactive breakdown columns in fixed display order."""
        order = [
            "inactive_days",
            "inactive_days_before_first_event",
            "inactive_days_after_last_event",
            "inactive_days_middle",
        ]
        return [c for c in order if c in self.stratify]

    def has_metric(self, col: str) -> bool:
        return col in self.stratify

    def can_plot_total(self) -> bool:
        return (
            self.has_metric("active_days") and
            self.has_metric("inactive_days")
        )

    def can_plot_breakdown(self) -> bool:
        return any(self.has_metric(c) for c in [
            "inactive_days_before_first_event",
            "inactive_days_after_last_event",
            "inactive_days_middle",
        ])

    # ------------------------------------------------------------------ #
    # Classmethods
    # ------------------------------------------------------------------ #

    @classmethod
    def build_with_defaults(cls, identity: str) -> "EventCoverageViolinConfig":
        """Return a config with all five metrics and sensible defaults."""
        return cls(
            identity = identity,
            metrics  = {
                "active_days": CategoryConfig(
                    color="#4CAF50", label="Hospitalized"
                ),
                "inactive_days": CategoryConfig(
                    color="#9E9E9E", label="Total inactive"
                ),
                "inactive_days_before_first_event": CategoryConfig(
                    color="#607D8B", label="Before first stay"
                ),
                "inactive_days_after_last_event": CategoryConfig(
                    color="#BDBDBD", label="After last stay"
                ),
                "inactive_days_middle": CategoryConfig(
                    color="#F44336", label="Gap between stays"
                ),
            },
            percentiles = PercentilesConfig(values=[25, 50]),
        )

    @classmethod
    def build_from_yaml(cls, path: str) -> "EventCoverageViolinConfig":
        """Build an EventCoverageViolinConfig from a YAML file."""
        raw = cls._parse_yaml(path)

        if "identity" not in raw:
            raise ValueError(
                f"{_ERROR_PREFIX}: YAML must contain 'identity' — "
                f"must match the identity passed to "
                f"CohortTimelineEventAnalyzer when compute_coverage() was called."
            )

        metrics = {}
        for key, val in (raw.get("metrics") or {}).items():
            if not isinstance(val, dict):
                raise ValueError(
                    f"{_ERROR_PREFIX}: metrics.{key!r} must be a mapping "
                    f"with 'color' and optional 'label', "
                    f"got {type(val).__name__}"
                )
            metrics[key] = CategoryConfig(**val)

        return cls(
            identity    = raw["identity"],
            metrics     = metrics,
            style       = cls._build_nested(StyleConfig,       raw.get("style")),
            percentiles = cls._build_nested(PercentilesConfig, raw.get("percentiles")),
            labels      = cls._build_nested(LabelsConfig,      raw.get("labels")),
        )

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def to_yaml(self, path: str) -> None:
        """Save this config to a YAML file."""
        metrics_raw = {}
        for key, cat in self.stratify.items():
            entry = {"color": cat.color}
            if cat.label is not None:
                entry["label"] = cat.label
            metrics_raw[key] = entry

        base = self._base_yaml_dict()
        cfg  = {
            "identity":    self.identity,
            "metrics":     metrics_raw,
            "style":       base["style"],
            "percentiles": base["percentiles"],
            "labels":      base["labels"],
        }
        with open(path, "w") as f:
            yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
        print(f"Config saved to: {path}")

    # ------------------------------------------------------------------ #
    # Dunder
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"EventCoverageViolinConfig(\n"
            f"  identity    : {self.identity!r}\n"
            f"  metrics     : {list(self.stratify.keys())}\n"
            f"  show_box    : {self.style.show_box}\n"
            f"  show_points : {self.style.show_points}\n"
            f"  percentiles : {self.percentiles.values}\n"
            f"  unit        : {self.labels.duration_unit}\n"
            f")"
        )
