"""inpatient_and_ed_handler.py"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Python_Events_Classes.ed_events_dataframe import EDEventsDataframe
from Python_Events_Classes.queried_events_dataframe import QueriedEventsDataframe
from Python_Events_Classes.inpatient_events_dataframe import InpatientEventsDataframe
from Python_Events_Classes.events_comparer import EventsComparer

class InpatientAndEDHandler():
    """
    Using queries for inpatient and ED events as inputs, access the database, 
    cleans and organizes inpatient and ED events, and categorizes them.
    Uses various classes such as QueriedEventsDataframe, EDEventsDataframe, 
    InpatientEventsDataframe, and EventsComparer.
    """
    def __init__(self, inpatient_query_string, ed_query_string,
                 columns_dict, verbose = True):
        self.error_message = "Error in InpatientAndEDHandler"
        self.verbose = verbose

        # Initialize parameters
        self.ed_query_string = ed_query_string
        self.inpatient_query_string = inpatient_query_string
        self.columns_dict = columns_dict

        # Parameters that will be populated by the methods
        self.ed_events = None
        self.inpatient_events = None
        self.ed_only_events = None
        self.ed_inpatient_events = None
        self.inpatient_only_events = None

    def _log(self, message):
        """Helper method for logging based on the verbose flag."""
        if self.verbose:
            print(message)

    def get_standardize_ed(self):
        """
        Queries, cleans, and standardizes ED event data.
        """
        # Pull raw data
        # Standardize into general events
        self._log("\nQuerying ED data from CareEv updated table")
        self._log("\nStandardizing as General Events...")
        hie_ed_events = QueriedEventsDataframe(self.ed_query_string, self.columns_dict)
        if self.verbose:
            hie_ed_events.print_breakdown()

        # Standardize into ED Events
        self._log("\nStandardizing as ED Events...")
        ed_events = EDEventsDataframe(hie_ed_events)
        if self.verbose:
            ed_events.print_breakdown()

        # Populate the attribute with the now standardize ED events
        self.ed_events = ed_events

    def get_standardize_inpatient(self):
        """
        Queries, cleans, and standardizes inpatient event data.
        """
        # Pull raw data
        # Standardize into general events
        self._log("\nQuerying Inpatient data from CareEv updated table")
        self._log("\nStandardizing as General Events...")
        hie_inp_events = QueriedEventsDataframe(self.inpatient_query_string, self.columns_dict)
        if self.verbose:
            hie_inp_events.print_breakdown()

        # Standardize Inpatient Events
        self._log("Standardizing as Inpatient Events...")
        inpatient_events = InpatientEventsDataframe(hie_inp_events, distinguishers = ['datasource'])
        if self.verbose:
            inpatient_events.print_breakdown()

        # Populate the attribute with the now standardize ED events
        self.inpatient_events = inpatient_events

    def categorize(self):
        """
        Categorizes the events into ED-only, inpatient-only, and overlapping events.
        
        Raises:
        - ValueError: If ED or inpatient events are not yet standardized.
        - ValueError: There is no information in the dataframe to assign emergency by admit
        """
        if self.ed_events is None or self.inpatient_events is None:
            raise ValueError ("You must get and standardize the ED and Inpatient objects first")

        if 'emergency_by_admit' not in self.inpatient_events.df.columns:
            raise ValueError (self.error_message + "The Inpatient Events object must be \
                              such that it has a 'emergency_by_admit' column which should \
                                have been built in the constructor")

        if self.verbose:
            print("All ED")
            self.ed_events.print_breakdown()
            print("All Inpatient")
            self.inpatient_events.print_breakdown()

        #-------------------------------
        # Part 1: Steps to flag overlaps
        
        self._log("Steps to flag the ED only: ")
        # Initialize the class for comparison of overlapping events
        comparer = EventsComparer()
        # Flag ED-only by finding which ed events did not have any overlap with inpatient events
        self.ed_events = comparer.check_overlap(self.ed_events, self.inpatient_events, \
                                                outcome_column = 'overlaps_with_inpatient',
                                                additional_distinguishers = ['datasource'])

        # Categorize into ED-only and those that overlap
        ed_only_events = comparer.filter_by_boolean(self.ed_events, \
                                                    'overlaps_with_inpatient', choose = False)
        ed_overlapping = comparer.filter_by_boolean(self.ed_events, \
                                                    'overlaps_with_inpatient', choose = True)

        # See which Inpatient Events overlap with the ED ones

        # Compare inpatient to those ED you already know overlap
        self.inpatient_events = comparer.check_overlap(self.inpatient_events, ed_overlapping, \
                                                                outcome_column = 'overlaps_with_ed',
                                                                additional_distinguishers = ['datasource'])
        #-----------------------------
        # Step 2: Get the ED Inpatient

        # Print out contingency tables with more information on how the inpatient were flagged
        if self.verbose:
            print("Contingency table explaining how ed_inpatient was flagged")
            cont = pd.crosstab(self.inpatient_events.df['overlaps_with_ed'], self.inpatient_events.df['emergency_by_admit'])
            print(cont)
            print("Contingency table pointing out how many were NULL")
            cont = pd.crosstab(self.inpatient_events.df['overlaps_with_ed'], self.inpatient_events.df['admitcolumns_null'])
            print(cont)

        # Use two criteria to decide whether ED inpatient
        # 1) Either it overlaps with ED in time
        # 2) There are signs that it is emergency from the admitsource columns (this logic is worked in the
        # constructor of the inpatient_events_dataframe class)
        self.inpatient_events.df['ED-Inpatient'] = self.inpatient_events.df['emergency_by_admit'] | self.inpatient_events.df['overlaps_with_ed']
        # Filter by thae ED-Inpatient column
        ed_inpatient_events = comparer.filter_by_boolean(self.inpatient_events, \
                                                    'ED-Inpatient', choose = True)
        
        # For inpatients that overlap with ED,
        # add the eventid, admitsource and datasource from ED event to the inpatient's event
        ed_inpatient_events = comparer.merge_unique_values(
                                ed_inpatient_events, ed_overlapping, \
                                columns=[self.columns_dict['eventid'],'datasource', 'admitsource', 'admitsourcecode', 'primarycaresetting'],
                                        flag_column = 'overlaps_with_ED')

        # Inpatient Only
        inpatient_only_events = comparer.filter_by_boolean(self.inpatient_events, \
                                                    'ED-Inpatient', choose = False)

        # Update attributes
        self.ed_only_events = ed_only_events
        self.ed_inpatient_events = ed_inpatient_events
        self.inpatient_only_events = inpatient_only_events

        # Break down days off for the ED only and inpatient only for the nearest counterparts
        if self.verbose:
            self._plot_days_off()

    def strip_to_necessary_cols(self, additional_columns_keep = None):
        """
        Unless additional columns are specified, the result dataframe will only have personid, 
        eventid, admitdate, and dischargedate.
        """

        # Columns to keep
        universal_columns = [self.columns_dict[x] for x in self.columns_dict.keys()]
 
        if additional_columns_keep:
            universal_columns = universal_columns + additional_columns_keep
        
        # Update the attributes using only the necessary columns
        self.ed_only_events.df = self.ed_only_events.df[universal_columns]
        self.ed_inpatient_events.df = self.ed_inpatient_events.df[universal_columns]
        self.inpatient_only_events.df = self.inpatient_only_events.df[universal_columns]

    def organize_into_one_dataframe(self):
        # Add category label
        self.inpatient_only_events.df['Category'] = np.full(len(self.inpatient_only_events.df), 'Inpatient_Only')
        self.ed_only_events.df['Category'] = np.full(len(self.ed_only_events.df), 'ED_Only')
        self.ed_inpatient_events.df['Category'] = np.full(len(self.ed_inpatient_events.df), 'ED_Inpatient')

        result = pd.concat([self.inpatient_only_events.df, self.ed_only_events.df, self.ed_inpatient_events.df])
        result.sort_values(by=[self.columns_dict['personid'], self.columns_dict['start']], inplace = True)

        return result

    def _plot_days_off(self):
        def _plot_overlap_delta(event, columnname, xlabel, filename):
            df = event.df.copy(deep = True)
            # Ensure 'ed_duration' contains only valid, finite numbers
            df = df[pd.notnull(df[columnname]) & np.isfinite(df[columnname])]
            # Bins and label
            bins = [-np.inf, -10, -5, -1, 0.9, 5, 10, np.inf]
            labels = ['Farther back than 9 days', '-9 to -5', '-5 to -1', '0', '1 to 5', '5 to 10', '11+']
            # Use pd.cut() to categorize the data into bins
            df['category'] = pd.cut(df[columnname], bins=bins, labels=labels)
            # Count the occurrences in each category
            category_counts = df['category'].value_counts().reindex(labels)
            # Plotting
            plt.bar(category_counts.index, category_counts.values, edgecolor='black')
            plt.xlabel(xlabel)
            plt.ylabel('Frequency')
            plt.title('Histogram')
            plt.xticks(rotation=45)  # Rotate labels to improve readability if necessary
            plt.savefig(filename, dpi = 400)
            plt.cla()

        _plot_overlap_delta(self.inpatient_only_events, 'overlaps_with_ed_days_ahead', xlabel = 'Inpatient days ahead of ED',
                                 filename = "inpedhandler_in inpatient_only_days_off_from_ed.jpg")
        _plot_overlap_delta(self.ed_only_events, 'overlaps_with_inpatient_days_ahead', xlabel = 'ED days ahead of inpatient',
                                 filename = "inpedhandler_ed_only_days_off_from_inpatient.jpg")

        n = sum(self.inpatient_only_events.df['overlaps_with_ed_days_ahead'].isna())
        self._log(f"Inpatient visits with no EDassociated for the patient: {n}")
        n_eds_with_no_inpatient_ever = sum(self.ed_only_events.df['overlaps_with_inpatient_days_ahead'].isna())
        self._log(f"ED visits with no inpatient associated for the patient: {n_eds_with_no_inpatient_ever}")


