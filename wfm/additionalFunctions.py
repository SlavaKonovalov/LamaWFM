from django.utils import timezone


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
