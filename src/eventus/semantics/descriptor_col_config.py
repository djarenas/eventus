"""
descriptor_col_config.py
DescriptorColConfig — declares the type and CohortTimeline carriage
rule for one descriptor column.

Lives in semantics because it describes what a column IS and how it
should be carried forward — not what to do with it analytically.
Cleaners and analyzers decide how to aggregate.
"""
from __future__ import annotations

from dataclasses import dataclass

_ERROR = "[DescriptorColConfig] Error"

_VALID_TYPES    = {"category", "numeric"}
_VALID_TIMELINE = {"sequence", "unique", "average", "none"}

_DEFAULT_TIMELINE = {
    "category": "sequence",
    "numeric":  "average",
}

_VALID_TIMELINE_FOR_TYPE = {
    "category": {"sequence", "unique", "none"},
    "numeric":  {"average", "sequence", "none"},
}

_EXAMPLE = (
    "Example:\n"
    "    descriptor_cols:\n"
    "      condition_code:\n"
    "        type: category\n"
    "      bmi_value:\n"
    "        type: numeric\n"
    "        timeline: sequence"
)


@dataclass
class DescriptorColConfig:
    """
    Declares the type and CohortTimeline carriage rule for one
    descriptor column.

    Parameters
    ----------
    type : str
        "category" — values are discrete labels
                     e.g. hospital_id, icd10_condition.
        "numeric"  — values are numbers
                     e.g. bmi_at_admission, systolic_bp.

    timeline : str | None
        How to carry this column into a CohortTimeline.
        Default is determined by type if not specified:
            category → "sequence"
            numeric  → "average"

        For category:  "sequence" (default), "unique", "none"
        For numeric:   "average" (default), "sequence", "none"

        "unique" is not valid for numeric.
        "average" is not valid for category.

    Examples
    --------
    >>> DescriptorColConfig(type="category")
    DescriptorColConfig(type='category', timeline='sequence')

    >>> DescriptorColConfig(type="numeric", timeline="sequence")
    DescriptorColConfig(type='numeric', timeline='sequence')
    """

    type:     str
    timeline: str | None = None

    def __post_init__(self) -> None:
        # ── type ─────────────────────────────────────────────────────
        if not isinstance(self.type, str):
            raise TypeError(
                f"{_ERROR}: 'type' must be a string, "
                f"got {type(self.type).__name__}. "
                f"Valid values: {sorted(_VALID_TYPES)}.\n"
                f"{_EXAMPLE}"
            )
        if self.type not in _VALID_TYPES:
            raise ValueError(
                f"{_ERROR}: 'type' must be one of {sorted(_VALID_TYPES)}, "
                f"got {self.type!r}.\n"
                f"{_EXAMPLE}"
            )

        # ── timeline ──────────────────────────────────────────────────
        if self.timeline is not None and not isinstance(self.timeline, str):
            raise TypeError(
                f"{_ERROR}: 'timeline' must be a string or None, "
                f"got {type(self.timeline).__name__}. "
                f"Valid values: {sorted(_VALID_TIMELINE)}.\n"
                f"{_EXAMPLE}"
            )

        # Apply default
        if self.timeline is None:
            self.timeline = _DEFAULT_TIMELINE[self.type]

        if self.timeline not in _VALID_TIMELINE:
            raise ValueError(
                f"{_ERROR}: 'timeline' must be one of {sorted(_VALID_TIMELINE)}, "
                f"got {self.timeline!r}.\n"
                f"{_EXAMPLE}"
            )

        valid_for_type = _VALID_TIMELINE_FOR_TYPE[self.type]
        if self.timeline not in valid_for_type:
            raise ValueError(
                f"{_ERROR}: timeline={self.timeline!r} is not valid for "
                f"type={self.type!r}. "
                f"Valid timeline values for '{self.type}': "
                f"{sorted(valid_for_type)}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "DescriptorColConfig":
        """
        Build from a dict, e.g. parsed from YAML.

        Expected keys: 'type' (required), 'timeline' (optional).
        """
        if not isinstance(data, dict):
            raise TypeError(
                f"{_ERROR}: each descriptor_cols entry must be a dict, "
                f"got {type(data).__name__}.\n"
                f"{_EXAMPLE}"
            )
        unknown = set(data.keys()) - {"type", "timeline"}
        if unknown:
            raise ValueError(
                f"{_ERROR}: unrecognized keys in descriptor col dict: "
                f"{sorted(unknown)}. Valid keys: 'type', 'timeline'.\n"
                f"{_EXAMPLE}"
            )
        if "type" not in data:
            raise ValueError(
                f"{_ERROR}: missing required key 'type' in descriptor col dict.\n"
                f"{_EXAMPLE}"
            )
        return cls(
            type     = data["type"],
            timeline = data.get("timeline", None),
        )

    def __repr__(self) -> str:
        return (
            f"DescriptorColConfig("
            f"type={self.type!r}, "
            f"timeline={self.timeline!r})"
        )
