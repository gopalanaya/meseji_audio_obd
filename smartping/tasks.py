from celery import shared_task
from smartping.utils import run_audio_obd, prepare_report, update_singlevoice
from smartping.models import CampaignCreation, SingleVoiceCreation

@shared_task
def background_run_campaign(campaignid):
    campaign_obj = CampaignCreation.objects.get(id=campaignid)
    run_audio_obd(campaign_obj)




@shared_task
def background_prepare_report(campaignid):
    campaign_obj = CampaignCreation.objects.get(id=campaignid)
    prepare_report(campaign_obj)


@shared_task
def background_update_singlevoice(singlevoiceid):
    singlevoiceobj = SingleVoiceCreation.objects.get(id=singlevoiceid)
    update_singlevoice(singlevoiceobj)
