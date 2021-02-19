from django import forms
from django.contrib.auth.models import User
from .models import Employee


class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=30)
    last_name = forms.CharField(label='Фамилия', max_length=30)
    username = forms.CharField(label='Пользователь', max_length=30)

    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        try:
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
        except User.DoesNotExist:
            pass
        except AttributeError:
            pass

    def save(self, commit=True):
        user_entity = self.instance.user
        if user_entity is None:
            user_entity = User.objects.create_user(self.cleaned_data['username'])
        user_entity.first_name = self.cleaned_data['first_name']
        user_entity.last_name = self.cleaned_data['last_name']

        user_entity.save()
        employee_entity = super(EmployeeForm, self).save(commit=False)
        employee_entity.user = user_entity
        if commit:
            employee_entity.save()
        return employee_entity

    class Meta:
        model = Employee
        fields = [
            'username',
            'first_name',
            'middle_name',
            'last_name',
            'personnel_number',
            'subdivision',
            'position',
            'duties',
            'part_time_job_org'
        ]