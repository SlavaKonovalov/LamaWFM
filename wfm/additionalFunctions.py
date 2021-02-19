from django.utils import timezone
from datetime import datetime, timedelta
from pytz import utc


class Global:

    @staticmethod
    def add_timezone(initial_date):
        return initial_date.astimezone(timezone.get_default_timezone())

    @staticmethod
    def round_math(value):
        return int(value + (0.5 if value > 0 else -0.5))

    @staticmethod
    def toFixed(num_obj, digits=0):
        return f"{num_obj:.{digits}f}"

    @staticmethod
    def add_timezone(initial_date):
        return initial_date.astimezone(timezone.get_default_timezone())

    @staticmethod
    def strdatetime2datetime(naive_date_time_string):
        naive_datetime = datetime.strptime(naive_date_time_string, '%d.%m.%Y %H:%M:%S')
        current_timezone = timezone.get_current_timezone()
        current_utcoffset_in_seconds = datetime.now(current_timezone).utcoffset().total_seconds()
        utc_naive_datetime = naive_datetime - timedelta(seconds=current_utcoffset_in_seconds)
        local_datetime = utc_naive_datetime.astimezone(timezone.get_default_timezone())
        return local_datetime


