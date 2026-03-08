"""Functions to deal with intervals"""
import itertools
import numpy as np
import pandas as pd

def merge_overlapping_intervals_with_aggregation(group, cnames_dict):
    """
    Merge overlapping intervals within a DataFrame group, assuming rows have been grouped by 'personid',
    and aggregate additional columns by keeping unique values only.
    
    Parameters:
    - group: pd.DataFrame, the DataFrame containing the intervals.
    - cnames_dict: dict, a dictionary mapping 'start' and 'end' to the corresponding column names in 'group'.
    """
    # Ensure 'start' and 'end' are in date format (without time)
    group[cnames_dict['start']] = pd.to_datetime(group[cnames_dict['start']]).dt.date
    group[cnames_dict['end']] = pd.to_datetime(group[cnames_dict['end']]).dt.date

    # Sort the group DataFrame by 'start' column
    sorted_group = group.sort_values(by=cnames_dict['start']).reset_index(drop=True)

    # Initialize merged_intervals with the first interval and additional column aggregation
    additional_cols = [col for col in group.columns if col not in [cnames_dict['start'], cnames_dict['end'], 'personid']]
    first_row_aggregation = {col: {sorted_group.iloc[0][col]} for col in additional_cols}  # Use set for uniqueness

    merged_intervals = [{'personid': sorted_group.iloc[0]['personid'], 
                         cnames_dict['start']: sorted_group.iloc[0][cnames_dict['start']],
                         cnames_dict['end']: sorted_group.iloc[0][cnames_dict['end']],
                         **first_row_aggregation}]

    for _, row in sorted_group.iloc[1:].iterrows():
        last_interval = merged_intervals[-1]
        if row[cnames_dict['start']] <= last_interval[cnames_dict['end']]:
            # Update the end date if the current interval extends it
            last_interval[cnames_dict['end']] = max(last_interval[cnames_dict['end']], row[cnames_dict['end']])
            # Aggregate additional columns by adding to the set for uniqueness
            for col in additional_cols:
                if row[col] is not None:
                    last_interval[col].add(row[col])
        else:
            # If no overlap, start a new interval and aggregate additional columns using set for uniqueness
            new_interval_aggregation = {col: {row[col]} for col in additional_cols}
            new_interval = {'personid': row['personid'], 
                            cnames_dict['start']: row[cnames_dict['start']], 
                            cnames_dict['end']: row[cnames_dict['end']],
                            **new_interval_aggregation}
            merged_intervals.append(new_interval)

    # Finalize the unique value aggregation of the additional columns
    # Convert sets to lists (or arrays) ensuring None is not included
    for interval in merged_intervals:
        for col in additional_cols:
            interval[col] = [value for value in interval[col] if value is not None]

    return pd.DataFrame(merged_intervals)

def check_day_interval_dataframes(day_df, interval_df, dates_column_dict):
    """
    Check if the provided dataframes meet the expected structure for further processing.

    Parameters:
    day_df (pd.DataFrame): DataFrame to be checked.
    interval_df (pd.DataFrame): Another DataFrame to be checked.
    dates_column_dict (dict): Dictionary specifying the column names for 'start' and 'end' dates.

    Raises:
    ValueError: If the dataframes do not meet the expected structure or 
    required columns are missing.
    """
    import pandas as pd

    # Check that day_df and interval_df are dataframes
    if not isinstance(day_df, pd.DataFrame) or not isinstance(interval_df, pd.DataFrame):
        raise ValueError("Both 'day_df' and 'interval_df' must be pandas DataFrames.")

    # Check for the presence of 'personid' column in both dataframes
    if 'personid' not in day_df.columns or 'personid' not in interval_df.columns:
        raise ValueError("Both 'day_df' and 'interval_df' must contain a 'personid' column.")

    # Function to check the date type of a column
    def check_date_column(df, column_name):
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' is missing in the DataFrame.")
        if not pd.api.types.is_datetime64_any_dtype(df[column_name]):
            actual_type = df[column_name].dtype
            raise ValueError(f"The column '{column_name}' must be of datetime type, but its actual type is {actual_type}.")

    # Check the date columns in day_df
    check_date_column(day_df, dates_column_dict['start'])

    # Check the date columns in interval_df
    check_date_column(interval_df, dates_column_dict['start'])
    check_date_column(interval_df, dates_column_dict['end'])

    return

