import io
import pandas
from ..additionalFunctions import Global



from ..models import Business_Indicator, Business_Indicator_Data, Subdivision

class BusinessIndicatorDownload4CSV:
    def __init__(self, file):
        self.file = file

    def run(self):
        decoded_file = self.file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        dataframe = pandas.read_csv(io_string, sep=r';',  usecols=['Подразделение', 'Показатель', 'Дата и время', 'Значение'])

        for index, row in dataframe.iterrows():
            subdivision_name = row['Подразделение']
            try:
                subdivision = Subdivision.objects.get(name=subdivision_name)
            except Subdivision.DoesNotExist:
                print("Подразделение не найдено в БД: " + subdivision_name)
                continue

            business_Indicator_name = row['Показатель']
            try:
                business_Indicator = Business_Indicator.objects.get(name=business_Indicator_name)
            except Business_Indicator.DoesNotExist:
                print("Показатель не найдено в БД: " + business_Indicator_name)
                continue

            naive_begin_date_time_string = row['Дата и время']
            local_begin_date_time = Global.strdatetime2datetime(naive_begin_date_time_string)

            indicator_value = row['Значение']

            business_Indicator_Data = Business_Indicator_Data()
            business_Indicator_Data.subdivision = subdivision
            business_Indicator_Data.business_indicator = business_Indicator
            business_Indicator_Data.begin_date_time = local_begin_date_time
            business_Indicator_Data.indicator_value = indicator_value
            business_Indicator_Data.time_interval_length = 15
            business_Indicator_Data.save()
            # print(business_Indicator_Data.__str__())

