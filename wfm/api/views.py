from rest_framework import generics
from ..models import Production_Task, Organization, Subdivision
from .serializers import ProductionTaskSerializer, OrganizationSerializer, SubdivisionSerializer


class ProductionTaskListView(generics.ListAPIView):
    queryset = Production_Task.objects.all()
    serializer_class = ProductionTaskSerializer


class ProductionTaskDetailView(generics.RetrieveAPIView):
    queryset = Production_Task.objects.all()
    serializer_class = ProductionTaskSerializer


class SubdivisionListView(generics.ListAPIView):
    queryset = Subdivision.objects.all()
    serializer_class = SubdivisionSerializer


class SubdivisionDetailView(generics.RetrieveAPIView):
    queryset = Subdivision.objects.all()
    serializer_class = SubdivisionSerializer


class OrganizationListView(generics.ListAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class OrganizationDetailView(generics.RetrieveAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
