import datetime as datetime
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from ..demandProcessing import DemandProcessing
from ..integration.demand_by_history_calculate import DemandByHistoryDataCalculate
from ..taskProcessing import TaskProcessing
from ..models import Production_Task, Organization, Subdivision, Employee, Employee_Position, Job_Duty, \
    Appointed_Production_Task, Scheduled_Production_Task, Demand_Detail_Main, Company
from .serializers import ProductionTaskSerializer, OrganizationSerializer, SubdivisionSerializer, EmployeeSerializer, \
    EmployeePositionSerializer, JobDutySerializer, AppointedTaskSerializer, ScheduledProductionTaskSerializer, \
    DemandMainSerializer, CompanySerializer


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
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    history_from_date = data.get('history_from_date')
    history_to_date = data.get('history_to_date')
    try:
        subdivision = Subdivision.objects.get(pk=subdivision_id)
    except Subdivision.DoesNotExist:
        return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)

    demand_by_history_data_calculate = DemandByHistoryDataCalculate(subdivision_id,
                                                                    from_date,
                                                                    to_date,
                                                                    history_from_date,
                                                                    history_to_date)
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
