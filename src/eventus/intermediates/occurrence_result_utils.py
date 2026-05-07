"""
occurrence_result_utils.py
Shared display and formatting logic for occurrence result objects.
No dependencies on other eventus utils files.

Functions
---------
to_yaml_repr(class_name, fields)
    Render a YAML-style __repr__ string from a dict of fields.
"""
from __future__ import annotations
import pandas as pd

_ERROR = "[occurrence_result_utils] Error"


def to_yaml_repr(class_name: str, fields: dict) -> str:
    """
    Render a clean YAML-style __repr__ string.

    Parameters
    ----------
    class_name : str
        The name of the result class (e.g. 'OccurrenceVolume').
    fields : dict
        Ordered dict of label → value pairs to display.
        Values may be any type — rendered via str().

    Returns
    -------
    str
        A multi-line string of the form:

        ClassName:
          field_one : value
          field_two : value

    Example
    -------
    >>> to_yaml_repr("OccurrenceVolume", {
    ...     "identity"  : "vaccination",
    ...     "entities"  : 1000,
    ...     "n_with_any": "847 (84.7%)",
    ... })
    OccurrenceVolume:
      identity   : vaccination
      entities   : 1,000
      n_with_any : 847 (84.7%)
    """
    if not isinstance(class_name, str) or not class_name.strip():
        raise TypeError(
            f"{_ERROR} class_name must be a non-empty string, "
            f"got {class_name!r}"
        )
    if not isinstance(fields, dict):
        raise TypeError(
            f"{_ERROR} fields must be a dict, "
            f"got {type(fields).__name__}"
        )

    max_key_len = max((len(k) for k in fields), default=0)
    lines = [f"{class_name}:"]
    for key, val in fields.items():
        padded = key.ljust(max_key_len)
        lines.append(f"  {padded} : {val}")
    return "\n".join(lines)


def format_n_pct(n: int, total: int) -> str:
    """
    Format a count and percentage as 'n (x.x%)'.

    Parameters
    ----------
    n : int
        The count.
    total : int
        The denominator for percentage calculation.

    Returns
    -------
    str
        e.g. '847 (84.7%)' or '0 (0.0%)' if total is 0.
    """
    pct = round(100 * n / total, 1) if total > 0 else 0.0
    return f"{n:,} ({pct}%)"
