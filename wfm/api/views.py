import datetime as datetime
import dateutil.parser
from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from dateutil.relativedelta import relativedelta

from ..additionalFunctions import Global
from ..availabilityProcessing import AvailabilityProcessing
from ..demandProcessing import DemandProcessing
from ..integration.demand_by_history_calculate import DemandByHistoryDataCalculate
from ..integration.integration_download_data import CreateEmployeesByUploadedData
from ..shiftPlanning import ShiftPlanning
from ..taskProcessing import TaskProcessing
from ..models import Production_Task, Organization, Subdivision, Employee, Employee_Position, Job_Duty, \
    Appointed_Production_Task, Scheduled_Production_Task, Demand_Detail_Main, Company, Availability_Template, \
    Employee_Availability_Templates, Availability_Template_Data, Planning_Method, Working_Hours_Rate, \
    Work_Shift_Planning_Rule, Breaking_Rule, Employee_Planning_Rules, Employee_Availability, Employee_Shift, Holiday, \
    Retail_Store_Format, Open_Shift, Demand_Hour_Main, Demand_Hour_Shift
from .serializers import ProductionTaskSerializer, OrganizationSerializer, SubdivisionSerializer, EmployeeSerializer, \
    EmployeePositionSerializer, JobDutySerializer, AppointedTaskSerializer, ScheduledProductionTaskSerializer, \
    DemandMainSerializer, CompanySerializer, AvailabilityTemplateSerializer, EmployeeAvailabilityTemplatesSerializer, \
    EmployeeAvailabilityTemplateSerializer, PlanningMethodSerializer, WorkingHoursRateSerializer, \
    WorkShiftPlanningRuleSerializer, BreakingRuleSerializer, EmployeePlanningRuleSerializer, \
    AssignEmployeePlanningRulesSerializer, EmployeeAvailabilitySerializer, EmployeeShiftSerializer, HolidaySerializer, \
    RetailStoreFormatSerializer, EmployeeShiftSerializerForUpdate, OpenShiftSerializer, OpenShiftSerializerHeader, \
    EmployeeShiftSerializerHeader, EmployeeUpdateSerializer


class ProductionTaskListView(generics.ListAPIView):
    serializer_class = ProductionTaskSerializer

    def get_queryset(self):
        queryset = Production_Task.objects.all()
        org_id = self.request.query_params.get('org_id', None)
        if org_id is not None:
            queryset = queryset.filter(organization_id=org_id)

        return queryset


class ProductionTaskDetailView(generics.RetrieveAPIView):
    queryset = Production_Task.objects.all()
    serializer_class = ProductionTaskSerializer


@api_view(['GET', 'POST'])
def scheduled_task_list(request):
    if request.method == 'GET':
        scheduled_tasks = Scheduled_Production_Task.objects.all()

        scheduled_task_serializer = ScheduledProductionTaskSerializer(scheduled_tasks, many=True)
        return JsonResponse(scheduled_task_serializer.data, safe=False)

    elif request.method == 'POST':
        scheduled_task_data = JSONParser().parse(request)
        scheduled_task_serializer = ScheduledProductionTaskSerializer(data=scheduled_task_data)
        if scheduled_task_serializer.is_valid():
            scheduled_task_serializer.save()
            return JsonResponse(scheduled_task_serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(scheduled_task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'DELETE'])
