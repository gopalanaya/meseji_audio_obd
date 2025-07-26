from django.shortcuts import render
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from smscampaign.tasks import process_dlr
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from smscampaign.models import SmsTemplate, SmsReport
from smscampaign.forms import SmsTemplateForm, SmsTestForm
import django_tables2 as tables
from django.contrib.auth.mixins import LoginRequiredMixin
from smscampaign.tables import SmsTemplateTable, SmsReportTable
from unidecode import unidecode


# Create your views here.
def sms_dlr(request):
    """ The SMS delivery URL. it should be simple but super fast"""
    track_code = request.GET.get('track_code', None)
    if not track_code:
        return HttpResponse('Parameter missing: track_code', 104)
    delivery_status = request.GET.get('dlr_status', None)
    delivery_msg = request.GET.get('dlr_msg', None)
    process_dlr(track_code=track_code, dlr_status=delivery_status, dlr_msg= delivery_msg)
    return HttpResponse('OK')


class SmsTemplateCreateView(CreateView):
    model = SmsTemplate
    form_class = SmsTemplateForm
    template_name = 'smscampaign/smstemplate_create.html'
    success_url = reverse_lazy('smscampaign:smstemplate_list')


    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)



class SmsTemplateTableView(LoginRequiredMixin,tables.SingleTableView):
    table_class = SmsTemplateTable
    template_name = 'smscampaign/smstemplate_list.html'


    def get_queryset(self):
        if self.request.user.is_staff:
            return SmsTemplate.objects.all()
        
        return SmsTemplate.objects.filter(user=self.request.user)
    

class SmsTemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = SmsTemplate
    template_name = 'smscampaign/smstemplate_delete.html'
    success_url = reverse_lazy('smscampaign:smstemplate_list')


class SmsApproveView(LoginRequiredMixin, UpdateView):
    model = SmsTemplate
    form_class = SmsTestForm
    template_name = 'smscampaign/smstemplate_approve.html'
    success_url = reverse_lazy('smscampaign:smstemplate_list')
    
    def form_valid(self, form):
        form.send_message()
        return super().form_valid(form)
    

class SmsReportTableView(LoginRequiredMixin,tables.SingleTableView):
    table_class = SmsReportTable
    template_name = 'smscampaign/smsreport_list.html'


    def get_queryset(self):
        if self.request.user.is_staff:
            return SmsReport.objects.all()
        
        return SmsReport.objects.filter(user=self.request.user)

def unicodetoascii(request):
    data = {
        'msg': 'not a valid method',
        'status': 'error'
    }
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        msg  = request.GET.get('msg', 'None')
        if msg:
            data['msg'] = unidecode(msg)
            data['status'] = 'success'
     
    return JsonResponse(data)