import numpy as np
import pandas as pd

from .event_semantics import EventSemantics
from .events_utils import merge_overlapping_events

class Events:
    """A collection of events that happened to people.

    Each event has an entity (i.e. person, company name,...), a start time, and an
    end time. The semantics object describes which columns hold which information.

    Events with bad data (nulls, bad time ordering) are separated
    into the rejected attribute at construction time. Everything
    in .data is guaranteed to be structurally valid.

    Attributes:
        data (pd.DataFrame): Valid events only.
        semantics (EventSemantics): Column mappings.
        rejected (pd.DataFrame): Rows with bad data,
            includes '_rejection_reason' column.
    """
    _ERROR_PREFIX = "[Events] Error"

    # Attribute Declarations
    data: pd.DataFrame              # valid events only
    semantics: EventSemantics
    rejected: pd.DataFrame          # has extra '_rejection_reason' column

    def __init__(self, data_input: pd.DataFrame, semantics: EventSemantics):
        # Prevent changes to original
        data = data_input.copy()

        # Validate inputs and ensure right type for date columns
        self._validate_input(data, semantics)
        self._validate_columns_exist(data, semantics)

        data = self._ensure_date_columns_type(data, semantics)
        # Initialize the semantics attribute
        self.semantics = semantics
        # Triage into good rows and bad rows -> Save into attributes
        self.data, self.rejected = self._triage(data.copy())

        self._report_rejected()

    # Public Methods

    def copy(self) -> "Events":
        return Events(self.data.copy(), self.semantics)

    def filter_by_entitys(self, entity_ids: list) -> "Events":
        col = self.semantics.entity_id_col
        filtered = self.data[self.data[col].isin(entity_ids)]
        return Events(filtered, self.semantics)

    def filter_by_dates(self, start=None, end=None) -> "Events":
        filtered = self.data
        if start is not None:
            filtered = filtered[filtered[self.semantics.start_time_col] >= start]
        if end is not None:
            filtered = filtered[filtered[self.semantics.end_time_col] <= end]
        return Events(filtered, self.semantics)

    def merge_overlapping_events(self, meaningful_gap: int = 0) -> "Events":
        merged_df = merge_overlapping_events(
            events_df=self.data,
            semantics=self.semantics,
            meaningful_gap = meaningful_gap
        )
        return Events(merged_df, self.semantics)

    def count_per_entity(self) -> np.ndarray:
        counts = self.data.groupby(self.semantics.entity_id_col).size()
        return counts.to_numpy()

    # Helper methods

    def _validate_input(self, data:pd.DataFrame, semantics: EventSemantics):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"{self._ERROR_PREFIX} in constructor: data must be a pandas dataframe")
        if not isinstance(semantics, EventSemantics):
            raise TypeError(f"{self._ERROR_PREFIX} in constructor: semantics must be a EventSemantics object")

    def _validate_columns_exist(self, data:pd.DataFrame, semantics: EventSemantics):
        """Raises if required columns are missing — structural problem."""        
        required = [
            semantics.entity_id_col,
            semantics.start_time_col,
            semantics.end_time_col,
        ]
        if semantics.event_id_col:
            required.append(semantics.event_id_col)
        if semantics.event_type_col:
            required.append(semantics.event_type_col)
        for col in semantics.metadata_cols:
            required.append(col)

        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"Missing columns in dataframe: {missing}")

    def _ensure_date_columns_type(self, data: pd.DataFrame, semantics: EventSemantics) -> pd.DataFrame:
        data[semantics.start_time_col] = pd.to_datetime(data[semantics.start_time_col], errors='coerce')
        data[semantics.end_time_col]   = pd.to_datetime(data[semantics.end_time_col],   errors='coerce') 
        return data

    def _triage(self, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Separate good rows from bad, tagging rejections with reasons."""
        reasons = pd.Series("", index=data.index)

        critical = [
            self.semantics.entity_id_col,
            self.semantics.start_time_col,
            self.semantics.end_time_col,
        ]
        for col in critical:
            mask = data[col].isna()
            reasons[mask] += f"null_{col}; "

        for col in [self.semantics.start_time_col, self.semantics.end_time_col]:
            if not pd.api.types.is_datetime64_any_dtype(data[col]):
                raise TypeError(
                    f"Column '{col}' must be datetime, got {data[col].dtype}. "
                    f"Convert before constructing Events."
                )

        start = data[self.semantics.start_time_col]
        end = data[self.semantics.end_time_col]
        bad_order = start > end
        reasons[bad_order] += "start_after_end; "

        is_rejected = reasons.str.len() > 0
        rejected = data[is_rejected].copy()
        rejected["_rejection_reason"] = reasons[is_rejected].str.rstrip("; ")
        good = data[~is_rejected].copy()

        return good, rejected

    def _report_rejected(self):
        if len(self.rejected) == 0:
            return
        total = len(self.data) + len(self.rejected)
        print(
            f"Warning: {len(self.rejected)}/{total} rows rejected. "
            f"Reasons: {self.rejected['_rejection_reason'].value_counts().to_dict()}"
        )

    # Special methods

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"Events({len(self)} rows, entity_col='{self.semantics.entity_id_col}')"