def scheduled_task_detail(request, pk):
    try:
        scheduled_task = Scheduled_Production_Task.objects.get(pk=pk)
    except Scheduled_Production_Task.DoesNotExist:
        return JsonResponse({'message': 'The scheduled task does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        scheduled_task_serializer = ScheduledProductionTaskSerializer(scheduled_task)
        return JsonResponse(scheduled_task_serializer.data)

    elif request.method == 'POST':
        scheduled_task_data = JSONParser().parse(request)
        scheduled_task_serializer = ScheduledProductionTaskSerializer(scheduled_task, data=scheduled_task_data)
        if scheduled_task_serializer.is_valid():
            scheduled_task_serializer.save()
            return JsonResponse(scheduled_task_serializer.data)
        return JsonResponse(scheduled_task_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        scheduled_task.delete()
        return JsonResponse({'message': 'Scheduled task was deleted successfully!'},
                            status=status.HTTP_204_NO_CONTENT)


class SubdivisionListView(generics.ListAPIView):
    serializer_class = SubdivisionSerializer

    def get_queryset(self):
        queryset = Subdivision.objects.all()
        org_id = self.request.query_params.get('org_id', None)
        if org_id is not None:
            queryset = queryset.filter(organization_id=org_id)
        return queryset


class SubdivisionDetailView(generics.RetrieveAPIView):
    queryset = Subdivision.objects.all()
    serializer_class = SubdivisionSerializer


# class OrganizationListView(generics.ListAPIView):
#     queryset = Organization.objects.all()
#     serializer_class = OrganizationSerializer
#
#
# class OrganizationDetailView(generics.RetrieveAPIView):
#     queryset = Organization.objects.all()
#     serializer_class = OrganizationSerializer


@api_view(['GET', 'POST'])
def organization_list(request):
    if request.method == 'GET':
        organizations = Organization.objects.all()

        organization_serializer = OrganizationSerializer(organizations, many=True)
        return JsonResponse(organization_serializer.data, safe=False)

    elif request.method == 'POST':
        organization_data = JSONParser().parse(request)
        organization_serializer = OrganizationSerializer(data=organization_data)
        if organization_serializer.is_valid():
            organization_serializer.save()
            return JsonResponse(organization_serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(organization_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'DELETE'])
def organization_detail(request, pk):
    try:
        organization = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return JsonResponse({'message': 'The organization does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        organization_serializer = OrganizationSerializer(organization)
        return JsonResponse(organization_serializer.data)

    elif request.method == 'POST':
        organization_data = JSONParser().parse(request)
        organization_serializer = OrganizationSerializer(organization, data=organization_data)
        if organization_serializer.is_valid():
            organization_serializer.save()
            return JsonResponse(organization_serializer.data)
        return JsonResponse(organization_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        organization.delete()
        return JsonResponse({'message': 'Organization was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


class EmployeePositionListView(generics.ListAPIView):
    serializer_class = EmployeePositionSerializer

    def get_queryset(self):
        queryset = Employee_Position.objects.all()
        org_id = self.request.query_params.get('org_id', None)
        if org_id is not None:
            queryset = queryset.filter(organization_id=org_id)
        return queryset


class EmployeeAvailabilityTemplatesView(generics.ListAPIView):
    serializer_class = EmployeeAvailabilityTemplatesSerializer

    def get_queryset(self):
        queryset = Employee_Availability_Templates.objects.all()
        empl_id = self.request.query_params.get('empl_id', None)
        if empl_id is not None:
            queryset = queryset.filter(employee_id=empl_id)
        return queryset


class EmployeeAvailabilityView(generics.ListAPIView):
    serializer_class = EmployeeAvailabilitySerializer

    def get_queryset(self):
        queryset = Employee_Availability.objects.all()
        employee_id = self.request.query_params.get('employee_id', None)
        subdivision_id = self.request.query_params.get('subdivision_id', None)
        if employee_id is not None and subdivision_id is not None:
            queryset = queryset.filter(employee_id=employee_id, subdivision_id=subdivision_id)
        elif employee_id is not None and subdivision_id is None:
            queryset = queryset.filter(employee_id=employee_id)
        elif employee_id is None and subdivision_id is not None:
            queryset = queryset.filter(subdivision_id=subdivision_id)
        return queryset


class EmployeePlanningRuleView(generics.ListAPIView):
    serializer_class = EmployeePlanningRuleSerializer

    def get_queryset(self):
        queryset = Employee_Planning_Rules.objects.all()
        empl_id = self.request.query_params.get('empl_id', None)
        if empl_id is not None:
            queryset = queryset.filter(employee_id=empl_id)
        return queryset


class PlanningMethodView(generics.ListAPIView):
    serializer_class = PlanningMethodSerializer

    def get_queryset(self):
        queryset = Planning_Method.objects.all()
        self_id = self.request.query_params.get('id', None)
        if self_id is not None:
            queryset = queryset.filter(id=self_id)
        return queryset


class WorkingHoursRateView(generics.ListAPIView):
    serializer_class = WorkingHoursRateSerializer

    def get_queryset(self):
        queryset = Working_Hours_Rate.objects.all()
        return queryset


class WorkShiftPlanningRuleView(generics.ListAPIView):
    serializer_class = WorkShiftPlanningRuleSerializer

    def get_queryset(self):
        queryset = Work_Shift_Planning_Rule.objects.all()
        return queryset


class BreakingRuleView(generics.ListAPIView):
    serializer_class = BreakingRuleSerializer

    def get_queryset(self):
        queryset = Breaking_Rule.objects.all()
        return queryset


class EmployeePositionDetailView(generics.RetrieveAPIView):
    queryset = Employee_Position.objects.all()
    serializer_class = EmployeePositionSerializer


class JobDutyListView(generics.ListAPIView):
    serializer_class = JobDutySerializer

    def get_queryset(self):
        queryset = Job_Duty.objects.all()
        org_id = self.request.query_params.get('org_id', None)
        if org_id is not None:
            queryset = queryset.filter(organization_id=org_id)
        return queryset


class JobDutyDetailView(generics.RetrieveAPIView):
    queryset = Job_Duty.objects.all()
    serializer_class = JobDutySerializer


class EmployeeListView(generics.ListAPIView):
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        queryset = Employee.objects.all()
        subdivision_id = self.request.query_params.get('subdivision_id', None)
        if subdivision_id is not None:
            queryset = queryset.filter(subdivision_id=subdivision_id)
        return queryset


class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class DemandMainListView(generics.ListAPIView):
    serializer_class = DemandMainSerializer

    def get_queryset(self):
        queryset = Demand_Detail_Main.objects.all()
        subdivision_id = self.request.query_params.get('subdivision_id', None)
        date_from_str = self.request.query_params.get('date_from', None)
        date_to_str = self.request.query_params.get('date_to', None)
        if subdivision_id is not None and date_from_str is not None and date_to_str is not None:
            date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d")
            date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d")
            queryset = queryset.filter(subdivision_id=subdivision_id)
            queryset = queryset.filter(date_time_value__range=[
                datetime.datetime.combine(date_from, datetime.time.min),
                datetime.datetime.combine(date_to, datetime.time.max)
            ])

        return queryset


class AppointedTaskListView(generics.ListAPIView):
    serializer_class = AppointedTaskSerializer

    def get_queryset(self):
        queryset = Appointed_Production_Task.objects.all()
        subdivision_id = self.request.query_params.get('subdivision_id', None)
        date_from_str = self.request.query_params.get('date_from', None)
        date_to_str = self.request.query_params.get('date_to', None)
        if subdivision_id is not None and date_from_str is not None and date_to_str is not None:
            date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d")
            date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d")
            queryset = queryset.filter(scheduled_task__subdivision_id=subdivision_id).select_related('scheduled_task')
            queryset = queryset.filter(date__range=[
                datetime.datetime.combine(date_from, datetime.time.min),
                datetime.datetime.combine(date_to, datetime.time.max)
            ])
        else:
            queryset = None
        return queryset


@api_view(['POST'])
def recalculate_history_demand(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    from_date_str = data.get('from_date')
    from_date = datetime.datetime.strptime(from_date_str, "%Y-%m-%d")
    datetime.datetime.combine(from_date, datetime.time.min)
    to_date_str = data.get('to_date')
    to_date = datetime.datetime.strptime(to_date_str, "%Y-%m-%d")
    datetime.datetime.combine(to_date, datetime.time.max)
    try:
        Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)

    demand_by_history_data_calculate = DemandByHistoryDataCalculate(subdivision_id,
                                                                    from_date,
                                                                    to_date)
    demand_by_history_data_calculate.run()

    return JsonResponse({'message': 'request processed'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def recalculate_demand(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    response = DemandProcessing.recalculate_demand(subdivision_id)
    return response


@api_view(['POST'])
def assign_tasks(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    scheduled_task_id = data.get('scheduled_task_id')
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if scheduled_task_id:
        try:
            scheduled_task = Scheduled_Production_Task.objects.get(pk=scheduled_task_id,
                                                                   subdivision_id=subdivision_id)
        except Scheduled_Production_Task.DoesNotExist:
            return JsonResponse({'message': 'The scheduled task does not exist'}, status=status.HTTP_404_NOT_FOUND)
    TaskProcessing.assign_tasks(subdivision_id, scheduled_task_id)
    return JsonResponse({'message': 'request processed'}, status=status.HTTP_204_NO_CONTENT)


class CompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer

    def get_queryset(self):
        queryset = Company.objects.all()
        return queryset


@api_view(['GET', 'POST'])
def availability_template_list(request):
    if request.method == 'GET':
        availability_template = Availability_Template.objects.all()

        availability_template_serializer = AvailabilityTemplateSerializer(availability_template, many=True)
        return JsonResponse(availability_template_serializer.data, safe=False)

    elif request.method == 'POST':
        availability_template_data = JSONParser().parse(request)
        availability_template_serializer = AvailabilityTemplateSerializer(data=availability_template_data)
        if availability_template_serializer.is_valid():
            availability_template_serializer.save()
            return JsonResponse(availability_template_serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(availability_template_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'DELETE'])
def availability_template_detail(request, pk):
    try:
        availability_template = Availability_Template.objects.get(pk=pk)
    except Availability_Template.DoesNotExist:
        return JsonResponse({'message': 'The organization does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        availability_template_serializer = AvailabilityTemplateSerializer(availability_template)
        return JsonResponse(availability_template_serializer.data)

    elif request.method == 'POST':
        availability_template_data = JSONParser().parse(request)
        availability_template_serializer = AvailabilityTemplateSerializer(availability_template,
                                                                          data=availability_template_data)
        if availability_template_serializer.is_valid():
            availability_template_serializer.save()
            return JsonResponse(availability_template_serializer.data)
        return JsonResponse(availability_template_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        availability_template.delete()
        return JsonResponse({'message': 'Organization was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
def availability_template_data_detail(request, pk):
    try:
        availability_template_data = Availability_Template_Data.objects.get(pk=pk)
    except Availability_Template_Data.DoesNotExist:
        return JsonResponse({'message': 'The organization does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        availability_template_data.delete()
        return JsonResponse({'message': 'Organization was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def assign_employee_availability_template(request):
    data = JSONParser().parse(request)
    eat_serializer = EmployeeAvailabilityTemplateSerializer(data=data)
    if eat_serializer.is_valid():
        employee_id = data.get('employee')
        template_id = data.get('template')
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return JsonResponse({'message': 'The employee does not exist'}, status=status.HTTP_404_NOT_FOUND)
        try:
            template = Availability_Template.objects.get(pk=template_id)
        except Availability_Template.DoesNotExist:
            return JsonResponse({'message': 'The template does not exist'}, status=status.HTTP_404_NOT_FOUND)
        response = AvailabilityProcessing.assign_availability_template(eat_serializer)
        return response
    return JsonResponse(eat_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def assign_employee_planning_rules(request):
    data = JSONParser().parse(request)
    epr_serializer = AssignEmployeePlanningRulesSerializer(data=data)
    if epr_serializer.is_valid():
        employee_id = data.get('employee')
        working_hours_rate_id = data.get('working_hours_rate')
        planning_method_id = data.get('planning_method')
        breaking_rule_id = data.get('breaking_rule')
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return JsonResponse({'message': 'The employee does not exist'}, status=status.HTTP_404_NOT_FOUND)
        try:
            working = Working_Hours_Rate.objects.get(pk=working_hours_rate_id)
        except Working_Hours_Rate.DoesNotExist:
            return JsonResponse({'message': 'The workingHoursRate does not exist'}, status=status.HTTP_404_NOT_FOUND)
        try:
            planning = Planning_Method.objects.get(pk=planning_method_id)
        except Planning_Method.DoesNotExist:
            return JsonResponse({'message': 'The planningMethod does not exist'}, status=status.HTTP_404_NOT_FOUND)
        try:
            breaking = Breaking_Rule.objects.get(pk=breaking_rule_id)
        except Breaking_Rule.DoesNotExist:
            return JsonResponse({'message': 'The breakingRule does not exist'}, status=status.HTTP_404_NOT_FOUND)
        response = ShiftPlanning.assign_employee_planning_rules(epr_serializer)
        return response
    return JsonResponse(epr_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def recalculate_availability(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    employee_id = data.get('employee_id')
    begin_date = dateutil.parser.parse(data.get('begin_date'))
    end_date = dateutil.parser.parse(data.get('end_date'))
    tomorrow_day = Global.get_current_midnight(datetime.datetime.now()) + datetime.timedelta(days=1)
    begin_date = max(begin_date, tomorrow_day)
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if employee_id:
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return JsonResponse({'message': 'The employee does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if begin_date is None or end_date is None or begin_date >= end_date:
        return JsonResponse({'message': 'Wrong date parameters'}, status=status.HTTP_400_BAD_REQUEST)
    response = AvailabilityProcessing.recalculate_availability(subdivision_id, begin_date, end_date, employee_id)
    return response


@api_view(['POST'])
def plan_shifts(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    employees = data.get('employees')
    begin_date = dateutil.parser.parse(data.get('begin_date'))
    end_date = dateutil.parser.parse(data.get('end_date'))
    tomorrow_day = Global.get_current_midnight(datetime.datetime.now()) + datetime.timedelta(days=1)
    begin_date = max(begin_date, tomorrow_day)
    # Обрезаем end_date до начала следующего месяца
    next_month_begin = (begin_date + relativedelta(months=1)).replace(day=1)
    if end_date > next_month_begin:
        end_date = next_month_begin
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    employee_list = []
    if employees:
        for employee_step in employees:
            employee_id = employee_step.get('employee_id')
            try:
                employee = Employee.objects.get(pk=employee_id)
                employee_list.append(employee_id)
            except Employee.DoesNotExist:
                return JsonResponse({'message': 'The employee does not exist'}, status=status.HTTP_404_NOT_FOUND)
    if begin_date is None or end_date is None or begin_date >= end_date:
        return JsonResponse({'message': 'Wrong date parameters'}, status=status.HTTP_400_BAD_REQUEST)
    ShiftPlanning.plan_shifts(subdivision_id, begin_date, end_date, employee_list)
    return JsonResponse({'message': 'Scheduled task was deleted successfully!'},
                        status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def create_employees_by_uploaded_data(request):
    try:
        with transaction.atomic():
            create_employees_by_uploaded_data = CreateEmployeesByUploadedData()
            create_employees_by_uploaded_data.run()
        return JsonResponse({'message': 'employees were loaded'}, status=status.HTTP_200_OK)
    except BaseException as e:
        return JsonResponse({'message': 'internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeShiftView(generics.ListAPIView):
    serializer_class = EmployeeShiftSerializer

    def get_queryset(self):
        queryset = Employee_Shift.objects.all()
        subdivision_id = self.request.query_params.get('subdivision_id', None)
        if subdivision_id is not None:
            queryset = queryset.filter(subdivision_id=subdivision_id)
        employee_id = self.request.query_params.get('employee_id', None)
        if employee_id is not None:
            queryset = queryset.filter(employee_id=employee_id)
        date_from_str = self.request.query_params.get('date_from', None)
        date_to_str = self.request.query_params.get('date_to', None)
        if date_from_str is not None and date_to_str is not None:
            date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d").date()
            date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d").date()
            queryset = queryset.filter(shift_date__range=[date_from, date_to])
        return queryset


@api_view(['POST'])
def employee_shift_plan_create(request):

    if request.method == 'POST':
        employee_shift_plan_request = JSONParser().parse(request)
        employee_shift_plan_serializer = EmployeeShiftSerializerHeader(data=employee_shift_plan_request)
        if employee_shift_plan_serializer.is_valid():
            employee_shift_plan_serializer.save()
            return JsonResponse(employee_shift_plan_serializer.data)
        return JsonResponse(employee_shift_plan_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'DELETE'])
def employee_shift_plan_data(request, pk):
    try:
        employee_shift_plan = Employee_Shift.objects.get(pk=pk)
    except Employee_Shift.DoesNotExist:
        return JsonResponse({'message': 'The shift does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        employee_shift_plan_serializer = EmployeeShiftSerializerForUpdate(employee_shift_plan)
        return JsonResponse(employee_shift_plan_serializer.data)

    elif request.method == 'POST':
        employee_shift_plan_request = JSONParser().parse(request)
        employee_shift_plan_serializer = EmployeeShiftSerializerForUpdate(employee_shift_plan,
                                                                          data=employee_shift_plan_request)
        if employee_shift_plan_serializer.is_valid():
            employee_shift_plan_serializer.save()
            return JsonResponse(employee_shift_plan_serializer.data)
        return JsonResponse(employee_shift_plan_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        employee_shift_plan.delete()
        return JsonResponse({'message': 'Shift was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


class HolidayListView(generics.ListAPIView):
    serializer_class = HolidaySerializer

    def get_queryset(self):
        queryset = Holiday.objects.all()
        return queryset


class RetailStoreFormatView(generics.ListAPIView):
    serializer_class = RetailStoreFormatSerializer

    def get_queryset(self):
        queryset = Retail_Store_Format.objects.all()
        return queryset


@api_view(['GET', 'POST'])
def open_shift_data(request):

    if request.method == 'GET':
        subdivision_id = request.query_params.get('subdivision_id', None)
        open_shift = Open_Shift.objects.all()
        if subdivision_id is not None:
            open_shift = open_shift.filter(subdivision_id=subdivision_id)
        open_shift_serializer = OpenShiftSerializer(open_shift, many=True)
        return JsonResponse(open_shift_serializer.data, safe=False)

    elif request.method == 'POST':
        open_shift_request = JSONParser().parse(request)
        open_shift_serializer = OpenShiftSerializerHeader(data=open_shift_request)
        if open_shift_serializer.is_valid():
            open_shift_serializer.save()
            return JsonResponse(open_shift_serializer.data)
        return JsonResponse(open_shift_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST', 'DELETE'])
def open_shift_data_detail(request, pk):
    try:
        open_shift = Open_Shift.objects.get(pk=pk)
    except Open_Shift.DoesNotExist:
        return JsonResponse({'message': 'The open shift does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        open_shift_serializer = OpenShiftSerializer(open_shift)
        return JsonResponse(open_shift_serializer.data)

    elif request.method == 'POST':
        open_shift_request = JSONParser().parse(request)
        open_shift_serializer = OpenShiftSerializer(open_shift, data=open_shift_request)
        if open_shift_serializer.is_valid():
            open_shift_serializer.save()
            return JsonResponse(open_shift_serializer.data)
        return JsonResponse(open_shift_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        open_shift.delete()
        return JsonResponse({'message': 'Open shift was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def employees_update(request, pk):
    try:
        employee = Employee.objects.get(pk=pk)
    except employee.DoesNotExist:
        return JsonResponse({'message': 'The employee does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        employee_request = JSONParser().parse(request)
        employee_serializer = EmployeeUpdateSerializer(employee, employee_request)
        if employee_serializer.is_valid():
            employee_serializer.save()
            return JsonResponse(employee_serializer.data)
        return JsonResponse(employee_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def add_shift_to_demand_on_hour(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    demand_date = data.get('demand_date', None)
    duty_id = data.get('duty_id')
    try:
        duty = Job_Duty.objects.get(pk=duty_id)
    except duty.DoesNotExist:
        return JsonResponse({'message': 'The duty does not exist'}, status=status.HTTP_404_NOT_FOUND)
    shift_id = data.get('shift_id')
    try:
        shift = Employee_Shift.objects.get(pk=shift_id)
    except shift.DoesNotExist:
        return JsonResponse({'message': 'The shift does not exist'}, status=status.HTTP_404_NOT_FOUND)
    hour = data.get('hour', None)
    try:
        DemandProcessing.add_shift_to_demand_on_hour(subdivision_id, demand_date, duty_id, shift_id, hour)
    except Exception:
        return JsonResponse({'message': 'Error'}, status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({'message': 'Succses'}, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def delete_shift_to_demand(request, pk):

    if request.method == 'DELETE':
        try:
            demand_hour_shift = Demand_Hour_Shift.objects.get(pk=pk)
        except demand_hour_shift.DoesNotExist:
            return JsonResponse({'message': 'The demand_hour_shift does not exist'}, status=status.HTTP_404_NOT_FOUND)
        demand_hour_shift.delete()
        return JsonResponse({'message': 'demand_hour_shift was deleted successfully!'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def recalculate_covering_on_date(request):
    data = JSONParser().parse(request)
    subdivision_id = data.get('subdivision_id')
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)
    demand_date = data.get('demand_date', None)
    try:
        DemandProcessing.recalculate_covering_on_date(subdivision_id, demand_date)
    except Exception:
        return JsonResponse({'message': 'Error'}, status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({'message': 'Succses'}, status=status.HTTP_201_CREATED)







