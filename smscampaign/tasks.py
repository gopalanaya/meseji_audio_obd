# tasks file to send_test_message and run campaign
from smscampaign.models import SmsReport, KannelSMSC, SmsTemplate
from django.contrib.auth import get_user_model
from django.core.cache import cache
import requests, datetime
import logging, hashlib
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()

def send_test_message(data):
    """ A function to send a test message and track the status. 
    Also it will update a message status, it should return message id or something

    Sample sms request:
    url = "http://localhost:14013/cgi-bin/sendsms"

    params = {
        'smsc': 'vector',
        'username':'anaya',
        'password':'anaya',
        'to':'919871034010',
        'from':'VMOFFR',
        'text':"Dear Customer, 24*7 support and cashless claims service. Best Insurance Quotes now. Click here: https://vm.ltd/VMOFFR/S34Rt4 T&C - VectorOffer",
        'charset':'iso-8859-1',
        'coding':0,
        'dlr-mask':11,
        'meta-data':'?smpp?tm_id=tm_id_given&pe_id=1701159231459927489&template_id=1707172796396663040'
        }

    Response: Status, message
    
    """
    # First need to send the sms and then makes entry in the database.
    # check if any Kannel SMSC present or not
    if KannelSMSC.objects.count() == 0:
        return False, 'No SMSC is attached'
    
    # Future function to check if we have any smsc attached to username
    # This is important, as we need to define that the given message should
    # use defined SMSC
    if not cache.get('default_provider'):
        provider = KannelSMSC.objects.first()
        cache.set('default_provider', provider, timeout=3600)
    
    provider = cache.get('default_provider')

    params = {
        'smsc': provider.smsc,
        'username': provider.username,
        'password': provider.password,
        'to': data['to'],
        'from': data['header'],
        'text': data['message'],
        'dlr-mask': 3
    }
    if len(data['message']) == len(data['message'].encode()):
        # its ASCII message
        params['charset'] = 'iso-8859-1'
        params['coding'] = 0
    else:
        params['charset'] = 'utf-8'
        params['coding'] = 2
    
    TM_ID = getattr(settings, 'TM_ID')

    # need to create a hash
    tm_id = hashlib.sha256('{},{}'.format(data['pe_id'],TM_ID).encode('utf-8')).hexdigest()
    print("Tm id is", tm_id)


    # set meta data
    params['meta-data'] = f"?smpp?tm_id={tm_id}&pe_id={data['pe_id']}&template_id={data['template_id']}"



    # get the user with username
    if not cache.get(data['username']):
        sms_user = User.objects.get(username=data['username'])
        cache.set(data['username'], sms_user, timeout=3600)
    else:
        sms_user = cache.get(data['username'])

    # prepare dlr_url, get the trackcode from SMS report
    sms_report_obj = SmsReport.objects.create(
        header = data['header'],
        pe_id = data['pe_id'],
        message = data['message'],
        template_id = data['template_id'],
        user=sms_user
    )
    # dlr url should be prepared automatically
    params['dlr-url'] = sms_report_obj.get_dlr_url()

    # Now we going to send the message
    sms_sent_url = provider.smsc_sent_url()
    logger.warning(f'Sending message with params: {params}')
    res = requests.get(sms_sent_url, params=params)
    if res.status_code == 202:
        sms_report_obj.is_sent = True
        sms_report_obj.msg_status = 'Accepted for delivery'
        sms_report_obj.sms_type = "approve"
        sms_report_obj.save()
        return 'OK', res.content.decode('utf-8')
    else:
        sms_report_obj.msg_status = "Error occurred: "+ res.content.decode('utf-8')
        logger.error('we received error while sending sms: {}'.format(res.content.decode('utf-8')))
        sms_report_obj.save()
        return 'Error', res.content.decode('utf-8')


    
def process_dlr(track_code="", dlr_status="", dlr_msg=""):
    """ Just save the dlr reports and logs """
    all_message = SmsReport.objects.filter(track_code=track_code)
    if len(all_message) > 0:
        # Message found
        sms_obj = all_message[0]
        sms_obj.is_delivered = True if dlr_status == '1' else False
        sms_obj.msg_status = " ".join(dlr_msg.split(' ')[-3:-1]) if dlr_msg else "NA"

        if sms_obj.sms_type == 'approve':
            # Need to approve the smsTemplate too
            sms_template_obj = SmsTemplate.objects.get(user=sms_obj.user, template_id = sms_obj.template_id)
            sms_template_obj.is_verified = True
            sms_template_obj.test_status = 'delvrd'
            sms_template_obj.save()

        sms_obj.save()
        logger.warning(f"Received DLR for {track_code}, {dlr_msg}, {dlr_status} on {datetime.datetime.now()}")

    else:
        # Need to logs this
        logger.warning(f"Message with track code: '{track_code}' Not found")