"""
validation_utils.py
Shared validation helpers used across analyzer classes.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[validation_utils] Error"


def validate_shared_entity_col(obj_a, obj_b, label_a: str = "obj_a", label_b: str = "obj_b") -> str:
    """
    Validate that two objects share the same entity_id_col in their semantics
    and that the column exists in both .data DataFrames.

    Parameters
    ----------
    obj_a, obj_b : any object with .semantics.entity_id_col and .data
        Typically Events, EventsPerEntity, Occurrences, or similar.
    label_a, label_b : str
        Human-readable names for the objects, used in error messages.

    Returns
    -------
    str
        The shared entity_id_col name.

    Raises
    ------
    ValueError
        If entity_id_col values differ between the two objects,
        or if the column is missing from either .data DataFrame.
    """
    col_a = obj_a.semantics.entity_id_col
    col_b = obj_b.semantics.entity_id_col

    if col_a != col_b:
        raise ValueError(
            f"{_ERROR_PREFIX}: {label_a} and {label_b} have different entity_id_col — "
            f"'{col_a}' vs '{col_b}'"
        )

    if col_a not in obj_a.data.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: entity_id_col '{col_a}' not found in {label_a}.data"
        )

    if col_b not in obj_b.data.columns:
        raise ValueError(
            f"{_ERROR_PREFIX}: entity_id_col '{col_b}' not found in {label_b}.data"
        )

    return col_a