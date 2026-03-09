class Events:
    """A collection of events that happened to people.

    Each event has a person, an event ID, a start time, and an
    end time. The semantics object describes which columns hold
    which information.

    Events with bad data (nulls, bad time ordering) are separated
    into the rejected attribute at construction time. Everything
    in .data is guaranteed to be structurally valid.

    Attributes:
        data (pd.DataFrame): Valid events only.
        semantics (EventSemantics): Column mappings.
        rejected (pd.DataFrame): Rows with bad data,
            includes '_rejection_reason' column.
    """

    # Attribute Declarations
    data: pd.DataFrame              # valid events only
    semantics: EventSemantics
    rejected: pd.DataFrame          # has extra '_rejection_reason' column

    def __init__(self, data: pd.DataFrame, semantics: EventSemantics):
        self.semantics = semantics
        self._validate_columns_exist(data)
        self.data, self.rejected = self._triage(data.copy())
        self._report_rejected()

    def _validate_columns_exist(self, data: pd.DataFrame):
        """Raises if required columns are missing — structural problem."""
        required = [
            self.semantics.person_id_col,
            self.semantics.event_id_col,
            self.semantics.start_time_col,
            self.semantics.end_time_col,
        ]
        if self.semantics.event_type_col:
            required.append(self.semantics.event_type_col)
        for col in self.semantics.metadata_cols:
            required.append(col)

        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"Missing columns in dataframe: {missing}")

    def _triage(self, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Separate good rows from bad, tagging rejections with reasons."""
        reasons = pd.Series("", index=data.index)

        critical = [
            self.semantics.person_id_col,
            self.semantics.event_id_col,
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

    def copy(self) -> "Events":
        return Events(self.data.copy(), self.semantics)

    def filter_by_persons(self, person_ids: list) -> "Events":
        col = self.semantics.person_id_col
        filtered = self.data[self.data[col].isin(person_ids)]
        return Events(filtered, self.semantics)

    def filter_by_dates(self, start=None, end=None) -> "Events":
        filtered = self.data
        if start is not None:
            filtered = filtered[filtered[self.semantics.start_time_col] >= start]
        if end is not None:
            filtered = filtered[filtered[self.semantics.end_time_col] <= end]
        return Events(filtered, self.semantics)

    def count_per_person(self) -> pd.Series:
        counts = self.data.groupby(self.semantics.person_id_col).size()
        counts.name = "event_count"
        return counts

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"Events({len(self)} rows, person_col='{self.semantics.person_id_col}')"