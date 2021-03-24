from django.contrib.auth.models import User
from rest_framework import serializers
from ..models import Production_Task, Subdivision, Employee, Scheduled_Production_Task, Employee_Position, Job_Duty, \
    Tasks_In_Duty, Appointed_Production_Task, Organization, Demand_Detail_Main, Demand_Detail_Task, Company, \
    Availability_Template, Availability_Template_Data, Employee_Availability_Templates, Planning_Method, \
    Working_Hours_Rate, Work_Shift_Planning_Rule


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


class EmployeeAvailabilityTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee_Availability_Templates
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
