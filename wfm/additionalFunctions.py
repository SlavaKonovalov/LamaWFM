from django.utils import timezone
import datetime
from pytz import utc


class Global:

    @staticmethod
    # Возвращает дату с текущей таймзоной
    def add_timezone(initial_date):
        return initial_date.astimezone(timezone.get_default_timezone())

    @staticmethod
    # Возвращает полночное время текущего дня
    def get_current_midnight(initial_date):
        return Global.add_timezone(datetime.datetime.combine(
            Global.add_timezone(initial_date).date(),
            datetime.time.min
        ))

    @staticmethod
    # Возвращает дату с текущей таймзоной
    def get_combine_datetime(initial_date, initial_time):
        return Global.add_timezone(datetime.datetime.combine(initial_date, initial_time))

    @staticmethod
    # Возвращает разницу в полных неделях между датами
    def get_week_delta(date_from, date_to):
        if date_from > date_to:
            return 0
        date_from_current = date_from
        date_to_current = date_to
        day = datetime.timedelta(days=1)
        while date_from_current.weekday() != 0:
            date_from_current -= day
        while date_to_current.weekday() != 0:
            date_to_current -= day
        return int((date_to_current - date_from_current).days / 7)

    @staticmethod
    # математическое округление
    def round_math(value):
        value = Global.toFixed(value, 2)
        return int(value + (0.5 if value > 0 else -0.5))

    @staticmethod
    # округление до digits знаков после запятой
    def toFixed(num_obj, digits=0):
        return float(f"{num_obj:.{digits}f}")

    @staticmethod
    def strdatetime2datetime(naive_date_time_string):
        naive_datetime = datetime.datetime.strptime(naive_date_time_string, '%d.%m.%Y %H:%M:%S')
        current_timezone = timezone.get_current_timezone()
        current_utcoffset_in_seconds = datetime.datetime.now(current_timezone).utcoffset().total_seconds()
        utc_naive_datetime = naive_datetime - datetime.timedelta(seconds=current_utcoffset_in_seconds)
        local_datetime = utc_naive_datetime.astimezone(timezone.get_default_timezone())
        return local_datetime


