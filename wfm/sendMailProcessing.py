from django.core.mail import send_mail
from django.http import BadHeaderError, JsonResponse
from rest_framework import status


class SendMailProcessing:
    @staticmethod
    def send_mail(subjects, message, from_email, to_email):
        to_email_list = [to_email]
        try:

            send_mail(subjects, message, 'valitovstas@yandex.ru', to_email_list, False, 'valitovstas@yandex.ru', 'Greedisgood990922')
        except BadHeaderError:
            return JsonResponse({'message': 'error to send!'},
                                status=status.HTTP_409_CONFLICT)
        return JsonResponse({'message': 'email sent!'}, status=status.HTTP_200_OK)