import datetime
from abc import ABC

from django.contrib.auth.models import User
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import connection
from django.db.models import Q
from rest_framework import serializers
from ..models import Production_Task, Subdivision, Employee, Scheduled_Production_Task, Employee_Position, Job_Duty, \
    Tasks_In_Duty, Appointed_Production_Task, Organization, Demand_Detail_Main, Demand_Detail_Task, Company, \
    Availability_Template, Availability_Template_Data, Employee_Availability_Templates, Planning_Method, \
    Working_Hours_Rate, Work_Shift_Planning_Rule, Breaking_Rule, Employee_Planning_Rules, Employee_Availability, \
    Employee_Shift_Detail_Plan, Employee_Shift, Holiday_Period, Holiday, Retail_Store_Format, Open_Shift_Detail, \
    Open_Shift, Demand_Hour_Shift, Demand_Hour_Main, Global_Parameters, Personal_Documents, Part_Time_Job_Vacancy, \
    Part_Time_Job_Employee_Request


class ScheduledProductionTaskSerializer(serializers.ModelSerializer):
    error_list = {}

    class Meta:
        model = Scheduled_Production_Task
        fields = '__all__'

    def is_valid(self, raise_exception=False):
        ret = super().is_valid(raise_exception)
        if not ret:
            self.error_list = self.errors
            return ret

        instance_pk = None
        if self.instance:
            instance_pk = self.instance.pk

        error_list = {}
        task = self.validated_data.get('task')
        if task.demand_data_source == 'statistical_scheduler':
            spt = Scheduled_Production_Task.objects.filter(~Q(id=instance_pk),
                                                           subdivision=self.validated_data.get('subdivision'),
                                                           task=task)
            if spt:
                error_list.update({NON_FIELD_ERRORS: "Дублирование задачи"})
                self.error_list = error_list
                return False

            if self.validated_data.get('work_scope') != 0:
                error_list.update({'work_scope': "Объём работ должен быть равен 0"})
            if self.validated_data.get('repetition_type') != 'day':
                error_list.update({'repetition_type': "Повторение должно иметь тип 'День'"})
            if self.validated_data.get('end_date') is not None:
                error_list.update({'end_date': "Дата завершения должна быть пустой"})
            if self.validated_data.get('repetition_interval') != 1:
                error_list.update({'repetition_interval': "Интервал повторения должен быть равен 1"})
            if error_list:
                error_list.update({NON_FIELD_ERRORS: "Обнаружены ошибки при сохранении задачи с "
                                                     "типом statistical_scheduler"})
                self.error_list = error_list

        return not bool(self.error_list)


class ProductionTaskSerializer(serializers.ModelSerializer):
    scheduled_task_set = ScheduledProductionTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Production_Task
        fields = '__all__'


class ProductionTaskShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Production_Task
        fields = ['id', 'name']


class SubdivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subdivision
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    # task_set = ProductionTaskSerializer(many=True, read_only=True)
    # subdivision_set = SubdivisionSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name'
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, many=False)

    class Meta:
        model = Employee
        fields = '__all__'


class EmployeePositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Position
        fields = '__all__'


class EmployeeAvailabilityTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Availability_Templates
        fields = '__all__'


class EmployeePlanningRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Planning_Rules
        fields = '__all__'


class PlanningMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planning_Method
        fields = '__all__'


class WorkingHoursRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Working_Hours_Rate
        fields = '__all__'


class WorkShiftPlanningRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work_Shift_Planning_Rule
        fields = '__all__'


class BreakingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breaking_Rule
        fields = '__all__'


class TasksInDutySerializer(serializers.ModelSerializer):
    task = ProductionTaskShortSerializer(read_only=True, many=False)

    class Meta:
        model = Tasks_In_Duty
        fields = '__all__'


class JobDutySerializer(serializers.ModelSerializer):
    task_in_duty_set = TasksInDutySerializer(read_only=True, many=True)

    class Meta:
        model = Job_Duty
        fields = '__all__'


class AppointedTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointed_Production_Task
        fields = '__all__'


class DemandTaskSerializer(serializers.ModelSerializer):
    task = ProductionTaskShortSerializer(read_only=True, many=False)

    class Meta:
        model = Demand_Detail_Task
        fields = '__all__'


class DemandMainSerializer(serializers.ModelSerializer):
    demand_detail_task_set = DemandTaskSerializer(read_only=True, many=True)

    class Meta:
        model = Demand_Detail_Main
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class AvailabilityTemplateDataSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Availability_Template_Data
        fields = '__all__'


