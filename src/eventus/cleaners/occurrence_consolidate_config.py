"""
occurrence_consolidate_config.py
OccurrenceConsolidateConfig — configuration for consolidating
same-date occurrence records within OccurrencesCleaner.

If consolidate is None in OccurrencesCleanerConfig, no consolidation
is performed beyond standard deduplication.
If consolidate is an OccurrenceConsolidateConfig, records sharing
the same entity + date + also_defined_by values are consolidated
into one occurrence, with descriptor columns aggregated according
to the declared rules.

Example YAML (nested inside OccurrencesCleanerConfig):

    consolidate:
      descriptor_cols:
        triage_level:   unique
        wait_time_mins: median
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_ERROR = "[OccurrenceConsolidateConfig] Error"

_VALID_CATEGORY_RULES = {"sequence", "unique"}
_VALID_NUMERIC_RULES  = {"mean", "median", "min", "max", "variance"}
_ALL_VALID_RULES      = _VALID_CATEGORY_RULES | _VALID_NUMERIC_RULES


@dataclass
class OccurrenceConsolidateConfig:
    """
    Configuration for consolidating same-date occurrence records.

    Two occurrences are eligible for consolidation only if:
      - They belong to the same entity, AND
      - They share the same date, AND
      - All OccurrenceSemantics.also_defined_by columns match

    Descriptor columns declared in descriptor_cols are aggregated
    according to their rules. Descriptor columns not declared here
    are pipe-aggregated using sequence as a fallback.

    Parameters
    ----------
    descriptor_cols : dict[str, str]
        Aggregation rules for descriptor columns during consolidation.
        Keys are column names declared in OccurrenceSemantics.descriptor_cols.
        Values are aggregation rules:
            For category columns: "sequence" or "unique"
            For numeric columns:  "mean", "median", "min", "max", "variance"

    Examples
    --------
    >>> OccurrenceConsolidateConfig(
    ...     descriptor_cols = {
    ...         "triage_level":   "unique",
    ...         "wait_time_mins": "median",
    ...     },
    ... )
    """

    descriptor_cols: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
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
        Validate OccurrenceConsolidateConfig against OccurrenceSemantics
        at cleaner construction.

        Checks:
          - descriptor_cols keys are declared in OccurrenceSemantics.descriptor_cols
          - descriptor_cols keys do not overlap with also_defined_by
          - aggregation rules are compatible with column types

        Parameters
        ----------
        also_defined_by : list[str]
            From OccurrenceSemantics.also_defined_by.
        descriptor_cols : dict[str, DescriptorColConfig]
            From OccurrenceSemantics.descriptor_cols.
        """
        sem_descriptors  = set(descriptor_cols.keys() if descriptor_cols else [])
        sem_also_defined = set(also_defined_by or [])

        # All consolidate descriptor_cols must be declared in semantics
        undeclared = set(self.descriptor_cols) - sem_descriptors
        if undeclared:
            raise ValueError(
                f"{_ERROR}: descriptor_cols keys not declared in "
                f"OccurrenceSemantics.descriptor_cols: {sorted(undeclared)}. "
                f"Declare them in OccurrenceSemantics first."
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
    def from_dict(cls, data: dict[str, Any]) -> "OccurrenceConsolidateConfig":
        """
        Build from a dict, e.g. parsed from YAML.

        Expected structure:
            descriptor_cols:        (optional)
                col_name: aggregation_rule
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"{_ERROR}: expected a dict, got {type(data).__name__}"
            )

        descriptor_cols = {}
        for col, rule in (data.get("descriptor_cols") or {}).items():
            if not isinstance(rule, str):
                raise ValueError(
                    f"{_ERROR}: descriptor_cols[{col!r}] must be a string "
                    f"aggregation rule, got {type(rule).__name__}"
                )
            descriptor_cols[col] = rule

        return cls(descriptor_cols=descriptor_cols)

    def __repr__(self) -> str:
        return (
            f"OccurrenceConsolidateConfig(\n"
            f"  descriptor_cols : {self.descriptor_cols}\n"
            f")"
        )
