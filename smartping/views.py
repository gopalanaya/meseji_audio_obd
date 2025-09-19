from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from smartping.models import VoxUpload, CampaignCreation, SingleVoiceCreation
from django.views.generic.edit import CreateView, DeleteView
from smartping.tables import VoxUploadTable, CampaignCreationTable, SingleVoiceCreationTable
from smartping.forms import VoxUploadForm, SingleVoiceCreationForm, CampaignCreationForm
from django_tables2 import SingleTableView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
import datetime, json
from django.utils import timezone
from smartping.tasks import (
    background_prepare_report,
      background_run_campaign,
     background_update_singlevoice,
     process_dlr)
from smscampaign.models import SmsTemplate
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
@csrf_exempt
def obd_dlr(request):
    """ Parameter required:
     api_key:
     data :  All data for dlr
     method post
    """
    # need to authenticate and check api key
    if request.method == 'POST':
        print(request.body)
        body = json.loads(request.body)
        api_key = body.get('api_key')
        data = body.get('data')
        if api_key == getattr(settings, 'SMARTPING_API_KEY'):
            process_dlr.delay(data)
            return HttpResponse("OK")
        else:
            return HttpResponseNotFound('invalid key')
    
    else:
        return HttpResponse('Method not allowed')


@login_required
def dashboard(request):
    return render(request, template_name='dashboard.html')


class VoxuploadListView(LoginRequiredMixin, SingleTableView):
    model = VoxUpload
    table_class = VoxUploadTable
    template_name = 'smartping/voxupload_list.html'
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return VoxUpload.objects.all()
        return VoxUpload.objects.filter(user=self.request.user)


class VoxuploadFormView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    template_name = "smartping/voxupload_create.html"
    form_class = VoxUploadForm
    success_url = reverse_lazy("smartping:audio_list")
    success_message = "%(filename)s was added successfully"


    def form_valid(self, form):
        if VoxUpload.objects.filter(voiceid='').count() > 0:
            messages.error(self.request, "An Audio is already in Pending to UPload. Try Again")
            return redirect(self.success_url)
        form.instance.user = self.request.user
        return super().form_valid(form)
    




class VoxuploadDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView ):
    template_name = "smartping/voxupload_delete.html"
    success_url = reverse_lazy("smartping:audio_list")
    success_message = "File  was deleted"

    def get_queryset(self):
        return VoxUpload.objects.filter(user=self.request.user)
    
    

class CampaignCreationListView(LoginRequiredMixin,  SingleTableView):
    model = CampaignCreation
    table_class = CampaignCreationTable
    template_name = 'smartping/campaign_list.html'

    def get_queryset(self):
        return CampaignCreation.objects.filter(user=self.request.user)


class CampaignCreateTemplateView(SuccessMessageMixin, CreateView):
    """ This is template for CreateView used in CampaignCreation and SingleVoiceCreation Model
    Reason: Both tables share common features
    """
    success_message = "Campaign Added"
    def get_form(self, form_class = None):
        form =  super().get_form(form_class)
        user = self.request.user
        form.fields['voiceId'].queryset = VoxUpload.objects.filter(user=user, status='APPROVED')
        if SmsTemplate.objects.filter(user=user, is_verified=True).count() == 0:
            # Need to disabled all three fields
            form.fields['sms_required'].disabled = True
            form.fields['duration'].disabled = True
            form.fields['sms_template'].disabled = True
        else:
            form.fields['sms_template'].queryset = SmsTemplate.objects.filter(user=user, is_verified=True)

        return form
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)



class CampaignCreationCreateView(LoginRequiredMixin, CampaignCreateTemplateView):
    template_name = 'smartping/campaign_create.html'
    form_class = CampaignCreationForm
    success_url = reverse_lazy('smartping:campaign_list')



class SingleVoiceCreationListView(LoginRequiredMixin, SingleTableView):
    model = SingleVoiceCreation
    table_class = SingleVoiceCreationTable
    template_name = 'smartping/singlevoicecreation_list.html'

    def get_queryset(self):
        return SingleVoiceCreation.objects.filter(user=self.request.user)
    

class SingleVoiceCreationCreateView(LoginRequiredMixin, CampaignCreateTemplateView):
    template_name = 'smartping/singlevoicecreation_create.html'
    form_class = SingleVoiceCreationForm
    success_url = reverse_lazy('smartping:singlevoice_list')