class AvailabilityTemplateSerializer(serializers.ModelSerializer):
    data_set = AvailabilityTemplateDataSerializer(many=True, required=False)

    class Meta:
        model = Availability_Template
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.type = validated_data.get('type', instance.type)
        subdivision = validated_data.get('subdivision', None)
        if subdivision is None:
            instance.subdivision_id = None
        else:
            instance.subdivision_id = subdivision.id
        instance.save()

        lines = validated_data.get('data_set')

        for line_step in lines:
            line_id = line_step.get('id', None)
            if line_id:
                line = Availability_Template_Data.objects.get(id=line_id, template=instance)
                line.week_num = line_step.get('week_num', line.week_num)
                line.week_day = line_step.get('week_day', line.week_day)
                line.begin_time = line_step.get('begin_time', line.begin_time)
                line.end_time = line_step.get('end_time', line.end_time)
                line.save()
            else:
                Availability_Template_Data.objects.create(**line_step)
        return instance


class EmployeeAvailabilityTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Availability_Templates
        fields = '__all__'


class AssignEmployeePlanningRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Planning_Rules
        fields = '__all__'


class EmployeeAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Availability
        fields = '__all__'


class EmployeeShiftDetailPlanSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Employee_Shift_Detail_Plan
        fields = '__all__'


class PartTimeJobVacancySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    creation_date_time = serializers.DateTimeField(required=False)
    error_list = {}

    class Meta:
        model = Part_Time_Job_Vacancy
        fields = '__all__'

    def is_valid(self, raise_exception=False):
        ret = super().is_valid(raise_exception)
        if not ret:
            # выходим, если есть ошибки валидации
            self.error_list = self.errors
            return ret

        error_list = {}

        instance_pk = None
        if self.instance:
            instance_pk = self.instance.pk
        else:
            # выходим при сохранении нового объекта
            if self.validated_data.get('requested_date') <= datetime.date.today():
                error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})
                self.error_list = error_list
                return False
            else:
                return True

        job_vacancy_instance = self.instance

        if self.validated_data.get('vacancy_status') == 'created':
            if job_vacancy_instance.vacancy_status == 'created':
                if self.validated_data.get('subdivision') != job_vacancy_instance.subdivision:
                    error_list.update({'subdivision': "Подразделение не может быть изменено!"})

                if self.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})

        elif self.validated_data.get('vacancy_status') == 'confirmed':
            if job_vacancy_instance.vacancy_status == 'created':
                if self.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})

            if job_vacancy_instance.vacancy_status == 'approved':
                error_list.update({'vacancy_status': "Откат данного статуса вакансии выполнятся через 'Запрос на подработку'!"})

        elif self.validated_data.get('vacancy_status') == 'approved':
            if job_vacancy_instance.vacancy_status == 'confirmed':
                error_list.update({'vacancy_status': "Утверждение вакансии выполнятся через 'Запрос на подработку'!"})

        if error_list:
            self.error_list = error_list

        return not bool(self.error_list)


class PartTimeJobRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part_Time_Job_Employee_Request
        fields = '__all__'


class EmployeeShiftSerializerHeader(serializers.ModelSerializer):
    class Meta:
        model = Employee_Shift
        fields = '__all__'


class DemandHourMainSerializer(serializers.ModelSerializer):
    duty = JobDutySerializer(read_only=True, many=False)

    class Meta:
        model = Demand_Hour_Main
        fields = '__all__'


class DemandHourShiftSerializer(serializers.ModelSerializer):
    demand_hour_main = DemandHourMainSerializer(many=False)

    class Meta:
        model = Demand_Hour_Shift
        fields = '__all__'


class EmployeeShiftSerializer(serializers.ModelSerializer):
    detail_plan_set = EmployeeShiftDetailPlanSerializer(read_only=True, many=True)
    demand_hour_shift_set = DemandHourShiftSerializer(read_only=True, many=True)

    class Meta:
        model = Employee_Shift
        fields = '__all__'


