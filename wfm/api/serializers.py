from django.contrib.auth.models import User
from rest_framework import serializers
from ..models import Production_Task, Subdivision, Employee, Scheduled_Production_Task, Employee_Position, Job_Duty, \
    Tasks_In_Duty, Appointed_Production_Task, Organization, Demand_Detail_Main, Demand_Detail_Task, Company

class ScheduledProductionTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Scheduled_Production_Task
        fields = '__all__'


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