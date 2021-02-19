from django import forms

class BusinessIndicatorDownloadForm(forms.Form):
  filePath4DowmLoad = forms.FileField(label="Выберите файл для загрузки ")


class DemandByHistoryCalculateForm(forms.Form):
  subdivision_id = forms.IntegerField(label='Подразделение', help_text='Выберите подразделение:')

