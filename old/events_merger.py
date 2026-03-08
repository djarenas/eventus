"""events_merger.py"""
import pandas as pd
from Python_Events_Classes.events_dataframe import EventsDataframe
import Python_Events_Classes.intervals_functions as interval

class EventsMerger:
    def __init__(self, columns_dict):
        self.columns_dict = columns_dict
        self.error_message = "Error in EventsMerger"

    def merge_overlapping_events(self, input_df, additional_distinguishers = None):
        """
        Purpose: Merge overlapping events into one. This is a computationally heavy
        algorithm. Handled by reference. 
        Additional columns (those besides personid, start, end) are aggregated by
        unique values.
        Distinguishers:
        By default, events are overlapped as long as they have the same personid. 
        The distinguishing column is therefore the personid by default. Additional
        column names, that must be the same in order to merge overlapping events,
        can be inputted as 
        """

        print("In EventsDataFrame. merge_overlapping_events()")

        # Make a copy of original dataframe
        df = input_df.copy(deep=True)

        # Group by Distinguishers
        # Default
        if additional_distinguishers is None:
            grouped = df.groupby(self.columns_dict['personid'])
        else:
            self._check_distinguishers_input(df, additional_distinguishers)
            distinguisher_list = [self.columns_dict['personid']] + additional_distinguishers
            grouped = df.groupby(distinguisher_list)

        # Apply custom function to merge overlaps to every grouping-by-person
        # Reset index
        result = grouped.apply(lambda group: \
                    interval.merge_overlapping_intervals_with_aggregation(group, self.columns_dict))
        result = result.reset_index(drop=True)

        # Ensure you are saving date columns as datetime
        result[self.columns_dict['start']] = pd.to_datetime(result[self.columns_dict['start']] )
        result[self.columns_dict['end']] = pd.to_datetime(result[self.columns_dict['end']] )

        # Sort the results by personid and start date column
        result = result.sort_values(by = ['personid', self.columns_dict['start']], \
                                    ascending = [True, True])

        return result

    def _check_distinguishers_input(self, df, variable):
        error_message = self.error_message + "error in _check_distinguishers_input"
        # 1. Check if the variable is a list
        if not isinstance(variable, list):
            raise ValueError(error_message + "The distinghishers variable is not a list.")
        else:
            # 2. Check if all elements in the list are contained in the column names of df
            if not all(item in df.columns for item in variable):
                raise ValueError(error_message + \
                                    "Not all elements in the list are column names of df.")

    def _merge_consecutive_rows(self, group, columns_dict):
        start = columns_dict['start']
        end = columns_dict['end']
        personid_column = columns_dict['personid']
        exclude_columns = [personid_column, start, end]

        # Ensure the group is sorted by 'start' date
        group = group.sort_values(by=start)

        # Placeholder for new rows
        new_rows = []

        # Temporary variables for merging rows
        temp_row = None
        for _, row in group.iterrows():
            if temp_row is None:
                temp_row = row.copy()
            else:
                # Check if current row starts within one day after temp_row ends
                if (row[start] - temp_row[end]) <= pd.Timedelta(days=1):
                    # Merge rows: Update 'end' and aggregate other columns
                    temp_row[end] = row[end]
                    for col in group.columns:
                        if col not in exclude_columns:
                            # Ensure temp_row[col] and row[col] are lists
                            if not isinstance(temp_row[col], list):
                                temp_row[col] = [temp_row[col]] if pd.notnull(temp_row[col]) else []
                            if not isinstance(row[col], list):
                                row_col_as_list = [row[col]] if pd.notnull(row[col]) else []
                            else:
                                row_col_as_list = row[col]
                            # Append items from the current row's list to temp_row's list
                            temp_row[col].extend(row_col_as_list)
                else:
                    # Append temp_row to new_rows and start a new merge with current row
                    new_rows.append(temp_row)
                    temp_row = row.copy()
        # Append the last temp_row if exists
        if temp_row is not None:
            new_rows.append(temp_row)
        
        return pd.DataFrame(new_rows)

    def merge_consecutive_events(self, input_df, additional_distinguishers = None):
        """
        Purpose: Find events that begin within one day of a previous event and merge to the previous event.
        Handled by reference. Additional columns (those besides personid, start, end) are aggregated by
        unique values.
        """
        df = input_df.copy(deep = True)
        if additional_distinguishers is None:
            grouped = df.groupby(self.columns_dict['personid'])
        else:
            self._check_distinguishers_input(df, additional_distinguishers)
            distinguisher_list = [self.columns_dict['personid']] + additional_distinguishers
            grouped = df.groupby(distinguisher_list)

        result = grouped.apply(lambda group: self._merge_consecutive_rows(group, self.columns_dict))
        result = result.reset_index(drop=True)

        print("After merging consecutive events: ", len(result))

        return result
