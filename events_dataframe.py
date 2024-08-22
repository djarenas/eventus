"""events_dataframe.py"""
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class EventsDataframe():
    """
    Purpose: A class to handle events data with start and end dates.
    It holds a dataframe with a personid, start date, end date
    """
    def __init__(self, df, columns_dict):
        # Validate the input dataframe and columns
        self._check_input(df, columns_dict)

        # Ensure date columns are in the correct format
        df = self._ensure_date_column_type(df, columns_dict)

        # Fix any invalid dates in the dataframe
        df = self._attempt_to_fix_invalid_dates(df, columns_dict)

        # Sort by person and date
        df = df.sort_values(by=[columns_dict['personid'], columns_dict['start']])

        # Assign attributes
        self.df = df
        self.columns_dict = columns_dict

    @staticmethod
    def _check_input(events_df, columns_dict):
        """ Validate input variables for the constructor of EventsDataFrame class"""
        if not isinstance(events_df, pd.DataFrame):
            raise ValueError("Input 'events_df' must be a pandas DataFrame.")
        if not isinstance(columns_dict, dict):
            raise ValueError("Input 'columns_dict' must be a dictionary.")

        # Ensure that the input has the required keys for the dictionary, and those values,
        # are found as column nnames of the input dataframe
        required_keys = columns_dict.keys()
        for key in required_keys:
            if key not in columns_dict:
                raise ValueError(f"Input 'columns_dict' must contain '{key}' key.")
            if columns_dict[key] not in events_df.columns:
                raise ValueError(f"DataFrame must contain '{columns_dict[key]}' column.")

        return True

    @staticmethod
    def _ensure_date_column_type(events_df, columns_dict, date_format=None):
        """
        Ensure the date columns are in datetime format. Raises a ValueError if
        conversion fails for any column.
        """
        for col in [columns_dict['start'], columns_dict['end']]:
            try:
                events_df[col] = pd.to_datetime(events_df[col], format=date_format, errors='coerce')
            except ValueError as e:
                raise ValueError(f"Error converting column '{col}' to datetime: {e}") from e
        
        return events_df

    @staticmethod
    def _attempt_to_fix_invalid_dates(events_df, columns_dict):
        """
        Fix invalid start and end dates:
        1. Remove rows where both start and end dates are invalid.
        2. Replace invalid end dates with the start date if start date is valid.
        3. Replace invalid start dates with the end date if end date is valid.
        """
        start_col = columns_dict['start']
        end_col = columns_dict['end']

        # Find rows where both start and end dates are invalid (NaT)
        invalid_both_mask = events_df[start_col].isna() & events_df[end_col].isna()
        num_removed = invalid_both_mask.sum()
        events_df = events_df[~invalid_both_mask]
        print(f"Removed {num_removed} rows where both start and end dates were invalid.")

        # Find rows where start is valid but end is invalid, and set end to start
        invalid_end_mask = events_df[start_col].notna() & events_df[end_col].isna()
        num_fixed_end = invalid_end_mask.sum()
        events_df.loc[invalid_end_mask, end_col] = events_df.loc[invalid_end_mask, start_col]
        print(f"Replaced invalid end dates with start dates for {num_fixed_end} rows.")

        # Find rows where end is valid but start is invalid, and set start to end
        invalid_start_mask = events_df[end_col].notna() & events_df[start_col].isna()
        num_fixed_start = invalid_start_mask.sum()
        events_df.loc[invalid_start_mask, start_col] = events_df.loc[invalid_start_mask, end_col]
        print(f"Replaced invalid start dates with end dates for {num_fixed_start} rows.")

        return events_df

    def deepcopy(self):
        """Prevent changes to original by returning a deep copy."""
        return copy.deepcopy(self)

    def print_breakdown(self):
        """Simple method to count the number of events and unique people."""
        print("Encounters: ", len(self.df), ". People: ", len(self.df['personid'].unique()))

    def keep_occurrences_within_period(self, period_dict):
        """
        Purpose: Keep events within a time range. Filters rows such that both
        the start and end dates are within the specified range.
        """
        # Validate input period_dict
        if not isinstance(period_dict, dict):
            raise ValueError("Input 'period_dict' must be a dictionary.")
        if 'start_period' not in period_dict or 'end_period' not in period_dict:
            raise ValueError("Input 'period_dict' must contain 'start_period' and 'end_period' keys.")

        # Convert start and end periods to datetime
        period_dict['start_period'] = pd.to_datetime(period_dict['start_period'], errors='raise')
        period_dict['end_period'] = pd.to_datetime(period_dict['end_period'], errors='raise')

        # Ensure the start period is less than or equal to the end period
        if period_dict['start_period'] > period_dict['end_period']:
            raise ValueError("Start period must be earlier than or equal to end period.")

        # Filter rows where start and end dates are within the specified period
        filtered_df = self.df.loc[
            (self.df[self.columns_dict['start']] >= period_dict['start_period']) &
            (self.df[self.columns_dict['end']] <= period_dict['end_period'])
        ]

        # Explicitly make a copy to avoid the SettingWithCopyWarning
        self.df = filtered_df.copy()

    def fix_zero_duration_intervals(self, hours=24):
        """
        Fix zero-duration intervals in a DataFrame by adding a specified number of hours
        to the 'end' column when 'start' and 'end' times are the same.
        
        Parameters:
        - hours: Number of hours to add to the 'end' column (default is 24 hours).
        """
        # Get a copy of the original dataframe
        events_df = self.df.copy()

        start_col = self.columns_dict['start']
        end_col = self.columns_dict['end']

        # Create a mask for rows where start and end times are the same
        zero_duration_mask = events_df[start_col] == events_df[end_col]

        # Count the number of affected rows
        count = zero_duration_mask.sum()

        # Add the specified number of hours to the 'end' column for those rows
        events_df.loc[zero_duration_mask, end_col] += pd.Timedelta(hours=hours)
        
        print(f"Number of zero-duration intervals fixed: {count}")

        # Update object's dataframe
        self.df = events_df

    def calc_duration_hours(self, output_columnname):
        """
        Calculate duration in hours
        """
        start_column = self.columns_dict['start']
        end_column = self.columns_dict['end']

        # Convert start and end columns to datetime
        self.df[start_column] = pd.to_datetime(self.df[start_column])
        self.df[end_column] = pd.to_datetime(self.df[end_column])

        # Update dataframe attribute with a new column and with the name of the duration
        self.df[output_columnname] = np.ceil(((self.df[end_column] - self.df[start_column]).dt.total_seconds()) / 3600)

    def plot_duration_histogram(self, duration_column, bintype = 'hours', filename = None):
        """
        This method can only be used after the constructor
        Histogram of event duration
        """
        df = self.df.copy(deep=True)
        # Ensure 'ed_duration' contains only valid, finite numbers
        df = df[pd.notnull(df[duration_column]) & np.isfinite(df[duration_column])]

        # Define custom bin edges and labels
        if bintype == 'hours':
            bins = [-np.inf, 0, 12, 24, 36, 48, np.inf]
            labels = ['0', '1-12', '13-24', '25-36', '37-48', '49+']
            xlabel = 'Duration (hrs)'
        elif bintype == 'days':
            bins = [-np.inf, 0, 24, 24*2, 24*3, 24*4, 24*5, 24*6, 24*7, 24*8, np.inf]
            labels = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9+']
            xlabel = 'Duration (days rounded up)'
        else:
            raise ValueError("Error in plot_duration_histogram. Bintype must be either hours or days")

        # Use pd.cut() to categorize the data into bins
        df['category'] = pd.cut(df[duration_column], bins=bins, labels=labels)

        # Count the occurrences in each category
        category_counts = df['category'].value_counts().reindex(labels)

        # Plotting
        plt.bar(category_counts.index, category_counts.values, edgecolor='black')
        plt.xlabel(xlabel)
        plt.ylabel('Frequency')
        plt.title('Histogram of Duration')
        plt.xticks(rotation=45)  # Rotate labels to improve readability if necessary

        if filename is not None:
            plt.savefig(filename, dpi = 400)
        else:
            plt.show()
        plt.close()
