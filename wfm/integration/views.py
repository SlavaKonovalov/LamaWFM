from django.shortcuts import render
from django.http import JsonResponse
from .forms import BusinessIndicatorDownloadForm, DemandByHistoryCalculateForm
from .integration_download_data import BusinessIndicatorDownload4CSV
from .demand_by_history_calculate import DemandByHistoryDataCalculate
from datetime import datetime


def business_indicator_dowload(request):
    if request.method == 'POST':
        form = BusinessIndicatorDownloadForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = request.FILES['filePath4DowmLoad']
            businessIndicatorDownload4CSV = BusinessIndicatorDownload4CSV(csvfile);
            businessIndicatorDownload4CSV.run()
            return JsonResponse({'message': csvfile.name})
        return JsonResponse({'message': 'not ok'})
    else:
        form = BusinessIndicatorDownloadForm()
        return render(request,'integration\\business_indicator_dowload.html',{'form': form})

def demand_by_history_calculate(request):
    if request.method == 'POST':
        form = DemandByHistoryCalculateForm(request.POST)
        if form.is_valid():
            subdivision_id = form.cleaned_data['subdivision_id']

            demandByHistoryDataCalculate = DemandByHistoryDataCalculate(subdivision_id, datetime(2021, 2,1, 00), datetime(2021, 2, 28, 00))
            ret = demandByHistoryDataCalculate.run()
            return JsonResponse({'message': ret})
        return JsonResponse({'message': 'form not valid'})
    else:
        form = DemandByHistoryCalculateForm()
        return render(request,'integration\\demand_by_history_calculate.html',{'form': form})
