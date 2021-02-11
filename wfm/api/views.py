import datetime as datetime
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from ..demandProcessing import DemandProcessing
from ..taskProcessing import TaskProcessing
from ..forms import RecalculateDemandForm
from ..models import Production_Task, Organization, Subdivision, Employee, Employee_Position, Job_Duty, \
    Appointed_Production_Task, Scheduled_Production_Task
from .serializers import ProductionTaskSerializer, OrganizationSerializer, SubdivisionSerializer, EmployeeSerializer, \
    EmployeePositionSerializer, JobDutySerializer, AppointedTaskSerializer


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
        subdiv_id = self.request.query_params.get('subdiv_id', None)
        if subdiv_id is not None:
            queryset = queryset.filter(subdivision_id=subdiv_id)
        return queryset


class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class AppointedTaskListView(generics.ListAPIView):
    serializer_class = AppointedTaskSerializer

    def get_queryset(self):
        queryset = Appointed_Production_Task.objects.all()
        subdiv_id = self.request.query_params.get('subdiv_id', None)
        date_from_str = self.request.query_params.get('date_from', None)
        date_to_str = self.request.query_params.get('date_to', None)
        if subdiv_id is not None and date_from_str is not None and date_to_str is not None:
            date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d")
            date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d")
            queryset = queryset.filter(scheduled_task__subdivision_id=subdiv_id).select_related('scheduled_task')
            queryset = queryset.filter(date__range=[
                datetime.datetime.combine(date_from, datetime.time.min),
                datetime.datetime.combine(date_to, datetime.time.max)
            ])
        else:
            queryset = None
        return queryset


@api_view(['GET', 'POST'])
def recalculate_demand_request(request):
    if request.method == 'POST':
        # Создаем экземпляр формы и заполняем данными из запроса (связывание, binding):
        form = RecalculateDemandForm(request.POST)

        # Проверка валидности данных формы:
        if form.is_valid():
            # Обработка данных из form.cleaned_data
            subdiv_id = form.cleaned_data['subdiv_id']
            date = form.cleaned_data['date']

            try:
                subdivision = Subdivision.objects.get(pk=subdiv_id)
            except Subdivision.DoesNotExist:
                return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)

            if subdivision is not None:
                DemandProcessing.recalculate_demand_on_date(subdivision, date)
                return JsonResponse({'message': 'request processed'}, status=status.HTTP_202_ACCEPTED)
            else:
                return JsonResponse({'message': 'request denied!'}, status=status.HTTP_409_CONFLICT)
        else:
            return JsonResponse({'message': 'Invalid data!'}, status=status.HTTP_409_CONFLICT)

    # Если это GET (или какой-либо еще), создать форму по умолчанию.
    else:
        form = RecalculateDemandForm()
    return render(request, 'test.html', {'form': form})


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
