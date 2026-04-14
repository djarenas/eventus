"""Helper functions for preparing count model design matrices.

These functions take a covariates DataFrame and transform it into
a numeric design matrix suitable for regression. Handles categorical
encoding, interaction terms, intercept addition, and event-level
aggregation.

The encoded column names become the coefficient keys in
CovariateDistribution objects. This is the contract between
the design matrix and everything downstream.
"""

import numpy as np
import pandas as pd


_ERROR_PREFIX = "[helper_count_design_matrix_preparer]"

# Supported encoding methods
ENCODING_METHODS = {"dummy", "one_hot"}

# Supported aggregation methods (must match CovariateSemantics)
AGGREGATION_METHODS = {
    "mean": lambda x: x.mean(),
    "sum": lambda x: x.sum(),
    "min": lambda x: x.min(),
    "max": lambda x: x.max(),
    "median": lambda x: x.median(),
    "mode": lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else np.nan,
    "proportion": lambda x: x.mean(),  # works for binary 0/1 columns
}


def encode_categoricals(df: pd.DataFrame, categorical_cols: list,
                         encoding: str = "dummy") -> pd.DataFrame:
    """Encode categorical columns as numeric columns.

    Args:
        df: DataFrame containing the categorical columns.
        categorical_cols: List of column names to encode.
        encoding: Encoding method.
            "dummy" — k-1 columns, drops first category alphabetically.
            "one_hot" — k columns, no drop.

    Returns:
        New DataFrame with categorical columns replaced by encoded
        columns. Original categorical columns are removed. All other
        columns are preserved.

    Raises:
        ValueError: If encoding method is not supported.
        KeyError: If any categorical column is not in the DataFrame.
    """
    if encoding not in ENCODING_METHODS:
        raise ValueError(
            f"{_ERROR_PREFIX} encode_categoricals: "
            f"encoding must be one of {ENCODING_METHODS}, got '{encoding}'"
        )

    missing = [col for col in categorical_cols if col not in df.columns]
    if missing:
        raise KeyError(
            f"{_ERROR_PREFIX} encode_categoricals: "
            f"Columns not found in DataFrame: {missing}"
        )

    if not categorical_cols:
        return df.copy()

    result = df.copy()

    for col in categorical_cols:
        # Sort categories for consistent ordering
        categories = sorted(result[col].unique())

        if encoding == "dummy":
            # Drop first category (reference level)
            for cat in categories[1:]:
                col_name = f"{col}_{cat}"
                result[col_name] = (result[col] == cat).astype(float)
        elif encoding == "one_hot":
            for cat in categories:
                col_name = f"{col}_{cat}"
                result[col_name] = (result[col] == cat).astype(float)

        # Remove original categorical column
        result = result.drop(columns=[col])

    return result


def build_interaction_terms(df: pd.DataFrame,
                             interactions: list) -> pd.DataFrame:
    """Add interaction term columns to a DataFrame.

    Each interaction is a tuple of two column names. The interaction
    column is the product of those two columns. For categorical
    encoded columns, this creates interactions with each dummy.

    Args:
        df: DataFrame with numeric columns (categoricals already encoded).
        interactions: List of (col1, col2) tuples.

    Returns:
        New DataFrame with interaction columns appended.
        Interaction columns are named "col1_x_col2".

    Raises:
        KeyError: If an interaction references a column not in the DataFrame.
        ValueError: If an interaction tuple doesn't have exactly 2 elements.
    """
    if not interactions:
        return df.copy()

    result = df.copy()

    for i, interaction in enumerate(interactions):
        if not isinstance(interaction, (tuple, list)) or len(interaction) != 2:
            raise ValueError(
                f"{_ERROR_PREFIX} build_interaction_terms: "
                f"interaction[{i}] must be a tuple of 2 column names, "
                f"got {interaction}"
            )

        col1_name, col2_name = interaction

        # Find all columns that match each name
        # (handles encoded categoricals: "county" matches "county_DuPage", etc.)
        col1_matches = _find_matching_columns(result, col1_name)
        col2_matches = _find_matching_columns(result, col2_name)

        if not col1_matches:
            raise KeyError(
                f"{_ERROR_PREFIX} build_interaction_terms: "
                f"No columns found matching '{col1_name}' in interaction[{i}]"
            )
        if not col2_matches:
            raise KeyError(
                f"{_ERROR_PREFIX} build_interaction_terms: "
                f"No columns found matching '{col2_name}' in interaction[{i}]"
            )

        # Create interaction for each pair of matching columns
        for c1 in col1_matches:
            for c2 in col2_matches:
                if c1 != c2:  # avoid self-interaction
                    interaction_name = f"{c1}_x_{c2}"
                    result[interaction_name] = result[c1] * result[c2]

    return result


def _find_matching_columns(df: pd.DataFrame, name: str) -> list:
    """Find columns matching a name, including encoded versions.

    If 'county' is the name, matches 'county' (exact) or
    'county_DuPage', 'county_Lake' (encoded).

    Args:
        df: DataFrame to search.
        name: Column name or base name of encoded columns.

    Returns:
        List of matching column names.
    """
    # Exact match first
    if name in df.columns:
        return [name]

    # Encoded match: look for columns starting with "name_"
    prefix = f"{name}_"
    matches = [col for col in df.columns if col.startswith(prefix)]
    return matches