def check_if_intervals_contain_days(interval_df, day_df, dates_column_dict, outcome_column):
    """
    Check if each entry in the 'day_df' dataframe falls within any of the intervals in the
    'interval_df' dataframe for the same 'personid' and calculates days off.
    This function combines both containment check and days off calculation to minimize iterations.
    """
    # Check inputs - Ensure this function validates the dataframes and column names as needed
    # check_day_interval_dataframes(day_df, interval_df, dates_column_dict)

    def operate_on_each_row(interval_df_row):
        matching_entries = day_df[day_df['personid'] == interval_df_row['personid']]
        days_ahead_list = []
        # Default value. In case there are no entries to even check against
        contains = False

        for _, entry in matching_entries.iterrows():
            # Resets contains, in case a previous entry was found to match
            contains = False
            interval_start_date = interval_df_row[dates_column_dict['start']].date()
            interval_end_date = interval_df_row[dates_column_dict['end']].date()
            entry_start_date = entry[dates_column_dict['start']].date()
            entry_end_date = entry[dates_column_dict['end']].date()

            # Check for containment
            if (interval_start_date <= entry_start_date <= interval_end_date) \
                or (interval_start_date <= entry_end_date <= interval_end_date):
                contains = True
                days_ahead = 0
                days_ahead_list.append(days_ahead)
                # Break the for loop
                break

            # Since this entry was contained within, calculate days ahead
            # Entry is after interval
            a = int((interval_start_date - entry_end_date).days)
            # Entry is before interval
            b = int((interval_start_date - entry_start_date).days)
            days_ahead = min(a,b, key = abs)
            days_ahead_list.append(days_ahead)

        # Process days off list to find minimum days off
        min_days_ahead = min(days_ahead_list, key = abs) if days_ahead_list else np.nan

        return contains, min_days_ahead

    # Apply the combined operation to each row in interval_df and split the results
    results = interval_df.apply(operate_on_each_row, axis=1)
    interval_df[outcome_column] = results.apply(lambda x: x[0])
    interval_df[outcome_column + "_days_ahead"] = results.apply(lambda x: x[1])

    interval_df.sort_values(by=['personid', 'admitdate', 'dischargedate'], inplace = True)

    return interval_df

def check_if_days_within_intervals(day_df, interval_df, dates_column_dict, outcome_column):
    """
    Check if each entry in the 'day_df' dataframe falls within any of the 
    intervals in the 'interval_df' dataframe for the same 'personid'.
    Compares days and does not use the times.
    """
    # Check inputs
    check_day_interval_dataframes(day_df, interval_df, dates_column_dict)

    # This function will be applied to each row of day_df
    def is_within_interval(day_df_row):
        person_intervals = interval_df[interval_df['personid'] == day_df_row['personid']]

        for _, interval in person_intervals.iterrows():
            # Convert individual datetime objects to date for comparison
            interval_start_date = interval[dates_column_dict['start']].date()
            interval_end_date = interval[dates_column_dict['end']].date()
            day_date = day_df_row[dates_column_dict['start']].date()

            if interval_start_date <= day_date <= interval_end_date:
                return True
        return False

    # Apply the function to each row in day_df
    day_df[outcome_column] = day_df.apply(is_within_interval, axis=1)

    return day_df

