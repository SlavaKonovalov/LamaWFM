from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from rest_framework import status

from .models import Employee, Subdivision


class LoginProcessing:

    @staticmethod
    @transaction.atomic
    def log_in(email, username):
        response_data = {}

        try:
            user = User.objects.get(email=email, username=username)

            if not user.is_active:
                response_data['login'] = 'false'
                response_data['message'] = 'Пользователь не активен'
                response_data['type_user'] = ''
                response_data['subdivision'] = ''
                response_data['organization'] = ''
                response_data['user_name'] = ''
                return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
            if not user.is_superuser:
                response_data['login'] = 'false'
                response_data['message'] = 'У пользователя нет прав доступа'
                response_data['type_user'] = ''
                response_data['subdivision'] = ''
                response_data['organization'] = ''
                response_data['user_name'] = ''
                return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
            groups = user.groups.filter(name='administrator')
            if groups:
                response_data['login'] = 'true'
                response_data['message'] = 'Вход выполнен'
                response_data['type_user'] = 'admin'
                response_data['subdivision'] = 'ALL'
                response_data['organization'] = 'ALL'
                response_data['user_name'] = user.first_name + ' ' + user.last_name
                return JsonResponse(response_data, status=status.HTTP_200_OK)
            else:
                groups = user.groups.filter(name='manager')
                if groups:
                    employee = Employee.objects.get(user_id=user.id)
                    subdivision = Subdivision.objects.get(pk=employee.subdivision_id)
                    response_data['login'] = 'true'
                    response_data['message'] = 'Вход выполнен'
                    response_data['type_user'] = 'manager'
                    response_data['subdivision'] = employee.subdivision_id
                    response_data['organization'] = subdivision.organization_id
                    response_data['user_name'] = user.first_name + ' ' + user.last_name
                    return JsonResponse(response_data, status=status.HTTP_200_OK)
                else:
                    response_data['login'] = 'false'
                    response_data['message'] = 'Пользовательская группа не определена'
                    response_data['type_user'] = ''
                    response_data['subdivision'] = ''
                    response_data['organization'] = ''
                    response_data['user_name'] = ''
                    return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            response_data['login'] = 'false'
            response_data['message'] = 'Пользователь не найден в системе'
            response_data['type_user'] = ''
            response_data['subdivision'] = ''
            response_data['organization'] = ''
            response_data['user_name'] = ''
            return JsonResponse(response_data, status=status.HTTP_401_UNAUTHORIZED)
