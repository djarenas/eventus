"""inpatient_events_dataframe.py"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .track_time import track_time
from .events_dataframe import EventsDataframe
from .events_merger import EventsMerger

class InpatientEventsDataframe(EventsDataframe):
    """
    A child class of EventsDataFrame that specializes in inpatient events.
    As an input, it uses an EventsDataFrame object which has already gone through 
    some data cleaning and standardization.
    """
    @track_time
    def __init__(self, events_dataframe, distinguishers = None):
        self.error_message = "Error in InpatientEventsDataframe. "
        if not isinstance(events_dataframe, EventsDataframe):
            raise ValueError(self.error_message + \
                             "Constructor input must be a EventsDataframe object")

        # Use the parent constructor
        # Checks dataframe input, columns, makes date columns in correct format, 
        super().__init__(events_dataframe.df, events_dataframe.columns_dict)

        print("In InpatientEventsDataframe constructor. Number of original events: ", len(self.df))

        # The following modifications are necessary to have a proper
        # conceptual InpatientEventsDataframe

        # Fix SNF entries, keep track of how many
        print("before dropping SNF and invalid datasources: ")
        self.print_breakdown()
        self._fix_snf_and_invalid_datasources()
        print("after dropping SNF and invalid datasources: ")
        self.print_breakdown()

        # How many pre-merged events have an admitdate = dischargedate (time sensitive comparison)
        print("Number of pre-merged events where admitdate is the same as dischargedate")
        print(len(self.df.loc[self.df[self.columns_dict['start']] == self.df[self.columns_dict['end']]]))

        # For inpatient hospitalizations, we should merge/chain overlapping encounters/claims
        event_merger = EventsMerger(self.columns_dict) # Instantiate the class for special merging methods
        self.df = event_merger.merge_overlapping_events(self.df, ['datasource'])

        # Update attribute with in
        self.calc_duration_hours('inpatient_duration')

        # Add a boolean column on whether the admitsource (or admitsourcecode) columns have values
        # with substrings suggestive of emergency room
        self._check_admit_source_for_emergency_strings(emergency_strings = ['emer', 'trauma', 'er'])

    def plot_inpatient_duration_histogram(self, filename = None):
        """
        This method can only be used after the constructor
        Histogram of Inpatient duration in days
        """
        df = self.df.copy(deep=True)
        # Ensure 'ed_duration' contains only valid, finite numbers
        df = df[pd.notnull(df['ed_duration']) & np.isfinite(df['ed_duration'])]

        # Define custom bin edges and labels
        bins = [-np.inf, 0, 12, 24, 36, 48, np.inf]
        labels = ['0', '1-12', '13-24', '25-36', '37-48', '49+']

        # Use pd.cut() to categorize the data into bins
        df['category'] = pd.cut(df['ed_duration'], bins=bins, labels=labels)

        # Count the occurrences in each category
        category_counts = df['category'].value_counts().reindex(labels)

        # Plotting
        plt.bar(category_counts.index, category_counts.values, edgecolor='black')
        plt.xlabel('Inpatient Duration (hrs)')
        plt.ylabel('Frequency')
        plt.title('Histogram of Inpatient Duration')
        plt.xticks(rotation=45)  # Rotate labels to improve readability if necessary

        if filename is not None:
            plt.savefig(filename, dpi = 400)
        else:
            plt.show()

    def _fix_snf_and_invalid_datasources(self):
        # Check that the dataframe attribute,
        # initialized by the parent constructor, has the right column

        if 'type' not in self.df.columns:
            raise ValueError("Cannot fix SNF. Queried data must have a 'type' column")
        if 'datasource' not in self.df.columns:
            raise ValueError("Cannot fix invalid datasources. Queried data must have a 'datasource' column")
        
        df = self.df.copy(deep=True)
        # Remove SNF types
        before = len(df)
        df = df.loc[df['type'] != 'Skilled Nursing Facility']
        after = len(df)
        print("SNF removed:", before-after)

        # Remove invalid facilities
        facilities = [
            'Abigail House for Nursing and Rehab (PCC)',
            'Atrium Post Acute Care of Woodbury (PCC)',
            'Cambridge Rehabilitation and Healthcare (PCC)',
            'Camden-InglemoorRehabPcc',
            'Cheshire Home (PCC)',
            'Genesis HealthCare Millville Center (PCC)',
            'Genesis HealthCare North Cape Center (PCC)',
            'Hammonton Center (PCC)',
            'Laurel Brook Rehabilitation & Healthcare Center (PCC)',
            'Merry Heart Nursing Home (PCC)',
            'Trenton-PrincetonCarePCC',
            'UMC at Pitman AL (PCC)',
            'UMC at Pitman HC (PCC)',
            'UMC at The Shores AL (PCC)',
            'UMC at The Shores HC (PCC)'
        ]

        before = len(df)
        df = df.loc[~df['datasource'].isin(facilities)]
        after = len(df)
        print("Specific facilities were removed. Number of rows: ", before-after)

        # Update attributes
        self.df = df

    def _check_admit_source_for_emergency_strings(self, emergency_strings):
        for col in ['admitsource', 'admitsourcecode']:
            if col not in self.df.columns:
                raise ValueError(f"Error in inpatient_events_dataframe constructor, using _check_admit_source: \
                                 {col} should be in the columns of the dataframe")

        def _check_substrings(row_list, substrings):
            if (len (row_list) == 0) | (len(row_list) ==1 and row_list[0] == ''):
                return False
            return any(any(sub.lower() in item.lower() for sub in substrings) for item in row_list)

        def _check_empty_list(row_list):
            return len(row_list) == 1 and row_list[0] == ''

        self.df['admitsource_check'] = self.df['admitsource'].apply(lambda row: _check_substrings(row, emergency_strings))
        self.df['admitsourcecode_check'] = self.df['admitsourcecode'].apply(lambda row: _check_substrings(row, emergency_strings))
        self.df['admitcolumns_null'] = self.df.apply(lambda row: _check_empty_list(row['admitsource']) \
                                                    and _check_empty_list(row['admitsourcecode']), axis=1)

        # Update attribute, remove dummy columns
        self.df['emergency_by_admit'] = self.df['admitsource_check'] | self.df['admitsourcecode_check']
        self.df.drop(['admitsource_check', 'admitsourcecode_check'], axis = 1, inplace = True)