def check_if_intervals_overlap(interval_a, interval_b, dates_column_dict, outcome_column, \
                               additional_distinguishers=None):
    """
    Check if intervals in 'interval_a' dataframe overlap with any intervals in 'interval_b' dataframe for the same 'personid', 
    and for the same additional distinguishers (i.e. datasource, hospital_location)
    The function adds a column to 'interval_a' indicating if an overlap was found and another column showing
    the minimum days until or since an overlapping interval, if no overlap is found.
    
    Parameters:
    - interval_a: DataFrame containing intervals to check.
    - interval_b: DataFrame containing intervals to compare with.
    - dates_column_dict: Dictionary with 'start' and 'end' keys mapping to column names in both DataFrames.
    - outcome_column: The column name to store the overlap status.
    - additional_distinguishers: Optional list of column names to further refine matching criteria (e.g., 'event_type').
    
    Returns:
    - interval_a: Updated DataFrame with two new columns indicating overlap and days to closest non-overlapping interval.
    """
    def operate_on_each_row(row_a):
        # For this row's personid, filter dataframe b to only those rows with the same personid
        matching_entries = interval_b.loc[interval_b['personid'] == row_a['personid']].copy(deep=True)

        # Filter using additional distinguishers
        if additional_distinguishers:
            for col in additional_distinguishers:
                # Ensure that row_a[col] is treated as a list for comparison
                values_in_row_a = row_a[col] if isinstance(row_a[col], list) else [row_a[col]]

                # We need a helper function for filtering into the rows that have in list b, as 
                # least one value from a
                def has_overlap(row_b, values_in_row_a = values_in_row_a):
                    values_in_row_b = row_b[col] if isinstance(row_b[col], list) else [row_b[col]]
                    # Return True if any value in row_a's list overlaps with values in row_b's list
                    return bool(set(values_in_row_a) & set(values_in_row_b))

                # Apply the has_overlap function to each row in matching_entries
                matching_entries = matching_entries.loc[matching_entries.apply(has_overlap, axis=1)].copy(deep=True)
    
        # If there were no matching entries for that personid and additional distinguishers
        # There is nothing to match so the answer is simple and you can return
        if len(matching_entries) == 0:
            return False, np.nan

        # There are matching entries to iterate through

        # The default value is that there is no overlap with that subset of matching entries
        overlap_found = False  # Track if an overlap is found
        # In case there are no overlaps, we may need to compare to multiple events in B. We 
        # want to keep track of how many days off so that we can at the end get the minimum value
        days_ahead_list = []

        # Simplify the variables so it is easy to read in the loop below
        # The start and end for this row
        start_a = row_a[dates_column_dict['start']].date()
        end_a = row_a[dates_column_dict['end']].date()

        # For each event in the subset of matching entries from B
        for _, entry_b in matching_entries.iterrows():
            start_b = entry_b[dates_column_dict['start']].date()
            end_b = entry_b[dates_column_dict['end']].date()

            # Check for overlap. Break once you find an overlap.
            if start_a <= end_b and end_a >= start_b:
                overlap_found = True
                days_ahead_list.append(0)  # Overlapping, so days ahead = 0
                break  

            # If no overlap, calculate days ahead or behind the current event.
            # Use float('inf') when the comparison doesn't apply, as we only want valid results.            
            days_before = -(start_b - end_a).days if start_b > end_a else float('inf')
            days_after = (start_a - end_b).days if start_a > end_b else float('inf')
            days_ahead = min(days_after, days_before, key=abs)
            days_ahead_list.append(days_ahead)

        # If no overlap is found, find the minimum days ahead or behind
        # When comparing you care most about absolute value, but keep whether it was a positive or 
        # negative number
        # Explain what positive number means here
        min_days_ahead = min(days_ahead_list, key=abs)

        return overlap_found, min_days_ahead

    # Apply the combined operation to each row in interval_a
    results = interval_a.apply(operate_on_each_row, axis=1)
    
    # Extract overlap and days_ahead into separate columns
    interval_a[outcome_column] = [res[0] for res in results]
    interval_a[outcome_column + "_days_ahead"] = [res[1] for res in results]

    # Sort the dataframe for easier analysis
    interval_a.sort_values(by=['personid', dates_column_dict['start'], dates_column_dict['end']], inplace=True)

    return interval_a
