"""
pipe_delimited_utils.py
Content validation utilities for PipeDelimitedIntermediate and its subclasses.
Validates pipe-delimited date columns row by row, collecting all bad rows.
"""
from __future__ import annotations
import pandas as pd

_ERROR_PREFIX = "[pipe_delimited_utils] Error"


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _try_parse_date(value: str) -> bool:
    """Return True if value is a parseable date string, False otherwise."""
    try:
        pd.Timestamp(value.strip())
        return True
    except Exception:
        return False


def _validate_pipe_dates(series: pd.Series, col_name: str) -> pd.Series:
    """
    For each row, check that all pipe-delimited tokens are valid dates.
    Returns a boolean Series — True where the row is BAD.
    """
    def row_is_bad(val) -> bool:
        if pd.isna(val):
            return False  # NAs handled separately
        tokens = str(val).split(" | ")
        return not all(_try_parse_date(t) for t in tokens)

    return series.apply(row_is_bad)


def _count_pipe_tokens(series: pd.Series) -> pd.Series:
    """Count pipe-delimited tokens per row. NAs return 0."""
    def count(val) -> int:
        if pd.isna(val):
            return 0
        return len(str(val).split(" | "))
    return series.apply(count)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def validate_content(
    data: pd.DataFrame,
    entity_col: str,
) -> pd.DataFrame:
    """
    Validate content of pipe-delimited date columns row by row.

    Checks:
    - span_start and span_end are valid dates (if present)
    - span_start <= span_end (if present)
    - event_starts and event_ends contain valid dates (if present)
    - event_starts and event_ends have the same token count per row (if present)
    - Any occ_* columns contain valid dates (if present)

    Parameters
    ----------
    data : pd.DataFrame
        The intermediate DataFrame to validate.
    entity_col : str
        Name of the entity identifier column.

    Returns
    -------
    pd.DataFrame
        Rows that failed validation, with an added '_validation_reason' column.
        Empty DataFrame if all rows are valid.
    """
    cols    = set(data.columns)
    reasons = pd.Series("", index=data.index)

    # --- span_start / span_end ---
    if "span_start" in cols and "span_end" in cols:
        # Check parseable
        bad_start = _validate_pipe_dates(data["span_start"], "span_start")
        bad_end   = _validate_pipe_dates(data["span_end"],   "span_end")
        reasons[bad_start] += "span_start is not a valid date; "
        reasons[bad_end]   += "span_end is not a valid date; "

        # Check ordering — only for rows where both parse
        both_valid = ~bad_start & ~bad_end & data["span_start"].notna() & data["span_end"].notna()
        if both_valid.any():
            starts = pd.to_datetime(data.loc[both_valid, "span_start"], errors="coerce")
            ends   = pd.to_datetime(data.loc[both_valid, "span_end"],   errors="coerce")
            bad_order = starts > ends
            reasons[both_valid & bad_order.values] += "span_start > span_end; "

    # --- event_starts / event_ends ---
    if "event_starts" in cols and "event_ends" in cols:
        # Check parseable dates in each token
        bad_starts = _validate_pipe_dates(data["event_starts"], "event_starts")
        bad_ends   = _validate_pipe_dates(data["event_ends"],   "event_ends")
        reasons[bad_starts] += "event_starts contains invalid dates; "
        reasons[bad_ends]   += "event_ends contains invalid dates; "

        # Check token counts match
        non_na = data["event_starts"].notna() & data["event_ends"].notna()
        if non_na.any():
            n_starts = _count_pipe_tokens(data.loc[non_na, "event_starts"])
            n_ends   = _count_pipe_tokens(data.loc[non_na, "event_ends"])
            mismatched = n_starts != n_ends
            reasons[non_na & mismatched.values] += (
                "event_starts and event_ends have different token counts; "
            )

    # --- occ_* columns ---
    occ_cols = [c for c in cols if c.startswith("occ_")]
    for col in occ_cols:
        bad = _validate_pipe_dates(data[col], col)
        reasons[bad] += f"'{col}' contains invalid dates; "

    # --- Collect bad rows ---
    is_bad = reasons.str.len() > 0
    if not is_bad.any():
        return pd.DataFrame(columns=list(data.columns) + ["_validation_reason"])

    bad_df = data[is_bad].copy()
    bad_df["_validation_reason"] = reasons[is_bad].str.rstrip("; ")
    return bad_df.reset_index(drop=True)
