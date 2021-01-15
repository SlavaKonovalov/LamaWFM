from rest_framework import serializers
from ..models import Production_Task, Subdivision
from ..models import Organization


class ProductionTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Production_Task
        fields = '__all__'


class SubdivisionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subdivision
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    task_set = ProductionTaskSerializer(many=True, read_only=True)
    subdivision_set = SubdivisionSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'
