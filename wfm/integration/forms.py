from django import forms


class BusinessIndicatorDownloadForm(forms.Form):
    filePath4DownLoad = forms.FileField(label="Выберите файл для загрузки ")


class DemandByHistoryCalculateForm(forms.Form):
    subdivision_id = forms.IntegerField(label='Подразделение', help_text='Выберите подразделение:', initial=3)
    from_date = forms.DateTimeField(label='С', help_text='Выберите начальную дату планирования',
                                    widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateTimeField(label='По', help_text='Выберите конечную дату планирования',
                                  widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    history_from_date = forms.DateTimeField(label='С', help_text='Выберите начальную дату истории',
                                    widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    history_to_date = forms.DateTimeField(label='По', help_text='Выберите конечную дату истории',
                                  widget=forms.widgets.DateInput(attrs={'type': 'date'}))
