from django.conf import settings
import psycopg2
import pandas

class DataBase:

    @staticmethod
    def get_dataframe_by_query(query):
        user = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']
        database_name = settings.DATABASES['default']['NAME']
        host = settings.DATABASES['default']['HOST']
        conn_string = "host='" + host + "' dbname= '" + database_name + "' user= '" + user + "' password='" + password + "'"

        connection = psycopg2.connect(conn_string)

        df = pandas.read_sql(query, connection)

        return df

