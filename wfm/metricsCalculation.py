import pandas

from .api.serializers import MetricsSerializer
from .models import Demand_Hour_Main


class MetricsCalculation:

    def __init__(self, subdivision_id, from_date, to_date):
        self.subdivision_id = subdivision_id
        self.from_date = from_date
        self.to_date = to_date
        self.output_data = []

    def serialize_data(self, df_dhm_on_date, df_dhm_on_hour):
        output_objects = []

        for dhm_row in df_dhm_on_date.itertuples():
            line_objects = []
            df_dhm_on_hour_rows = df_dhm_on_hour[(df_dhm_on_hour.date == dhm_row.date)
                                                 & (df_dhm_on_hour.duty == dhm_row.duty)]
            for dhm_on_hour_row in df_dhm_on_hour_rows.itertuples():
                line_objects_row = {
                    "date": dhm_on_hour_row.date,
                    "hour": dhm_on_hour_row.hour,
                    "duty": dhm_on_hour_row.duty,
                    "demand": dhm_on_hour_row.demand_value,
                    "covering": dhm_on_hour_row.covering_value,
                    "breaks": dhm_on_hour_row.breaks_value,
                    "overcovering": dhm_on_hour_row.overcovering,
                    "undercovering": dhm_on_hour_row.undercovering
                }
                line_objects.append(line_objects_row)

            output_objects_row = {
                "date": dhm_row.date,
                "duty": dhm_row.duty,
                "demand": dhm_row.demand_sum,
                "covering": dhm_row.covering_sum,
                "breaks": dhm_row.breaks_sum,
                "overcovering": dhm_row.overcovering_value,
                "undercovering": dhm_row.undercovering_value,
                "covering_percentage": dhm_row.covering_percentage,
                "utilization_percentage": dhm_row.utilization_percentage,
                "lines": line_objects
            }
            output_objects.append(output_objects_row)

        self.output_data = output_objects
        metrics_serializer = MetricsSerializer(self)

        return metrics_serializer

    def calculate_output_data(self):
        demand_hour_main = Demand_Hour_Main.objects.filter(subdivision_id=self.subdivision_id,
                                                           demand_date__gte=self.from_date,
                                                           demand_date__lte=self.to_date)

        df_dhm_on_hour = pandas.DataFrame(
            demand_hour_main.values_list('demand_date', 'demand_hour', 'duty_id', 'demand_value',
                                         'covering_value', 'breaks_value'),
            columns=['date', 'hour', 'duty', 'demand_value', 'covering_value', 'breaks_value'])

        df_dhm_on_hour['covering_diff'] = df_dhm_on_hour['covering_value'] - df_dhm_on_hour['demand_value'] - \
                                          df_dhm_on_hour['breaks_value']
        df_dhm_on_hour['overcovering'] = df_dhm_on_hour[df_dhm_on_hour.covering_diff > 0]['covering_diff']
        df_dhm_on_hour.overcovering = df_dhm_on_hour.overcovering.fillna(0)
        df_dhm_on_hour['undercovering'] = -df_dhm_on_hour[df_dhm_on_hour.covering_diff < 0]['covering_diff']
        df_dhm_on_hour.undercovering = df_dhm_on_hour.undercovering.fillna(0)

        # set 'float' type
        df_dhm_on_hour.covering_value = df_dhm_on_hour.covering_value.astype('float')
        df_dhm_on_hour.breaks_value = df_dhm_on_hour.breaks_value.astype('float')
        df_dhm_on_hour.overcovering = df_dhm_on_hour.overcovering.astype('float')
        df_dhm_on_hour.undercovering = df_dhm_on_hour.undercovering.astype('float')

        df_dhm_on_hour['demand_sum'] = df_dhm_on_hour.groupby(['date', 'duty'])['demand_value'].transform("sum")
        df_dhm_on_hour['covering_sum'] = df_dhm_on_hour.groupby(['date', 'duty'])['covering_value'].transform("sum")
        df_dhm_on_hour['breaks_sum'] = df_dhm_on_hour.groupby(['date', 'duty'])['breaks_value'].transform("sum")
        df_dhm_on_hour['overcovering_value'] = df_dhm_on_hour.groupby(['date', 'duty'])['overcovering'].transform("sum")
        df_dhm_on_hour['undercovering_value'] = df_dhm_on_hour.groupby(['date', 'duty'])['undercovering'].transform(
            "sum")

        df_dhm_on_date = df_dhm_on_hour[
            ['date', 'duty', 'demand_sum', 'covering_sum', 'breaks_sum', 'overcovering_value',
             'undercovering_value']].drop_duplicates()
        df_dhm_on_date['covering_clear'] = df_dhm_on_date.covering_sum - df_dhm_on_date.breaks_sum
        df_dhm_on_date['covering_percentage'] = ((df_dhm_on_date.covering_clear - df_dhm_on_date.overcovering_value
                                                  ) / df_dhm_on_date.demand_sum).astype('float')
        df_dhm_on_date['utilization_percentage'] = df_dhm_on_date.apply(
            lambda x: (x['demand_sum'] - x['undercovering_value']
                       ) / x['covering_clear'] if x['covering_clear'] != 0 else 0, axis=1).astype('float')
        df_dhm_on_date['covering_percentage'] = df_dhm_on_date['covering_percentage'].round(decimals=2)
        df_dhm_on_date['utilization_percentage'] = df_dhm_on_date['utilization_percentage'].round(decimals=2)

        metrics_serializer = self.serialize_data(df_dhm_on_date, df_dhm_on_hour)

        return metrics_serializer
