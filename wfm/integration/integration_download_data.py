import datetime
import io

import pandas
from ..additionalFunctions import Global
from django.contrib.auth.models import User
from ..db import DataBase
from ..demandProcessing import DemandProcessing
from ..models import Business_Indicator, Business_Indicator_Data, Subdivision, Employee, Personal_Documents, \
    Employee_Availability
from ..shiftPlanning import ShiftPlanning


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

        query = "SELECT  * FROM public.datai_employees_data WHERE subdivision_id <> 0"

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
                    if employee.ref_id_1C != row['REFID1C'] or employee.juristic_person_id != row['JURISTICPERSONID']:
                        employee.ref_id_1C = row['REFID1C']
                        employee.juristic_person_id = row['JURISTICPERSONID']
                        employees_arr.append(employee)
                else:
                    continue

            else:
                Employee.objects.create(user=user, subdivision=subdivision, middle_name=row['middle_name'],
                                        personnel_number=row['personnel_number'], pf_reg_id=row['pf_reg_num'],
                                        ref_id_1C=row['REFID1C'], juristic_person_id=row['JURISTICPERSONID'])

        User.objects.bulk_update(users_arr, ['first_name', 'last_name', 'is_active'])
        Employee.objects.bulk_update(employees_arr, ['middle_name', 'personnel_number'])


class LoadAvailabilityFromDoc:
    @staticmethod
    def load():
        personal_documents = Personal_Documents.objects.all()
        personal_documents = personal_documents.filter(operation_type='INS')
        availabilities_for_update = []
        availabilities_for_create = []
        documents = []
        for personal_document in personal_documents.iterator():
            employee = Employee.objects.get(personnel_number=personal_document.personnel_number)
            if not employee:
                continue
            subdivision = Subdivision.objects.get(id=employee.subdivision_id)
            if not subdivision:
                continue

            date_start = datetime.datetime.combine(personal_document.date_from, datetime.time.min)
            date_start = Global.add_timezone(date_start)
            date_start += datetime.timedelta(hours=11)
            date_end = datetime.datetime.combine(personal_document.date_to, datetime.time.min)
            date_end = Global.add_timezone(date_end)
            date_end += datetime.timedelta(hours=11)
            date_step = date_start

            employee_list = [employee.id]
            shift_planning = ShiftPlanning()
            shift_planning.delete_all_shifts(subdivision.id, date_start, date_end, employee_list)

            demand_processing = DemandProcessing()
            demand_processing.recalculate_covering(subdivision.id, date_start.date())

            while date_step < date_end:
                employee_availability = Employee_Availability.objects.filter(employee_id=employee.id,
                                                                             subdivision_id=subdivision.id,
                                                                             begin_date_time__lt=date_step,
                                                                             end_date_time__gte=date_step)
                if employee_availability:
                    for row in employee_availability.iterator():
                        line = row
                        line.availability_type = 1
                        line.personnel_document = personal_document
                        line.begin_date_time = datetime.datetime.combine(date_step, datetime.time.min)
                        line.end_date_time = datetime.datetime.combine(date_step, datetime.time.max)
                        availabilities_for_update.append(line)
                else:
                    line = Employee_Availability(employee=employee, subdivision=subdivision, type=0,
                                                 availability_type=1, personnel_document=personal_document,
                                                 begin_date_time=datetime.datetime.combine(date_step, datetime.time.min),
                                                 end_date_time=datetime.datetime.combine(date_step, datetime.time.max))
                    availabilities_for_create.append(line)

                date_step += datetime.timedelta(days=1)

            doc_line = personal_document
            doc_line.operation_type = 'FIN'
            documents.append(doc_line)
        Employee_Availability.objects.bulk_create(availabilities_for_create)
        Employee_Availability.objects.bulk_update(availabilities_for_update, ['availability_type', 'personnel_document',
                                                                              'begin_date_time', 'end_date_time'])
        Personal_Documents.objects.bulk_update(documents, ['operation_type'])
