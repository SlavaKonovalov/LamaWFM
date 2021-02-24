from django.shortcuts import render
from django.http import JsonResponse
from .forms import BusinessIndicatorDownloadForm, DemandByHistoryCalculateForm
from .integration_download_data import BusinessIndicatorDownload4CSV
from .demand_by_history_calculate import DemandByHistoryDataCalculate


def business_indicator_download(request):
    if request.method == 'POST':
        form = BusinessIndicatorDownloadForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = request.FILES['filePath4DownLoad']
            businessIndicatorDownload4CSV = BusinessIndicatorDownload4CSV(csvfile);
            businessIndicatorDownload4CSV.run()
            return JsonResponse({'message': csvfile.name})
        return JsonResponse({'message': 'not ok'})
    else:
        form = BusinessIndicatorDownloadForm()
        return render(request, 'integration\\business_indicator_download.html', {'form': form})


def demand_by_history_calculate(request):
    if request.method == 'POST':
        form = DemandByHistoryCalculateForm(request.POST)
        if form.is_valid():
            subdivision_id = form.cleaned_data['subdivision_id']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']

            demand_by_history_data_calculate = DemandByHistoryDataCalculate(subdivision_id, from_date, to_date)
            # demandByHistoryDataCalculate = DemandByHistoryDataCalculate(subdivision_id,
            #                                                             datetime.fromisoformat('2021-02-01'),
            #                                                             datetime.fromisoformat('2021-02-05'))
            ret = demand_by_history_data_calculate.run()
            return JsonResponse({'message': ret})
        return JsonResponse({'message': 'form not valid'})
    else:
        form = DemandByHistoryCalculateForm()
        return render(request, 'integration\\demand_by_history_calculate.html', {'form': form})