def add_intercept(df: pd.DataFrame) -> pd.DataFrame:
    """Add an intercept column (all ones) as the first column.

    Args:
        df: DataFrame to add intercept to.

    Returns:
        New DataFrame with 'intercept' as the first column.
    """
    result = df.copy()
    result.insert(0, "intercept", 1.0)
    return result


def aggregate_event_level(events_df: pd.DataFrame,
                           person_id_col: str,
                           event_level_continuous: list = None,
                           event_level_categorical: list = None) -> pd.DataFrame:
    """Aggregate event-level covariates to person-level.

    Takes a DataFrame with multiple rows per person and produces
    one row per person with aggregated values.

    Args:
        events_df: DataFrame with event-level data.
        person_id_col: Column name for person identifier.
        event_level_continuous: List of dicts with 'column' and
            'aggregation' keys. e.g. [{"column": "wait_time", "aggregation": "mean"}]
        event_level_categorical: List of dicts with 'column' and
            'aggregation' keys. e.g. [{"column": "was_emergency", "aggregation": "proportion"}]

    Returns:
        DataFrame with one row per person and aggregated columns.

    Raises:
        KeyError: If person_id_col or any covariate column not in DataFrame.
        ValueError: If aggregation method is not supported.
    """
    if person_id_col not in events_df.columns:
        raise KeyError(
            f"{_ERROR_PREFIX} aggregate_event_level: "
            f"person_id_col '{person_id_col}' not found in DataFrame"
        )

    event_level_continuous = event_level_continuous or []
    event_level_categorical = event_level_categorical or []

    all_specs = event_level_continuous + event_level_categorical

    if not all_specs:
        # Nothing to aggregate — just return unique person IDs
        return events_df[[person_id_col]].drop_duplicates().reset_index(drop=True)

    agg_dict = {}
    for spec in all_specs:
        col = spec["column"]
        agg_method = spec["aggregation"]

        if col not in events_df.columns:
            raise KeyError(
                f"{_ERROR_PREFIX} aggregate_event_level: "
                f"Column '{col}' not found in DataFrame"
            )
        if agg_method not in AGGREGATION_METHODS:
            raise ValueError(
                f"{_ERROR_PREFIX} aggregate_event_level: "
                f"Unknown aggregation '{agg_method}' for column '{col}'. "
                f"Available: {list(AGGREGATION_METHODS.keys())}"
            )

        agg_dict[col] = AGGREGATION_METHODS[agg_method]

    result = events_df.groupby(person_id_col).agg(agg_dict).reset_index()
    return result


def build_design_matrix_dataframe(
    covariates_df: pd.DataFrame,
    continuous_cols: list = None,
    categorical_cols: list = None,
    interactions: list = None,
    encoding: str = "dummy",
    add_intercept_col: bool = True,
    drop_person_id: str = None,
) -> tuple:
    """Build a complete design matrix from a covariates DataFrame.

    This is the main function. It:
    1. Selects the requested columns
    2. Encodes categoricals
    3. Builds interaction terms
    4. Adds intercept
    5. Returns numpy matrix + column names

    Args:
        covariates_df: DataFrame with one row per person.
        continuous_cols: List of continuous column names to include.
        categorical_cols: List of categorical column names to encode.
        interactions: List of (col1, col2) tuples for interaction terms.
            Use original column names (before encoding).
        encoding: "dummy" (k-1) or "one_hot" (k) for categoricals.
        add_intercept_col: If True, prepend an intercept column.
        drop_person_id: If specified, drop this column from the matrix
            (keep it for reference but don't include in numeric matrix).

    Returns:
        Tuple of (matrix, column_names) where:
        - matrix: np.ndarray of shape (n_persons, n_features)
        - column_names: list of column name strings matching matrix columns

    Raises:
        TypeError: If covariates_df is not a DataFrame.
        KeyError: If requested columns are not found.
        ValueError: If encoding method is not supported.
    """
    if not isinstance(covariates_df, pd.DataFrame):
        raise TypeError(
            f"{_ERROR_PREFIX} build_design_matrix_dataframe: "
            f"Expected DataFrame, got {type(covariates_df).__name__}"
        )

    continuous_cols = continuous_cols or []
    categorical_cols = categorical_cols or []
    interactions = interactions or []

    # Validate all requested columns exist
    all_requested = continuous_cols + categorical_cols
    missing = [col for col in all_requested if col not in covariates_df.columns]
    if missing:
        raise KeyError(
            f"{_ERROR_PREFIX} build_design_matrix_dataframe: "
            f"Columns not found: {missing}. "
            f"Available: {list(covariates_df.columns)}"
        )

    # Select only the columns we need
    selected = covariates_df[all_requested].copy()

    # Encode categoricals
    if categorical_cols:
        selected = encode_categoricals(selected, categorical_cols, encoding)

    # Build interaction terms
    if interactions:
        selected = build_interaction_terms(selected, interactions)

    # Add intercept
    if add_intercept_col:
        selected = add_intercept(selected)

    # Convert to numpy
    column_names = list(selected.columns)
    matrix = selected.values.astype(float)

    return matrix, column_names
