"""Events with covariates.

EventsWithCovariates extends Events by adding a CovariateSemantics
that describes which columns in the data are person-level or
event-level covariates. It validates that the covariate columns
exist, are the right types, and that person-level covariates are
actually constant per person.

It inherits all functionality from Events — filtering, counting,
triage — and adds covariate-specific validation on top.
"""

import pandas as pd

from .events import Events
from .event_semantics import EventSemantics
from .covariate_semantics import CovariateSemantics


class EventsWithCovariates(Events):
    """Events that have person-level and event-level features attached.

    Inherits from Events — it IS an Events object. Any code that
    accepts Events will also accept EventsWithCovariates. The
    covariate_semantics attribute describes which columns are
    covariates and what type they are.

    Attributes:
        data (pd.DataFrame): Valid events only (inherited).
        semantics (EventSemantics): Event column mappings (inherited).
        rejected (pd.DataFrame): Bad rows with reasons (inherited).
        covariate_semantics (CovariateSemantics): Covariate column
            descriptions — types, levels, aggregation methods.

    Example:
        >>> ewc = EventsWithCovariates(df, event_semantics, covariate_semantics)
        >>> ewc.count_per_person()
        >>> ewc.filter_by_persons([101, 102])  # returns EventsWithCovariates

    Example (from YAMLs):
        >>> event_sem = EventSemantics.build_from_yaml("events.yaml")
        >>> cov_sem = CovariateSemantics.build_from_yaml("covariates.yaml")
        >>> ewc = EventsWithCovariates(df, event_sem, cov_sem)
    """

    _ERROR_PREFIX = "[EventsWithCovariates]"

    # C++ Style Attribute Declarations (in addition to Events attributes)
    # *** gotta add the ones from the parent class here
    covariate_semantics: CovariateSemantics

    def __init__(self, data: pd.DataFrame, semantics: EventSemantics,
                 covariate_semantics: CovariateSemantics):
        """Create events with covariate descriptions.

        First runs all Events validation (column existence, triage
        bad rows). Then validates covariate-specific requirements.

        Args:
            data: DataFrame of event records with covariate columns.
            semantics: Event column mappings.
            covariate_semantics: Covariate column descriptions.

        Raises:
            TypeError: If covariate_semantics is wrong type.
            ValueError: If covariate columns are missing, person_id
                doesn't match, person-level covariates aren't constant,
                or covariate columns have nulls.
        """
        # Events validation first (columns, triage, etc.)
        super().__init__(data, semantics)

        # Covariate validation
        self._validate_covariate_semantics(covariate_semantics)
        self.covariate_semantics = covariate_semantics
        self._validate_covariate_columns()
        self._validate_person_id_match()
        self._validate_covariate_types()
        self._validate_covariate_nulls()
        self._validate_person_level_constant()

    def _validate_covariate_semantics(self, covariate_semantics) -> None:
        """Check that covariate_semantics is the right type.

        Raises:
            TypeError: If not a CovariateSemantics instance.
        """
        if not isinstance(covariate_semantics, CovariateSemantics):
            raise TypeError(
                f"{self._ERROR_PREFIX} __init__: "
                f"covariate_semantics must be CovariateSemantics, "
                f"got {type(covariate_semantics).__name__}"
            )

    def _validate_covariate_columns(self) -> None:
        """Check that all covariate columns exist in the data.

        Raises:
            ValueError: If any covariate column is missing.
        """
        required = self.covariate_semantics.all_column_names()
        missing = [col for col in required if col not in self.data.columns]
        if missing:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"Covariate columns missing from data: {missing}. "
                f"Available columns: {list(self.data.columns)}"
            )

    def _validate_person_id_match(self) -> None:
        """Check that person_id_col matches between event and covariate semantics.

        Raises:
            ValueError: If person_id_col differs.
        """
        event_pid = self.semantics.person_id_col
        cov_pid = self.covariate_semantics.person_id_col
        if event_pid != cov_pid:
            raise ValueError(
                f"{self._ERROR_PREFIX} __init__: "
                f"person_id_col mismatch — EventSemantics uses '{event_pid}', "
                f"CovariateSemantics uses '{cov_pid}'"
            )

    def _validate_covariate_types(self) -> None:
        """Check that continuous columns are numeric and categorical are not.

        Raises:
            TypeError: If a continuous column is not numeric or a
                categorical column is numeric.
        """
        # Check continuous columns are numeric
        all_continuous = (
            self.covariate_semantics.person_level_continuous
            + [e["column"] for e in self.covariate_semantics.event_level_continuous]
        )
        for col in all_continuous:
            if not pd.api.types.is_numeric_dtype(self.data[col]):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Continuous covariate '{col}' must be numeric, "
                    f"got {self.data[col].dtype}"
                )

        # Check categorical columns are not float
        all_categorical = (
            self.covariate_semantics.person_level_categorical
            + [e["column"] for e in self.covariate_semantics.event_level_categorical]
        )
        for col in all_categorical:
            if pd.api.types.is_float_dtype(self.data[col]):
                raise TypeError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Categorical covariate '{col}' should not be float, "
                    f"got {self.data[col].dtype}. "
                    f"Consider casting to string or int."
                )

    def _validate_covariate_nulls(self) -> None:
        """Check that covariate columns have no nulls in valid data.

        Only checks self.data (already triaged), not rejected rows.

        Raises:
            ValueError: If any covariate column has nulls.
        """
        for col in self.covariate_semantics.all_column_names():
            null_count = self.data[col].isna().sum()
            if null_count > 0:
                raise ValueError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Covariate column '{col}' has {null_count} null values "
                    f"in valid data. Handle nulls before constructing."
                )

    def _validate_person_level_constant(self) -> None:
        """Check that person-level covariates are constant per person.

        A person-level covariate like 'age' must have the same value
        across all events for a given person.

        Raises:
            ValueError: If a person-level covariate varies within a person.
        """
        person_col = self.semantics.person_id_col
        person_level_cols = self.covariate_semantics.person_level_columns()

        for col in person_level_cols:
            nunique = self.data.groupby(person_col)[col].nunique()
            inconsistent = nunique[nunique > 1]
            if len(inconsistent) > 0:
                bad_persons = inconsistent.index.tolist()[:5]
                raise ValueError(
                    f"{self._ERROR_PREFIX} __init__: "
                    f"Person-level covariate '{col}' has different values "
                    f"across events for the same person. "
                    f"Inconsistent persons (first 5): {bad_persons}"
                )

    # ---- Override filter methods to return EventsWithCovariates ----

    def copy(self) -> "EventsWithCovariates":
        """Return a deep copy preserving covariate semantics.

        Returns:
            A new EventsWithCovariates with copied data.
        """
        return EventsWithCovariates(
            self.data.copy(), self.semantics, self.covariate_semantics
        )

    def filter_by_persons(self, person_ids: list) -> "EventsWithCovariates":
        """Filter to specific persons, preserving covariate semantics.

        Args:
            person_ids: List of person IDs to keep.

        Returns:
            A new EventsWithCovariates with only matching persons.
        """
        col = self.semantics.person_id_col
        filtered = self.data[self.data[col].isin(person_ids)]
        return EventsWithCovariates(
            filtered, self.semantics, self.covariate_semantics
        )

    def filter_by_dates(self, start=None, end=None) -> "EventsWithCovariates":
        """Filter to a date range, preserving covariate semantics.

        Args:
            start: Minimum start time (inclusive), or None.
            end: Maximum end time (inclusive), or None.

        Returns:
            A new EventsWithCovariates with only matching events.
        """
        filtered = self.data
        if start is not None:
            filtered = filtered[filtered[self.semantics.start_time_col] >= start]
        if end is not None:
            filtered = filtered[filtered[self.semantics.end_time_col] <= end]
        return EventsWithCovariates(
            filtered, self.semantics, self.covariate_semantics
        )

    def __repr__(self) -> str:
        n_covariates = len(self.covariate_semantics.all_column_names())
        return (
            f"EventsWithCovariates("
            f"{len(self)} rows, "
            f"person_col='{self.semantics.person_id_col}', "
            f"{n_covariates} covariates)"
        )
