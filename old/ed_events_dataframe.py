"""ed_events_dataframe.py"""
import pandas as pd
from .events_dataframe import EventsDataframe

class EDEventsDataframe(EventsDataframe):
    """
    A child class of EventsDataFrame that specializes in ED events.
    As an input, it uses an EventsDataFrame object which has already gone through some data cleaning and
    standardization. It then fixes events with no duration by adding 23 hours to the end date. It also
    merges ED events that occur in the same day.
    """
    def __init__(self, events_dataframe):
        self.error_message = "Error in EDEventsDataframe constructor. "
        # Check input
        if not isinstance(events_dataframe, EventsDataframe):
            raise ValueError(self.error_message + \
                             "events_dataframe input must be a EventsDataFrame object")

        # Use the parent constructor
        # This parent standardizes into an event. Performs checks, cleans, etc...
        # See documentation for the parent class
        super().__init__(events_dataframe.df, events_dataframe.columns_dict)

        # The following modifications is necessary to have a proper conceptual EDEventsDataframe
        # Merge events that have the same start date and same datasource
        # Aggregates the other columns so that you do not lose information
        self.merge_same_start_day(additional_distinguishers = ['datasource'])

        # Calculate duration 
        self.calc_duration_hours('ed_duration')

    def _aggregate_rows_with_same_start_day(self, group, columns_dict):
        """
        Aggregate rows that occur on the same day for the same person and/or additional distinguishers.

        For rows within a group that have the same 'start' date, it combines/aggregates other columns into lists,
        ensuring that no information is lost. The 'end' date for the aggregated event will be the latest among all
        merged rows. The 'personid', 'start', and 'end' columns are excluded from aggregation.

        Parameters:
        - group (pd.DataFrame): A group of rows belonging to the same person and/or additional distinguishers.
        - columns_dict (dict): Dictionary mapping columns, including 'personid', 'start', and 'end'.

        Returns:
        - pd.DataFrame: A DataFrame with aggregated rows for the same start day.

        Aggregation details:
        - For list columns, the elements of the lists are concatenated.
        - For other columns, values are appended to lists.
        - The 'end' column takes the latest end time within the group.
        """
        # Ensure the group is sorted by 'start' date for sequential comparison
        group = group.sort_values(by=columns_dict['start'])

        aggregated_rows = []
        exclude_columns = [columns_dict['personid'], columns_dict['start'], columns_dict['end']]

        aggregated_data = {}

        for _, row in group.iterrows():
            if not aggregated_data:  # Initialize aggregated_data with the first row, taking care of None
                for col in group.columns:
                    if col in exclude_columns:
                        aggregated_data[col] = row[col]
                    else:
                        # Initialize as list but exclude None values
                        aggregated_data[col] = [] if row[col] is None else ([row[col]] if not isinstance(row[col], list) else row[col])
            else:
                if row[columns_dict['start']].date() == aggregated_data[columns_dict['start']].date():
                    for col in group.columns:
                        if col not in exclude_columns:
                            # Avoid appending or extending None values
                            if isinstance(row[col], list):
                                # Extend only with non-None items
                                aggregated_data[col].extend([item for item in row[col] if item is not None])
                            elif row[col] is not None:
                                aggregated_data[col].append(row[col])
                    # Update 'end' date to the latest
                    aggregated_data[columns_dict['end']] = max(aggregated_data[columns_dict['end']], row[columns_dict['end']])
                else:
                    # Different day, finalize current aggregation and reset
                    aggregated_rows.append(aggregated_data.copy())
                    aggregated_data.clear()
                    # Initialize for the new row, excluding None
                    for col in group.columns:
                        if col in exclude_columns:
                            aggregated_data[col] = row[col]
                        else:
                            aggregated_data[col] = [] if row[col] is None else ([row[col]] if not isinstance(row[col], list) else row[col])

        # Don't forget the last aggregation
        if aggregated_data:
            aggregated_rows.append(aggregated_data)

        return pd.DataFrame(aggregated_rows)

    def merge_same_start_day(self, additional_distinguishers = None):
        """
        Merge events with the same start date into a single event per person (and optional additional distinguishers).

        For each person (or set of distinguishers), this method finds events that start on the same day
        and merges them into one event. It aggregates data from other columns to ensure that no information is lost.

        Parameters:
        - additional_distinguishers (list): A list of additional columns that must also match for events to be merged.
                                            These can be things like 'datasource' or other relevant columns.

        Raises:
        - ValueError: If any of the additional distinguishers are not columns in the dataframe.

        Notes:
        - After merging, the 'end' date for each merged event will be the latest end date for any event on that day.
        - Other columns will have their values aggregated into lists.
        """  
        df = self.df.copy()
        if additional_distinguishers:
            distinguishers_list = [self.columns_dict['personid']] + additional_distinguishers
            for i in distinguishers_list:
                if i not in self.df.columns:
                    raise ValueError (f"Error in merge_same_start_day. {i} must be a column")
        else:
            distinguishers_list = [self.columns_dict['personid']]

        distinguisher_grouped = df.groupby(distinguishers_list)
        result = distinguisher_grouped.apply(lambda group: \
                    self._aggregate_rows_with_same_start_day(group, self.columns_dict))
        result = result.reset_index(drop=True)

        # Update the dataframe of the object
        self.df = result
