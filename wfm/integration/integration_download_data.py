import datetime
import io

import pandas
from ..additionalFunctions import Global
from django.contrib.auth.models import User
from ..db import DataBase
from ..demandProcessing import DemandProcessing
from ..models import Business_Indicator, Business_Indicator_Data, Subdivision, Employee, Personal_Documents, \
    Employee_Availability, Employee_Fact_Scan
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
                    if employee.ref_id_1C != row['REFID1C'] or employee.juristic_person_id != row['JURISTICPERSONID'] or employee.dateTo != row['dateTo']:
                        employee.ref_id_1C = row['REFID1C']
                        employee.juristic_person_id = row['JURISTICPERSONID']
                        employee.dateTo = row['dateTo']
                        employees_arr.append(employee)
                else:
                    continue

            else:
                Employee.objects.create(user=user, subdivision=subdivision, middle_name=row['middle_name'],
                                        personnel_number=row['personnel_number'], pf_reg_id=row['pf_reg_num'],
                                        ref_id_1C=row['REFID1C'], juristic_person_id=row['JURISTICPERSONID'], dateTo=row['dateTo'])

        User.objects.bulk_update(users_arr, ['first_name', 'last_name', 'is_active'])
        Employee.objects.bulk_update(employees_arr, ['middle_name', 'personnel_number', 'ref_id_1C', 'juristic_person_id', 'dateTo'])


class LoadFactScanForEmployees:
    def run(self):

        query = """SELECT DISTINCT 
                        a.ScanDate, 
                        a.StoreNumber, 
                        a.PersonnelNumber, 
                        b.ScanTimeStart,
                        c.ScanTimeEnd
                    FROM public.datai_scan_history_log a
                    JOIN (SELECT MIN(ScanTime) AS ScanTimeStart, ScanDate, StoreNumber, PersonnelNumber, ScanType
                          FROM public.datai_scan_history_log 
                          WHERE ScanType = 0 AND ScanDate = CURRENT_DATE  - INTERVAL '1 Day' 
                          GROUP BY ScanDate, StoreNumber, PersonnelNumber, ScanType) b ON b.ScanDate = a.ScanDate 
                          AND b.StoreNumber = a.StoreNumber AND b.PersonnelNumber = a.PersonnelNumber
                    JOIN (SELECT MIN(ScanTime) AS ScanTimeEnd, ScanDate, StoreNumber, PersonnelNumber, ScanType
                          FROM public.datai_scan_history_log 
                          WHERE ScanType = 1 AND ScanDate = CURRENT_DATE  - INTERVAL '1 Day' 
                          GROUP BY ScanDate, StoreNumber, PersonnelNumber, ScanType) c ON c.ScanDate = a.ScanDate 
                          AND c.StoreNumber = a.StoreNumber AND c.PersonnelNumber = a.PersonnelNumber
                    WHERE a.ScanDate = CURRENT_DATE  - INTERVAL '1 Day' """
        dataframe = DataBase.get_dataframe_by_query(query)

        for index, row in dataframe.iterrows():
            storeNumber = row['storenumber']
            try:
                subdivision = Subdivision.objects.get(external_code=storeNumber)
            except Subdivision.DoesNotExist:
                continue
            personnelNumber = row['personnelnumber']
            try:
                employee = Employee.objects.get(personnel_number=personnelNumber)
            except Employee.DoesNotExist:
                continue

            Employee_Fact_Scan.objects.create(scan_date=row['scandate'], subdivision=subdivision, employee=employee,
                                              time_from=row['scantimestart'], time_to=row['scantimeend'])





