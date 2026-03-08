"""hie_events_dataframe.py"""

from .track_time import track_time
from Python_CareEvAccess_Classes.careev_connection import CareEvConnection
from Python_QueryBuilders_Classes.perform_query import PerformQuery
from Python_QueryBuilders_Classes.query_text import QueryText
from Python_Events_Classes.events_dataframe import EventsDataframe


class QueriedEventsDataframe(EventsDataframe):

    @track_time
    def __init__(self, query_string, columns_dict):
        # Convert the string into an object of the QueryText class, this is necessary to use
        # methods of the classes used below
        query_text = QueryText(query_string)

        # Connect to database, perform query, get results into a dataframe
        connection = CareEvConnection("Connection for get_encounter_claims_from_hie")
        events_df = PerformQuery(connection).execute_query(query_text)
        connection.delete_connection()

        # Sort by personid, start, end
        events_df = events_df.sort_values(by=[columns_dict['personid'], columns_dict['start'], columns_dict['end']], ascending=True)

        # Use parent constructor to create the attributes of an EventsDataframe object
        # Initializes the object attributes: df, columns_dict
        super().__init__(events_df, columns_dict)
