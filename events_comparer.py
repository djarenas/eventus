"""events_comparer.py"""
import numpy as np
from .track_time import track_time
from Python_Events_Classes.events_dataframe import EventsDataframe
import Python_Events_Classes.intervals_functions as interval

class EventsComparer():
    """
    Functions for comparing EventsDataframe objects to one another.
    """
    def __init__(self):
        pass

    def _check_two_eventsdataframe(self, x_events_dataframe, y_events_dataframe):
        if not isinstance(x_events_dataframe, EventsDataframe) \
        or not isinstance(y_events_dataframe, EventsDataframe):
            raise ValueError ("Error in  does_x_begin_within_y, make sure inputs \
                                  are events_dataframe objects")

        # Get the dataframes
        df_x = x_events_dataframe.df
        df_y = y_events_dataframe.df
        # Make sure the two event_dataframe objects have the same column names depicting start, end
        if x_events_dataframe.columns_dict != y_events_dataframe.columns_dict:
            raise ValueError ("Error in  does_x_begin_within_y, make sure inputs \
                                  columns_dict and column names must be the same for both objects")
        
        # Check that the dataframes of the objects are in the right format
        # This may be obsolete since the constructors for these objects should take care of this
        try:
            interval.check_day_interval_dataframes(df_x, df_y, x_events_dataframe.columns_dict)
        except ValueError as e:
            print(f"Error in does_x_begin_within_ys: {e}")

    @track_time
    def do_xs_begin_within_ys(self, x_events_dataframe, y_events_dataframe, \
                               outcome_column = "begins within ys"):
        """
        Purpose: For every person, for all their events in dataframe X...
        It checks the start-date, it then checks if dataframe Y 
        has a row with the same person and an interval that contains the start-date.
        For example, check if ED visits in X fall within any of the inpatient visits in Y
        Returns a object X with a new boolean column
        """
        # Check inputs
        self._check_two_eventsdataframe(x_events_dataframe, y_events_dataframe)

        # Get the dataframes
        df_x = x_events_dataframe.df
        df_y = y_events_dataframe.df

        # This interval function, looks at person by person...
        # For every event in X, it checks if its start-day falls within the duration of any event in Y
        df_x = interval.check_if_days_within_intervals(df_x, df_y, \
                                                 x_events_dataframe.columns_dict, outcome_column)

        x_events_dataframe.df = df_x

        return x_events_dataframe

    @track_time
    def do_xs_contain_ys(self, x_events_dataframe, y_events_dataframe, \
                               outcome_column = "contains_ys"):
        """
        Purpose: For every person, for all their events in dataframe X...
        It checks checks if dataframe Y has a row with the same person and a start-date within that event.
        For example, check if inpatient visits in X contain any ED visits in Y for the same person.
        Returns a object X with a new boolean column
        """
        # Check inputs
        self._check_two_eventsdataframe(x_events_dataframe, y_events_dataframe)

        # Get the dataframes
        df_x = x_events_dataframe.df
        df_y = y_events_dataframe.df

        # Apply interval function
        df_x = interval.check_if_intervals_contain_days(df_x, df_y, \
                                                 x_events_dataframe.columns_dict, outcome_column)
        x_events_dataframe.df = df_x

        return x_events_dataframe

    @track_time
    def check_overlap(self, x_events_dataframe, y_events_dataframe, outcome_column= 'intervals_overlap',
                      additional_distinguishers = None):
        """
        """
        # Check inputs
        self._check_two_eventsdataframe(x_events_dataframe, y_events_dataframe)

        x_events_dataframe = x_events_dataframe.deepcopy()

        # Get the dataframes
        df_x = x_events_dataframe.df
        df_y = y_events_dataframe.df

        # Apply interval function
        df_x = interval.check_if_intervals_overlap(df_x, df_y, \
                                                 x_events_dataframe.columns_dict, outcome_column, additional_distinguishers)
        
        x_events_dataframe.df = df_x

        return x_events_dataframe

    def filter_by_boolean(self, events_dataframe, boolean_variable, choose = True):
        """
        Return the object after 
        """
        new_events_dataframe = events_dataframe.deepcopy()
        df = new_events_dataframe.df

        if choose:
            df = df.loc[df[boolean_variable]]
        else:
            df = df.loc[~df[boolean_variable]]

        new_events_dataframe.df = df

        return new_events_dataframe

    @track_time
    def merge_unique_values(self, events_a, events_b, columns, id_col='personid', start_col='admitdate', \
                            end_col='dischargedate', flag_column = 'flagged'):
        """
        """ 
        result = events_a.deepcopy()
        df_a = events_a.df
        df_b = events_b.df

        # Ensure all specified columns are lists if not already
        for col in columns:
            for df in [df_a, df_b]:
                df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])

        # Sort both dataframes by start and end
        df_a.sort_values(by=[id_col, start_col, end_col], inplace = True)
        df_b.sort_values(by=[id_col, start_col, end_col], inplace = True)

        # Create a new column that keeps track of merging
        df_a[flag_column] = np.full(len(df_a), False, dtype = bool)

        # Iterate over DataFrame A by index to modify it directly
        for idx_a, row_a in df_a.iterrows():
            # Filter DataFrame B for the same id_col. Make sure the filtering did not mess up the sort.
            filtered_b = df_b[df_b[id_col] == row_a[id_col]].copy(deep = True)
            filtered_b.sort_values(by=[start_col, end_col], inplace = True)
            
            # Check for overlapping dates
            for _, row_b in filtered_b.iterrows():
                if (row_a[start_col] <= row_b[end_col]) and (row_a[end_col] >= row_b[start_col]):
                    # Merge unique values for each specified column
                    for col in columns:
                        current_values = set(row_a[col])
                        additional_values = set(row_b[col])
                        df_a.at[idx_a, col] = list(current_values.union(additional_values))
                        # Flag that there was a merge
                        df_a.at[idx_a, flag_column] = True
                # Avoid unnecessary steps
                if (row_b[start_col] > row_a[end_col]):
                    break

            df_a.sort_values(by=[id_col, start_col, end_col], inplace = True)

            result.df = df_a
        
        return result