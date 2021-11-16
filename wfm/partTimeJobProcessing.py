import datetime

from django.db import transaction

from .models import Part_Time_Job_Vacancy, Part_Time_Job_Employee_Request, Employee_Shift


class PartTimeJobProcessing:

    def __init__(self, serializer):
        self.serializer = serializer
        self.errors = {}

    def check_vacancy(self):
        error_list = {}

        instance_pk = None
        if self.serializer.instance:
            instance_pk = self.serializer.instance.pk
        else:
            # выходим при сохранении нового объекта
            if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})
                self.serializer.error_list = error_list
                return False
            else:
                return True

        job_vacancy_instance = self.serializer.instance

        if self.serializer.validated_data.get('vacancy_status') == 'created':
            if job_vacancy_instance.vacancy_status == 'created':
                if self.serializer.validated_data.get('subdivision') != job_vacancy_instance.subdivision:
                    error_list.update({'subdivision': "Подразделение не может быть изменено!"})

                if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})

        elif self.serializer.validated_data.get('vacancy_status') == 'confirmed':
            if job_vacancy_instance.vacancy_status == 'created':
                if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})

            if job_vacancy_instance.vacancy_status == 'approved':
                error_list.update(
                    {'vacancy_status': "Откат данного статуса вакансии выполнятся через 'Запрос на подработку'!"})

        elif self.serializer.validated_data.get('vacancy_status') == 'approved':
            if job_vacancy_instance.vacancy_status == 'confirmed':
                error_list.update({'vacancy_status': "Утверждение вакансии выполнятся через 'Запрос на подработку'!"})

        if error_list:
            self.serializer.error_list = error_list

        return not bool(self.serializer.error_list)

    def check_request(self):
        error_list = {}

        instance_pk = None
        if self.serializer.instance:
            instance_pk = self.serializer.instance.pk
        else:
            # выходим при сохранении нового объекта
            if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                error_list.update({'requested_date': "Дата вакансии должна быть позже текущей"})
                self.serializer.error_list = error_list
                return False
            else:
                return True

        job_request_instance = self.serializer.instance

        if self.serializer.validated_data.get('request_status') == 'created':
            if job_request_instance.request_status == 'created':
                if self.serializer.validated_data.get('employee') != job_request_instance.employee:
                    error_list.update({'employee': "Сотрудник не может быть изменен!"})

                if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата запроса должна быть позже текущей"})

        elif self.serializer.validated_data.get('request_status') == 'published':
            if job_request_instance.request_status == 'created':
                if self.serializer.validated_data.get('requested_date') <= datetime.date.today():
                    error_list.update({'requested_date': "Дата запроса должна быть позже текущей"})

                # проверка смены на этот день по сотруднику
                employee_shift = Employee_Shift.objects.select_related('subdivision').filter(
                    employee_id=self.serializer.validated_data.get('employee'),
                    shift_date=self.serializer.validated_data.get('requested_date')).first()
                if employee_shift:
                    error_list.update({'message': "Сотруднику назначена смена на этот день! Подразделение: "
                                                  + employee_shift.subdivision.name})

            elif job_request_instance.request_status == 'shift_created':
                vacancy = self.serializer.validated_data.get('vacancy')
                if vacancy is None:
                    error_list.update({'vacancy': "Отсутствует ссылка на вакансию!"})

        elif self.serializer.validated_data.get('request_status') == 'shift_created':
            if job_request_instance.request_status == 'published':
                vacancy = self.serializer.validated_data.get('vacancy')
                if vacancy is None:
                    error_list.update({'vacancy': "Отсутствует ссылка на вакансию!"})

        if error_list:
            self.serializer.error_list = error_list

        return not bool(self.serializer.error_list)

    @transaction.atomic
    def update_request(self):
        job_request_id = self.serializer.validated_data.get('id')
        try:
            job_request = Part_Time_Job_Employee_Request.objects.get(pk=job_request_id)
        except Part_Time_Job_Employee_Request.DoesNotExist:
            self.serializer.error_list.update({'message': 'The job request does not exist'})
            return False

        request_status = self.serializer.validated_data.get('request_status')
        if request_status == 'shift_created':
            if job_request.request_status == 'published':
                # проверка вакансии
                try:
                    job_vacancy = Part_Time_Job_Vacancy.objects.get(pk=self.serializer.validated_data.get('vacancy').pk)
                except Part_Time_Job_Vacancy.DoesNotExist:
                    self.serializer.error_list.update({'message': 'The job vacancy does not exist'})
                    return False
                # обновление вакансии
                if job_vacancy.vacancy_status == 'confirmed':
                    job_vacancy.vacancy_status = 'approved'
                    job_vacancy.save(update_fields=['vacancy_status'])
                # TODO создание смены

        if request_status == 'published':
            if job_request.request_status == 'shift_created':
                # проверка вакансии
                try:
                    job_vacancy = Part_Time_Job_Vacancy.objects.get(pk=self.serializer.validated_data.get('vacancy').pk)
                except Part_Time_Job_Vacancy.DoesNotExist:
                    self.serializer.error_list.update({'message': 'The job vacancy does not exist'})
                    return False
                # TODO удаление смены
                # откат статуса вакансии
                if job_vacancy.vacancy_status == 'approved':
                    job_vacancy.vacancy_status = 'confirmed'
                    job_vacancy.save(update_fields=['vacancy_status'])

        self.serializer.validated_data['vacancy'] = None
        if self.serializer.is_valid():
            self.serializer.save()
        return True
