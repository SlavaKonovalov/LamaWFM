import io
import pandas
from ..additionalFunctions import Global
from django.contrib.auth.models import User
from ..db import DataBase
from ..models import Business_Indicator, Business_Indicator_Data, Subdivision, Employee


class BusinessIndicatorDownload4CSV:
    def __init__(self, file):
        self.file = file

    def run(self):
        decoded_file = self.file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        dataframe = pandas.read_csv(io_string, sep=r';',
                                    usecols=['Подразделение', 'Показатель', 'Дата и время', 'Значение'])

        for index, row in dataframe.iterrows():
            subdivision_name = row['Подразделение']
            try:
                subdivision = Subdivision.objects.get(name=subdivision_name)
            except Subdivision.DoesNotExist:
                print("Подразделение не найдено в БД: " + subdivision_name)
                continue

            business_indicator_name = row['Показатель']
            try:
                business_indicator = Business_Indicator.objects.get(name=business_indicator_name)
            except Business_Indicator.DoesNotExist:
                print("Показатель не найдено в БД: " + business_indicator_name)
                continue

            naive_begin_date_time_string = row['Дата и время']
            local_begin_date_time = Global.strdatetime2datetime(naive_begin_date_time_string)

            indicator_value = row['Значение']

            business_indicator_data = Business_Indicator_Data()
            business_indicator_data.subdivision = subdivision
            business_indicator_data.business_indicator = business_indicator
            business_indicator_data.begin_date_time = local_begin_date_time
            business_indicator_data.indicator_value = indicator_value
            business_indicator_data.time_interval_length = 15
            business_indicator_data.save()


class CreateEmployeesByUploadedData:
    def run(self):
        users_arr = []
        employees_arr = []

        query = "SELECT " \
                "username, first_name, last_name, middle_name, " \
                "personnel_number, store_number, pf_reg_num, subdivision_id " \
                "FROM public.datai_employees_data " \
                "WHERE subdivision_id <> 0"

        dataframe = DataBase.get_dataframe_by_query(query)
        for index, row in dataframe.iterrows():
            username = row['username']
            user_fnd = User.objects.get_or_create(username=username, defaults={'first_name': row['first_name'],
                                                  'last_name': row['last_name'], 'is_active': True})
            user = user_fnd[0]
            subdivision = Subdivision.objects.get(id=row['subdivision_id'])
            if not user_fnd[1]:
                employee = Employee.objects.get(user_id=user.id)

                if employee and subdivision.id == employee.subdivision.id:
                    if user.first_name != row['first_name'] or user.last_name != row['last_name'] or user.is_active is not True:
                        user.first_name = row['first_name']
                        user.last_name = row['last_name']
                        user.is_active = True
                        users_arr.append(user)
                    if employee.middle_name != row['middle_name'] or employee.personnel_number != row['personnel_number']:
                        employee.middle_name = row['middle_name']
                        employee.personnel_number = row['personnel_number']
                        employees_arr.append(employee)
                else:
                    continue

            else:
                Employee.objects.create(user=user, subdivision=subdivision, middle_name=row['middle_name'],
                                        personnel_number=row['personnel_number'], pf_reg_id=row['pf_reg_num'])

        User.objects.bulk_update(users_arr, ['first_name', 'last_name', 'is_active'])
        Employee.objects.bulk_update(employees_arr, ['middle_name', 'personnel_number'])
