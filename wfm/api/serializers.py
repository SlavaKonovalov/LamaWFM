from django.contrib.auth.models import User
from rest_framework import serializers
from ..models import Production_Task, Subdivision, Employee, Scheduled_Production_Task
from ..models import Organization


class ScheduledProductionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheduled_Production_Task
        fields = '__all__'


class ProductionTaskSerializer(serializers.ModelSerializer):
    scheduled_task_set = ScheduledProductionTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Production_Task
        fields = '__all__'


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
