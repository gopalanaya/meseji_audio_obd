from celery import shared_task
from smartping.utils import run_audio_obd, prepare_report, update_singlevoice
from smartping.models import CampaignCreation, SingleVoiceCreation, CampaignSmsTracker
from django.conf import settings
import datetime, csv
from django.core.cache import cache

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

def dump_data(filename, data_dict):
    """ This will just dump data in file"""
    
    headers = list(data_dict.keys())
    with open(filename, 'a') as f:
        csv_writer = csv.DictWriter(f,
                delimiter=',',
                lineterminator='\n',
                fieldnames=headers
                )
        if f.tell() == 0:
            csv_writer.writeheader()

        csv_writer.writerow(data_dict)


def check_sms_campaign_tracker(data):
    """ This function will check if campaign sms tracker exists or not
        If not exists, create empty entry
    """
    campaignid = data['CAMPAIGN_ID']
    campaign_cache_key = 'cmgn_tracker_{}'.format(campaignid)
    if not cache.get(campaign_cache_key):
        # create tracker object from CampaignSmsTracker, need to save empty results sets too
        tracker_obj_list = CampaignSmsTracker.objects.filter(campaign=campaignid)
        # We need to log this
        print('Campaign with id ', campaignid, 'Not found')
        cache.set(campaign_cache_key, tracker_obj_list, timeout=300) # cache for 5 minutes
    else:
        tracker_obj_list = cache.get(campaign_cache_key)   
    # Finally process the tracker objects
    if  tracker_obj_list:
        # Some campaign found
        # It may be single or bulk
        for obj in tracker_obj_list:
            # Need not to check if its active or not, as we may get dlr after long time
            if obj.is_active and data['STATUS'].lower() =='answered':
                number = data['MSISDN']
                min_sec = data['Call Duration']
                dtmf = data['DTMF_REP'] or 0
                res = obj.check_qualify(min_sec=min_sec, dtmf=dtmf)
                if res:
                    obj.send_sms(destination=number)
                    # Need to check if object is single or bulk
                if res and obj.campaign_type == 'single':
                    # update object status to inactive
                    obj.is_active = False
                    obj.save()
 
    try:
        obj = CampaignSmsTracker.objects.get(campaign=campaignid)
    except CampaignSmsTracker.DoesNotExist:
        # create empty entry
        obj = CampaignSmsTracker.objects.create(
            campaign_id=campaignid,
            is_active=False,
            campaign_type='single',
        )
    return obj


@shared_task
def process_dlr(data):
    """ This function will do the following
        1. Logs the DLR to file
        2. Check if SMS sent is registered. Send the sms if found

        Need to refractor this function to minimize DB hits
    """
    # This process should not take too much time
    # and should not depend upon multiple database
    dlr_dir = getattr(settings, 'DLR_DIR')
    print('We got dlr ', data)
    if not dlr_dir:
        dlr_dir.mkdir(parents=True)
    
    filename = dlr_dir / '{}.log'.format(datetime.datetime.now().strftime('%y%m%d'))
    if isinstance(data, list):
        data = data[0]

    dump_data(filename, data)
    check_sms_campaign_tracker(data)
    return "Done"

        


