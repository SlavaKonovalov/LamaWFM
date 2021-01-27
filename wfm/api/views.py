from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser

from ..forms import RecalculateDemandForm
from ..models import Production_Task, Organization, Subdivision, Employee
from .serializers import ProductionTaskSerializer, OrganizationSerializer, SubdivisionSerializer, EmployeeSerializer


class ProductionTaskListView(generics.ListAPIView):
    queryset = Production_Task.objects.all()
    serializer_class = ProductionTaskSerializer


class ProductionTaskDetailView(generics.RetrieveAPIView):
    queryset = Production_Task.objects.all()
    serializer_class = ProductionTaskSerializer


class SubdivisionListView(generics.ListAPIView):
    serializer_class = SubdivisionSerializer

    def get_queryset(self):
        queryset = Subdivision.objects.all()
        org_id = self.request.query_params.get('org_id', None)
        if org_id is not None:
            queryset = queryset.filter(organization__id=org_id)
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


class EmployeeListView(generics.ListAPIView):
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        queryset = Employee.objects.all()
        subdiv_id = self.request.query_params.get('subdiv_id', None)
        if subdiv_id is not None:
            queryset = queryset.filter(subdivision__id=subdiv_id)
        return queryset


class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


@api_view(['GET', 'POST'])
def recalculate_demand(request):
    if request.method == 'POST':
        # Создаем экземпляр формы и заполняем данными из запроса (связывание, binding):
        form = RecalculateDemandForm(request.POST)

        # Проверка валидности данных формы:
        if form.is_valid():
            # Обработка данных из form.cleaned_data
            subdiv_id = form.cleaned_data['subdiv_id']

            try:
                subdivision = Subdivision.objects.get(pk=subdiv_id)
            except Subdivision.DoesNotExist:
                return JsonResponse({'message': 'The subdivision does not exist'}, status=status.HTTP_404_NOT_FOUND)

            if subdivision is not None:
                return JsonResponse({'message': 'request received!'}, status=status.HTTP_202_ACCEPTED)
            else:
                return JsonResponse({'message': 'request denied!'}, status=status.HTTP_409_CONFLICT)

    # Если это GET (или какой-либо еще), создать форму по умолчанию.
    else:
        form = RecalculateDemandForm()

    return render(request, 'test.html', {'form': form})