@login_required
def refresh_voice_status(request, voiceid):
    voice = get_object_or_404(VoxUpload, voiceid=voiceid)
    print(voice.fetch_status())
    return HttpResponseRedirect(reverse_lazy('smartping:audio_list'))




@login_required
def get_campaign_status(request):
    """ This helper function will be called frequently for checking status and download the report
    Need to check if its from Single campaign creation  or Bulk Campaign

    mode : single -> SingleCampaign
           bulk   -> Bulk Campaign
    """
    # check if we able to query string
    mode = request.GET.get('mode', None)
    campaignid = request.GET.get('campaignid', None)
    if not (mode and campaignid):
        return HttpResponseNotFound('Parameter missing: mode, campaignid')
    
    if mode == 'single':
        obj_list = SingleVoiceCreation.objects.filter(campg_id=campaignid)
        if len(obj_list) < 1:
            return HttpResponseNotFound('No Campaign Found')
        for obj in obj_list:
            if obj.status_fetched:
                # need to pass this time
                continue

            status = obj.get_campaign_summary(obj.campg_id)
            if status:
                obj.status = status
                obj.save()
            else:
                # update_singlevoice(obj)
                background_update_singlevoice.delay(obj.id)

        return HttpResponseRedirect(reverse_lazy('smartping:singlevoice_list'))
    
    elif mode == 'bulk':
        # We need to query each campg_id as it is bulk campaign
        obj = get_object_or_404(CampaignCreation, id=campaignid)
        for campg_id in obj.campg_id.split(','):
            if not campg_id:
                # this is fail safe when campg_id is having value like 28398,,238928,,32892,,,89328
                continue
            status = obj.get_campaign_summary(campaignid=campg_id)
            obj.status = status
            if status == 'CLOSE':
                continue
            else:
                # One of the campaign is still running, so break and will check later on
                break
        if obj.status:
            obj.save() # quick fix for null value
        return HttpResponseRedirect(reverse_lazy('smartping:campaign_list'))
    
    else:
        return HttpResponseNotFound('No such mode available')



@login_required
def download_campaign_report(request):
    """" This will download the campaign report
    First check if campaign is_fetched is False or not, True will return else continue
    Then check and download the report
    """
    campgid = request.GET.get('campaignid', None)
    if not campgid:
        return HttpResponseNotFound("No campaign found")
    
    campg_objlist = CampaignCreation.objects.filter(id=campgid)
    if len(campg_objlist) == 0:
        return HttpResponseNotFound('Campaign Not Found')
    
    campg_obj = campg_objlist[0]
    # Need to wait until all number is processed
    audio_duration = campg_obj.voiceId.plantype

    # need to change the time
    if campg_obj.valid_count < 100:
        total_sec = campg_obj.valid_count * audio_duration
    else:
        total_sec = 7200
    report_time = campg_obj.updated_at + datetime.timedelta(seconds=total_sec)
    if timezone.now() > report_time:
        # prepare_report(campg_obj)
        background_prepare_report.delay_on_commit(campg_obj.id)
        messages.info(request, f"We are preparing report for campaign id: {campg_obj.id}")
    else:
        messages.warning(request, "Too Early to get reports. Please wait")
    return HttpResponseRedirect(reverse_lazy('smartping:campaign_list'))


@login_required
def run_campaign(request):
    """ This function will allow user to run campaign from panel"""
    campaignid = request.GET.get('campaignid', None)
    if not campaignid:
        return HttpResponseNotFound('Invalid Action for campaign')
    elif CampaignCreation.objects.filter(id=campaignid, user=request.user).count() == 0:
        return HttpResponseNotFound("No Campaign Found")
    else:
        campgn_obj = CampaignCreation.objects.get(id=campaignid)
        if campgn_obj.is_sent:
            messages.info(request, f'campaign with id {campgn_obj.id} for user: {campgn_obj.user} is already sent')
            return HttpResponseRedirect(reverse_lazy('smartping:campaign_list'))
        else:
            # run_audio_obd(campgn_obj)
            background_run_campaign.delay(campgn_obj.id)
            messages.info(request, f'Campaign id: {campaignid} is started. Please wait 1 minute Before clicking again.')
            # campgn_obj.is_sent = True
            # campgn_obj.save()
            return HttpResponseRedirect(reverse_lazy('smartping:campaign_list'))
            