class EmployeeShiftSerializerForUpdate(serializers.ModelSerializer):
    detail_plan_set = EmployeeShiftDetailPlanSerializer(required=False, many=True)
    demand_hour_shift_set = DemandHourShiftSerializer(required=False, many=True)

    class Meta:
        model = Employee_Shift
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.handle_correct = validated_data.get('handle_correct', instance.handle_correct)
        instance.fixed = validated_data.get('fixed', instance.fixed)
        instance.shift_date = validated_data.get('shift_date', instance.shift_date)
        instance.shift_type = validated_data.get('shift_type', instance.shift_type)
        subdivision = validated_data.get('subdivision', None)
        if subdivision is None:
            instance.subdivision_id = None
        else:
            instance.subdivision_id = subdivision.id
        employee = validated_data.get('employee', None)
        if employee is None:
            instance.employee_id = None
        else:
            instance.employee_id = employee.id
        instance.save()

        lines = validated_data.get('detail_plan_set')

        for line_step in lines:
            line_id = line_step.get('id', None)
            if line_id:
                line = Employee_Shift_Detail_Plan.objects.get(id=line_id, shift=instance)
                line.type = line_step.get('type', line.type)
                line.time_from = line_step.get('time_from', line.time_from)
                line.time_to = line_step.get('time_to', line.time_to)
                line.save()
            else:
                Employee_Shift_Detail_Plan.objects.create(**line_step)
        return instance


class HolidayPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday_Period
        fields = '__all__'


class HolidaySerializer(serializers.ModelSerializer):
    holiday_period_set = HolidayPeriodSerializer(read_only=True, many=True)

    class Meta:
        model = Holiday
        fields = '__all__'


class RetailStoreFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retail_Store_Format
        fields = '__all__'


class OpenShiftDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Open_Shift_Detail
        fields = '__all__'


class OpenShiftSerializerHeader(serializers.ModelSerializer):
    class Meta:
        model = Open_Shift
        fields = '__all__'


class OpenShiftSerializer(serializers.ModelSerializer):
    detail_open_shift_set = OpenShiftDetailSerializer(many=True, required=False)

    class Meta:
        model = Open_Shift
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.shift_date = validated_data.get('shift_date', instance.shift_date)
        subdivision = validated_data.get('subdivision', None)
        if subdivision is None:
            instance.subdivision_id = None
        else:
            instance.subdivision_id = subdivision.id
        instance.save()

        lines = validated_data.get('detail_open_shift_set')

        for line_step in lines:
            line_id = line_step.get('id', None)
            if line_id:
                line = Open_Shift_Detail.objects.get(id=line_id, open_shift=instance)
                line.type = line_step.get('type', line.type)
                line.time_from = line_step.get('time_from', line.time_from)
                line.time_to = line_step.get('time_to', line.time_to)
                line.save()
            else:
                Open_Shift_Detail.objects.create(**line_step)
        return instance


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'subdivision', 'middle_name', 'personnel_number', 'pf_reg_id', 'position', 'duties',
                  'part_time_job_org']

    def update(self, instance, validated_data):
        subdivision = validated_data.get('subdivision', None)
        if subdivision is None:
            instance.subdivision_id = None
        else:
            instance.subdivision_id = subdivision.id
        instance.id = validated_data.get('id', instance.id)
        instance.middle_name = validated_data.get('middle_name', instance.middle_name)
        instance.personnel_number = validated_data.get('personnel_number', instance.personnel_number)
        instance.pf_reg_id = validated_data.get('pf_reg_id', instance.pf_reg_id)
        position = validated_data.get('position', None)
        if position is None:
            instance.position_id = None
        else:
            instance.position_id = position.id

        instance.save()

        cursor = connection.cursor()
        query = "DELETE FROM wfm_employee_duties WHERE employee_id = %i " % (instance.id)
        cursor.execute(query)

        lines = validated_data.get("duties")

        for line_step in lines:
            cursor = connection.cursor()
            query = "INSERT INTO public.wfm_employee_duties(employee_id, job_duty_id) VALUES (%i, %i) " % (
            instance.id, line_step.id)
            cursor.execute(query)

        cursor = connection.cursor()
        query = "DELETE FROM wfm_employee_part_time_job_org WHERE employee_id = %i " % (instance.id)
        cursor.execute(query)

        lines = validated_data.get("part_time_job_org")

        for line_step in lines:
            cursor = connection.cursor()
            query = "INSERT INTO public.wfm_employee_part_time_job_org(employee_id, company_id) VALUES (%i, %i) " % (
            instance.id, line_step.id)
            cursor.execute(query)

        return instance


class GlobalParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Global_Parameters
        fields = '__all__'


class PersonalDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personal_Documents
        fields = '__all__'


class MetricsSerializer(serializers.Serializer):
    subdivision_id = serializers.IntegerField()
    from_date = serializers.DateTimeField()
    to_date = serializers.DateTimeField()
    output_data = serializers.ListField()
