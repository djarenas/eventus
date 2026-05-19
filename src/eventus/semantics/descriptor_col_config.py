"""
descriptor_col_config.py
DescriptorColConfig — declares the type and CohortTimeline carriage
rule for one descriptor column.

Lives in semantics because it describes what a column IS and how it
should be carried forward — not what to do with it analytically.
Cleaners and analyzers decide how to aggregate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_ERROR = "[DescriptorColConfig] Error"

_VALID_TYPES    = {"category", "numeric"}
_VALID_TIMELINE = {"sequence", "unique", "average", "none"}

# Default timeline behavior by type
_DEFAULT_TIMELINE = {
    "category": "sequence",
    "numeric":  "average",
}

# Valid timeline values per type
_VALID_TIMELINE_FOR_TYPE = {
    "category": {"sequence", "unique", "none"},
    "numeric":  {"average", "sequence", "none"},
}


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

        Valid values per type:

        For category columns:
            "sequence" (default) — pipe-delimit values in visit order,
                preserving repetition.
                e.g. visits with conditionA, conditionA, conditionB
                     → "conditionA | conditionA | conditionB"
                Use when the order or frequency of values matters.
                e.g. "patient had conditionA twice then conditionB"

            "unique" — collect all values across visits, deduplicate,
                sort alphabetically.
                e.g. visits with conditionA, conditionA, conditionB
                     → "conditionA | conditionB"
                Use when you only care what categories appeared,
                not how many times or in what order.
                e.g. for stratification: "was this patient ever
                     seen for conditionB?"

            "none"   — do not carry into CohortTimeline.

        For numeric columns:
            "average" (default) — compute the mean across visits and
                carry a single float.
                e.g. BP readings [118.2, 124.5, 109.0] → 117.2
                Use when you want a per-member summary value.

            "sequence" — pipe-delimit values in visit order.
                e.g. [118.2, 124.5, 109.0]
                     → "118.2 | 124.5 | 109.0"
                Use when the trend or pattern across visits matters.

            "none"    — do not carry into CohortTimeline.

        Note: "unique" is not valid for numeric columns — deduplicating
        floating point measurements is not meaningful. "average" is not
        valid for category columns — averaging labels makes no sense.

    Examples
    --------
    >>> DescriptorColConfig(type="category")
    DescriptorColConfig(type='category', timeline='sequence')

    >>> DescriptorColConfig(type="category", timeline="unique")
    DescriptorColConfig(type='category', timeline='unique')

    >>> DescriptorColConfig(type="numeric")
    DescriptorColConfig(type='numeric', timeline='average')

    >>> DescriptorColConfig(type="numeric", timeline="sequence")
    DescriptorColConfig(type='numeric', timeline='sequence')
    """

    type:     str
    timeline: str | None = None

    def __post_init__(self) -> None:
        # Validate type
        if self.type not in _VALID_TYPES:
            raise ValueError(
                f"{_ERROR}: type must be one of {sorted(_VALID_TYPES)}, "
                f"got {self.type!r}"
            )

        # Apply default timeline if not specified
        if self.timeline is None:
            self.timeline = _DEFAULT_TIMELINE[self.type]

        # Validate timeline value
        if self.timeline not in _VALID_TIMELINE:
            raise ValueError(
                f"{_ERROR}: timeline must be one of {sorted(_VALID_TIMELINE)}, "
                f"got {self.timeline!r}"
            )

        # Validate timeline is compatible with type
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

        Expected keys:
            type     : required
            timeline : optional — defaults applied if absent
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"{_ERROR}: expected a dict, got {type(data).__name__}"
            )
        if "type" not in data:
            raise ValueError(f"{_ERROR}: missing required key 'type'")
        return cls(
            type     = str(data["type"]),
            timeline = str(data["timeline"]) if "timeline" in data else None,
        )

    def __repr__(self) -> str:
        return (
            f"DescriptorColConfig("
            f"type={self.type!r}, "
            f"timeline={self.timeline!r})"
        )
