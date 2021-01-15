from django import forms
from django.contrib.auth.models import User

from .models import Employee


class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=30)
    last_name = forms.CharField(label='Фамилия', max_length=30)

    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        try:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
        except User:
            pass

    class Meta:
        model = Employee
        exclude = ['user']
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'personnel_number',
            'subdivision',
            'position',
        ]
