"""
merge_config.py
MergeConfig — configuration for merging overlapping or adjacent
episode intervals within EpisodesCleaner.

If merge is None in EpisodesCleanerConfig, no merging is performed.
If merge is a MergeConfig, merging is performed with the declared rules.

merge_mandates (which columns must match to allow merging) are declared
in EpisodeSemantics.also_defined_by — not here. MergeConfig only declares
the gap threshold and how to aggregate descriptor columns.

Example YAML (nested inside EpisodesCleanerConfig):

    merge:
      meaningful_gap_days: 1
      descriptor_cols:
        icd10_condition:  unique
        bmi_at_admission: median
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_ERROR = "[MergeConfig] Error"

_VALID_CATEGORY_RULES = {"sequence", "unique"}
_VALID_NUMERIC_RULES  = {"mean", "median", "min", "max", "variance"}
_ALL_VALID_RULES      = _VALID_CATEGORY_RULES | _VALID_NUMERIC_RULES


@dataclass
class MergeConfig:
    """
    Configuration for merging overlapping or adjacent episode intervals.

    Which columns must match before two intervals can be merged is
    declared in EpisodeSemantics.also_defined_by — that is a semantic
    property of the data, not a cleaning strategy.

    MergeConfig declares:
      - How large a gap to bridge (meaningful_gap_days)
      - How to aggregate descriptor columns when rows are merged

    Parameters
    ----------
    meaningful_gap_days : int
        Gaps between consecutive intervals of <= this many days are
        treated as continuous and merged into one episode.
        0 = only merge exactly overlapping intervals.
        1 = also merge intervals separated by a single day gap
            (e.g. discharged Monday, readmitted Tuesday = one episode).

    descriptor_cols : dict[str, str]
        Aggregation rules for descriptor columns during merging.
        Keys are column names declared in EpisodeSemantics.descriptor_cols.
        Values are aggregation rules:
            For category columns: "sequence" or "unique"
            For numeric columns:  "mean", "median", "min", "max", "variance"

    Examples
    --------
    >>> MergeConfig(
    ...     meaningful_gap_days = 1,
    ...     descriptor_cols     = {
    ...         "icd10_condition":  "unique",
    ...         "bmi_at_admission": "median",
    ...     },
    ... )
    """

    meaningful_gap_days: int
    descriptor_cols:     dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.meaningful_gap_days, int) or \
                self.meaningful_gap_days < 0:
            raise ValueError(
                f"{_ERROR}: meaningful_gap_days must be a non-negative int, "
                f"got {self.meaningful_gap_days!r}"
            )
        if not isinstance(self.descriptor_cols, dict):
            raise ValueError(
                f"{_ERROR}: descriptor_cols must be a dict, "
                f"got {type(self.descriptor_cols).__name__}"
            )
        for col, rule in self.descriptor_cols.items():
            if rule not in _ALL_VALID_RULES:
                raise ValueError(
                    f"{_ERROR}: descriptor_cols[{col!r}] has invalid "
                    f"aggregation rule {rule!r}. "
                    f"Valid rules: {sorted(_ALL_VALID_RULES)}"
                )

    def validate_against_semantics(
        self,
        also_defined_by: list[str],
        descriptor_cols: dict,
    ) -> None:
        """
        Validate MergeConfig against EpisodeSemantics at cleaner construction.

        Checks:
          - descriptor_cols keys are declared in EpisodeSemantics.descriptor_cols
          - descriptor_cols keys do not overlap with also_defined_by
          - aggregation rules are compatible with column types

        Parameters
        ----------
        also_defined_by : list[str]
            From EpisodeSemantics.also_defined_by.
        descriptor_cols : dict[str, DescriptorColConfig]
            From EpisodeSemantics.descriptor_cols.
        """
        sem_descriptors  = set(descriptor_cols.keys() if descriptor_cols else [])
        sem_also_defined = set(also_defined_by or [])

        # All merge descriptor_cols must be declared in semantics
        undeclared = set(self.descriptor_cols) - sem_descriptors
        if undeclared:
            raise ValueError(
                f"{_ERROR}: descriptor_cols keys not declared in "
                f"EpisodeSemantics.descriptor_cols: {sorted(undeclared)}. "
                f"Declare them in EpisodeSemantics first."
            )

        # Descriptor cols cannot overlap with also_defined_by
        overlap = set(self.descriptor_cols) & sem_also_defined
        if overlap:
            raise ValueError(
                f"{_ERROR}: descriptor_cols cannot include columns from "
                f"also_defined_by — those are identity columns, not "
                f"descriptors: {sorted(overlap)}"
            )

        # Aggregation rules must be compatible with column types
        if descriptor_cols:
            for col, rule in self.descriptor_cols.items():
                col_type = descriptor_cols[col].type
                if col_type == "category" and rule not in _VALID_CATEGORY_RULES:
                    raise ValueError(
                        f"{_ERROR}: column {col!r} is type 'category' but "
                        f"aggregation rule {rule!r} is for numeric columns. "
                        f"Valid category rules: {sorted(_VALID_CATEGORY_RULES)}"
                    )
                if col_type == "numeric" and rule not in _VALID_NUMERIC_RULES:
                    raise ValueError(
                        f"{_ERROR}: column {col!r} is type 'numeric' but "
                        f"aggregation rule {rule!r} is for category columns. "
                        f"Valid numeric rules: {sorted(_VALID_NUMERIC_RULES)}"
                    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MergeConfig":
        """
        Build from a dict, e.g. parsed from YAML.

        Expected structure:
            meaningful_gap_days: int
            descriptor_cols:                    (optional)
                col_name: aggregation_rule
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"{_ERROR}: expected a dict, got {type(data).__name__}"
            )
        if "meaningful_gap_days" not in data:
            raise ValueError(
                f"{_ERROR}: missing required key 'meaningful_gap_days'"
            )

        descriptor_cols = {}
        for col, rule in (data.get("descriptor_cols") or {}).items():
            if not isinstance(rule, str):
                raise ValueError(
                    f"{_ERROR}: descriptor_cols[{col!r}] must be a string "
                    f"aggregation rule, got {type(rule).__name__}"
                )
            descriptor_cols[col] = rule

        return cls(
            meaningful_gap_days = int(data["meaningful_gap_days"]),
            descriptor_cols     = descriptor_cols,
        )

    def __repr__(self) -> str:
        return (
            f"MergeConfig(\n"
            f"  meaningful_gap_days : {self.meaningful_gap_days}\n"
            f"  descriptor_cols     : {self.descriptor_cols}\n"
            f")"
        )
