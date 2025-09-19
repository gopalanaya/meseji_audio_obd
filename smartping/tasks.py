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


@shared_task
def process_dlr(data):
    """ This function will do the following
        1. Logs the DLR to file
        2. Check if SMS sent is registered. Send the sms if found
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

    # check if sms is registered for a campaign
    campaignid = data['CampaignID']
    campaign_cache_key = 'cmgn_tracker_{}'.format(campaignid)
    if not cache.get(campaign_cache_key):
        tracker_obj = CampaignSmsTracker.objects.filter(campaign=campaignid)
        if not tracker_obj:
            print('Campaign with id ', campaignid, 'Not found')
            return "OK"
        else:
            # Some campaign found
            # It may be single or bulk
            for obj in tracker_obj:
                number = data['MSISDN']
                min_sec = data['DURATION']
                dtmf = data['DTMF'] or 0
                if data['STATUS'].lower() == 'answered':
                    res = obj.check_qualify(min_sec=min_sec, dtmf=dtmf)
                    if res:
                        obj.send_sms(destination=number)


    return "Done"

        


