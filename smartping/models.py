from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
import requests, json, datetime
from django.contrib.auth import get_user_model
from django.core.files import File
from pathlib import Path
from smartping.ffmpeg_utils import construct_output_filename, convert_audio_file, read_audio_meta
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from typing import Union


# other app models
from smscampaign.models import SmsTemplate

def handle_uploaded_file(sourcefile):
    current_date = datetime.datetime.now().strftime('%Y%m%d')
    target_directory = settings.MEDIA_ROOT / '{}'.format(current_date)
    if not target_directory.exists():
        target_directory.mkdir()
    
    target_file = target_directory / '{}.txt'.format(datetime.datetime.now().strftime('%H%M%S'))
    with open(target_file, 'wb+') as destination:
        for chunk in sourcefile.chunks():
            destination.write(chunk)


PLANTYPE_CHOICES = (
    (15, '15'),
    (30, '30'),
    (60, '60'),
    (120, '120'),
)

class SmartpingModel(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, default="1")
    status = models.CharField(max_length=15, default='processing')
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True, auto_now=False)

    class Meta:
        abstract = True

    
    def get_campaign_summary(self, campaignid=None) -> str:
        """ A helper function to check the status of campaign.  Basically when to fetch the result
        of campaign. 
         
        A campaign is open: it means still running
        A campaign is closed: it means all number is sent for call and we can fetch response.

        For single number campaign, we have to match the id.
        For bulk campaign, we will have to fetch, the number too.
        """
        target_url = getattr(settings, 'smartping_url'.upper()) + '/OBD_REST_API/api/OBD_Rest/Campaign_Summary'

        params = {
            'username': getattr(settings, 'smartping_username'.upper()),
            'password': getattr(settings, 'smartping_password'.upper()),
            'campaignid': campaignid
        }
        if not campaignid:
            return 'NA'
        else:
            res = requests.get(target_url, params=params)
            data = res.json()
            return data['Status']
        

    def get_campaign_detail(self, campaignid=None) -> Union[list[dict], str]:
        """ This will be the main function that will be getting reports of campaign """
        if not campaignid:
            return 'NA'
        
        status = self.get_campaign_summary(campaignid=campaignid)
        if status == 'CLOSE':
            # We need to fetch the report
            target_url = getattr(settings, 'smartping_url'.upper()) + '/OBD_REST_API/api/OBD_Rest/Campaign_Call_Details'

            params = {
                'username': getattr(settings, 'smartping_username'.upper()),
                'password': getattr(settings, 'smartping_password'.upper()),
                'campaignid': campaignid
                }
            
            res = requests.get(target_url, params=params)
            return res.json()
        
        if not status:
            target_url = getattr(settings, 'smartping_url'.upper()) + '/OBD_REST_API/api/OBD_Rest/Campaign_Call_Details'

            params = {
                'username': getattr(settings, 'smartping_username'.upper()),
                'password': getattr(settings, 'smartping_password'.upper()),
                'campaignid': campaignid
                }
            
            res = requests.get(target_url, params=params)
            return res.json()  
        
        else:
            return status


class VoxUpload(SmartpingModel):
    plantype = models.IntegerField('Plan Type', default=15, choices=PLANTYPE_CHOICES)
    filename = models.CharField('Filename', max_length=40)
    uploadedfile = models.FileField('Uploaded file', upload_to='voxupload')
    processedfile = models.FileField('Processed file', upload_to="voxupload", null=True, blank=True)
    status = models.CharField(max_length=100, blank=True)
    voiceid = models.CharField(max_length=15, blank=True, unique=True)
    

    def __str__(self):
        return "(%s) %s" %(self.voiceid, self.filename)
    
    def __repr__(self):
        return '%s:%s' % (self.voiceid, self.status)
    

    def verify_plantype(self):
        """ This function will modify plantype based on media duration"""
        result = read_audio_meta(self.processedfile.path)
        for p in PLANTYPE_CHOICES:
            if float(result['duration']) < p[0]:
                duration = p[0]
                break
        
        if duration != self.plantype:
            self.plantype = duration
            self.save()
        

    def upload_to_vox(self):
        """ This function is used to upload audio to server and get the voice id:
        Requirement: processedfile should not be None
        Sample code:
        import requests

        url = "http://103.132.146.183/VoxUpload/api/Values/upload"

        payload = {'username': '',
                  'password': '',
                  'plantype': '30',
                  'filename': 'mukhya_mantri_majhi_ladki_bahin'}
                  files=[
                      ('uploadedfile',('MUKHYA MANTRI MAJHI LADKI BAHIN_1.wav',open('/C:/Users/Gopal Anaya/Downloads/MUKHYA MANTRI MAJHI LADKI BAHIN_1.wav','rb'),'audio/wav'))
                     ]
                  headers = {}

                  response = requests.request("POST", url, headers=headers, data=payload, files=files)

                   print(response.text)

                   Response: 200
                   Submitted Successfully to Provisioning with Voice ID: 35751
        """
        # first verify the plantype and duration
        self.verify_plantype()
        target_url = getattr(settings, 'SMARTPING_URL') +'/VoxUpload/api/Values/upload'
        # check if its already uploaded
        if self.voiceid:
            return "Already Uploaded"
        payload = {
            'username': getattr(settings, 'SMARTPING_USERNAME'),
            'password': getattr(settings, 'SMARTPING_PASSWORD'),
            'filename': self.filename,
            'plantype': self.plantype,
        }

        files = [
            ('uploadedfile', (self.processedfile.name, open(self.processedfile.path, 'rb'), 'audio/wav'))
        ]

        headers = {}
        response = requests.request("POST", target_url, headers=headers, data=payload, files=files)

        if response.status_code == 200:
            # Note down the voiceid and save it.
            print(response.text)
            print(response.content)
            # Fix when voice file is rejected
            if 'rejected' in response.text.lower():
                self.voiceid = 0;
                self.status = "REJECTED"
            else:
                if len(response.text.split(':')) > 1:
                    self.voiceid = response.text.strip().split(':')[1].strip()
                    self.status = 'provisioning'
                else:
                    self.status = "REJECTED ALREADY EXIST"
        
        else:
            self.status = 'error occurred.'
            print('Error occured,', response.content)

        self.save()

    
    def fetch_status(self):
        """ This function will query the server and get the status of voice file with given id"""
        # check if voiceid is returned
        if not self.voiceid:
            return "Pending for Upload"
        
        # if voiceid is there, we need to check if its approved or not.
        target_url = getattr(settings, 'SMARTPING_URL') + '/VoxUpload/api/Values/CheckStatus'
        payload = {
            'username': getattr(settings, 'SMARTPING_USERNAME'),
            'password': getattr(settings, 'SMARTPING_PASSWORD'),
            'voiceid': self.voiceid,
        }
        headers = {}
        response = requests.request('POST', target_url, data=payload, headers=headers)

        if response.status_code == 200:
            # get the status and save to table
            status = response.text
            if "approved" in status.lower():
                self.status = "APPROVED"
            elif "open" in status.lower():
                self.status = "OPEN"
            elif 'rejected' in status.lower():
                self.status = 'REJECTED'

            self.save()
            return status
        else:
            # some error occured
            print(response.content)
            return "Unable to get status. Try again"
        

    def media_play(self):
        """ This will return the html to play an audio"""
        if self.processedfile.url:
            fileurl = self.processedfile.url
        else:
            fileurl = self.uploadedfile.url
        return format_html(mark_safe(f"""<span><audio controls >
                           <source src="{fileurl}" type="audio/wav">
                           </audio></span>             
                          """))



    

    #def save(self, *args, **kwargs):
        
    #    if not self.pk:
    #        uploadedfile = self.uploadedfile
        
    #        # convert the audio
    #        convert_audio_file(uploadedfile.path)
    #        processedfile_path = Path(construct_output_filename(uploadedfile.path))
    #        with processedfile_path.open(mode='rb') as f:
    #            self.processedfile = File(f, name=processedfile_path.path)
        
    #    super(VoxUpload, self).save(*args, **kwargs)

@receiver(post_save, sender=VoxUpload)
def transcode_and_upload(sender, instance, created, **kwargs):
    if created:
        uploadedfile = instance.uploadedfile.path
        convert_audio_file(uploadedfile) # its converted now
        processedfile_path = Path(construct_output_filename(uploadedfile))

        with processedfile_path.open(mode='rb') as f:
            instance.processedfile = File(f, name=processedfile_path.name)
            instance.save()
        
        # Now cleanup the temproary file
        processedfile_path.unlink()
    

@receiver(pre_delete, sender=VoxUpload)
def remove_uploaded_media(sender, instance, **kwargs):
    if instance.processedfile:
        instance.processedfile.delete()
    if instance.uploadedfile:
        instance.uploadedfile.delete()


OBD_TYPE_CHOICES = (
    ('SINGLE_VOICE', 'SINGLE VOICE'),
    ('DTMF', 'DTMF'),
    ('CallPatch', 'Call Patch'),

)


# Create your models here.

# A Base model for common information
class CampaignCreation(SmartpingModel):
    """ CampaignCreation Model excluding username and password save"""
    transitionId = models.CharField("Transition id", max_length=20, serialize=True)
    voiceId = models.ForeignKey(VoxUpload, on_delete=models.CASCADE, to_field='voiceid')
    campaignData = models.FileField("Campaign Numbers", upload_to='uploads/campaign_data')
    obd_type = models.CharField("OBD Type", max_length=12, choices=OBD_TYPE_CHOICES, default='SINGLE_VOICE')
    dtmf = models.CharField("DTMF?", max_length=10, blank=True)
    call_patch_no = models.CharField("Call Patch No", max_length=20, blank=True)
    err_code = models.CharField("Error Code", max_length=10, blank=True)
    err_desc = models.CharField("Error Description", max_length=100, blank=True)
    campg_id = models.TextField("Campaign IDs", blank=True)
    is_sent = models.BooleanField('is sent?', default=False)
    status_fetched = models.BooleanField('is_feteched?', default=False)
    sms_required = models.BooleanField('sent sms on answered?', default=False)
    duration = models.IntegerField('Minimum Duration', default=0, help_text="Minimum duration to qualify for SMS")
    sms_template = models.ForeignKey(SmsTemplate, on_delete=models.DO_NOTHING, blank=True, null=True, help_text="Verified sms only")

    # Campaign related count, valid_count, invalid_count, valid_base
    valid_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    processedData = models.FileField('Valid Base', upload_to='uploads/valid_campaign_data', blank=True)

    # Report data
    reportData = models.FileField('Report Data', upload_to='reports', blank=True)
    sms_sent = models.BooleanField('Sms Sent?', default=False)

    def __str__(self):
        return '%s %s %s' % (self.id, self.voiceId, self.obd_type)
    

    def parse_base_and_count(self):
        """ This function will open the uploaded data and update the count"""
        import re, os
        number_pattern =  r'^([0|\+[0-9]{1,5})?([6-9]\d{9})$'
        valid_count = 0
        invalid_count = 0
        sourcefile = self.campaignData.path
        targetfile = Path(sourcefile + '.temp')
        new_file = 'processed_' + os.path.basename(sourcefile)
        number_list = []
        

        with targetfile.open('w', encoding='utf-8') as f:
            for line in open(self.campaignData.path, 'r', encoding='utf-8'):
                line = line.strip().replace('^M', '').replace(' ', '')
                if line and len(line) in [10, 12]:
                    # get number
                    
                    if re.search(number_pattern, line):
                        number = re.search(number_pattern, line ).groups()[1]
                        if  number not in number_list:
                            number_list.append(number)
                            valid_count += 1
                            f.write('{}\n'.format(number))
                        else:
                            invalid_count += 1
                    else:
                        invalid_count += 1

        
        with targetfile.open('r', encoding='utf-8') as f:
            self.processedData = File(f, name=new_file)
            self.valid_count = valid_count
            self.invalid_count = invalid_count
            self.save()

        # finally delete the file
        targetfile.unlink()

    

    def get_post_url(self):
        """ This function will return POST url based on obd_type selection"""
        target_url = getattr(settings, 'SMARTPING_URL') 
        if self.obd_type.lower() == 'single_voice':
            target_url += '/OBD_REST_API/api/OBD_Rest/Campaign_Creation'

        elif self.obd_type.lower() == 'dtmf':
            target_url += '/OBD_REST_API/api/OBD_Rest/Campaign_CreationDTMF'
        else:
            # assume its callpatch
            target_url += '/OBD_REST_API/api/OBD_Rest/Campaign_CreationCallPatch'
        
        return target_url
    

    def get_data_dict(self):
        """" A function to return all dictionary necessary for creating campaign"""
        data = {
        'UserName': getattr(settings, 'smartping_username'.upper()),
        'Password': getattr(settings, 'smartping_password'.upper()),
        'TransitionId': self.transitionId,
        'VoiceId': self.voiceId.voiceid,
        'CampaignData': self.campaignData.path,
        'OBD_TYPE': self.obd_type,
        'DTMF': self.dtmf,
        'CALL_PATCH_NO': self.call_patch_no,
        }

        return data

    def dump_data(self):
        return {
            'transitionId': self.transitionId,
            'voiceId': self.voiceId,
            'campaignData': self.campaignData,
            'obd_type': self.obd_type,
            'err_code'.upper(): self.err_code,
            'err_desc'.upper(): self.err_desc,
            'campg_id'.upper(): self.campg_id,
            'sms_required': self.sms_required
        }
    


@receiver(post_save, sender=CampaignCreation, dispatch_uid="create_campaign")
def validate_campaign_and_save(sender, instance, created, **kwargs):
    """ This funtion will call parse_base_and_count property and save the file
    """
    if created:
        instance.parse_base_and_count()


# Create your models here.
class SingleVoiceCreation(SmartpingModel):
    """ CampaignCreation Model for single name excluding username and password save"""
    voiceId = models.ForeignKey(VoxUpload, on_delete=models.CASCADE, to_field='voiceid')
    dn = models.CharField("Destination Number",max_length=10)
    obd_type = models.CharField("OBD Type", max_length=12, choices=OBD_TYPE_CHOICES, default='SINGLE_VOICE')
    err_code = models.CharField("Error Code", max_length=10, blank=True)
    err_desc = models.CharField("Error Description", max_length=100, blank=True)
    campg_id = models.CharField("Campaign ID", max_length=20, blank=True)
    trans_id = models.CharField('Transaction ID', max_length=30, blank=True)
    status_fetched = models.BooleanField('is_feteched?', default=False)
    sms_required = models.BooleanField('sent sms on answered?', default=False)
    duration = models.IntegerField('Minimum Duration', default=0, help_text="Minimum duration to qualify for SMS")
    sms_template = models.ForeignKey(SmsTemplate, on_delete=models.DO_NOTHING, blank=True, null=True, help_text="Verified sms only")
    dtmf = models.CharField("DTMF?", max_length=2, default="NA")

    def __str__(self):
        return self.campg_id 
    
    def get_dict_data(self):
        data = {
        'UserName': getattr(settings, 'smartping_username'.upper()),
        'Password': getattr(settings, 'smartping_password'.upper()),
        'VoiceId': self.voiceId.voiceid,
        'DN': self.dn,
        'OBD_TYPE': self.obd_type,
        }

        return data
    
    def get_post_url(self):
        """ This will be the dynamic urls based on obd_type"""
        return  getattr(settings, 'smartping_url'.upper()) + '/OBD_REST_API/api/OBD_Rest/SINGLE_CALL'


    

@receiver(post_save, sender=SingleVoiceCreation, dispatch_uid="single_call")
def create_campaign(sender, instance, created, **kwargs):
    """ This will create a campaign and send it to remote party with status"""
    target_url = instance.get_post_url()
    data = instance.get_dict_data()
    # send the request and save the response
    
    if created:
        print(f'Initiating Type: Single Call, number {instance.dn}, type: {instance.obd_type}')
        # it already have, so we have to ignore
        res = requests.get(target_url, params=data)
        if res.status_code == 200:
            # save the response
            print(res.content)
            res_data = json.loads(res.content)
            err_code = res_data.get('err_code'.upper())
            if err_code == '0':
                instance.err_code = res_data.get('err_code'.upper())
                instance.err_desc = res_data.get('err_desc'.upper())
                instance.campg_id = res_data.get('campg_id'.upper())
                instance.trans_id = res_data.get('trans_id'.upper())
            else:
                instance.err_code = err_code
                instance.err_desc = res_data.get('err_desc'.upper())

            instance.save()
        else:
            print(res.content)



class CampaignStatus(models.Model):
    """ This field need to store in DB coming from API results
    Example response:
        {"CampaignID": "331599",
        "CampaignCode": null,
        "CampaignName": null,
        "CampaignScheduleTime": null,
        "Status": null,
        "ScheduleType": null,
        "EndDate": null,
        "MSISDN": "08278876726",
        "CLI": "1408360650",
        "FLAG": "P",
        "STATUS": "No Answer",
        "STARTTIME": "09-09-2024 13:06:04",
        "ENDTIME": "09-09-2024 13:06:35",
        "VALID_DN": null,
        "INVALID_DN": null,
        "ERROR": null,
        "DURATION": "31",
        "PROJECTED_AMOUNT": null,
        "CONSUMED_AMOUNT": null,
        "OPENING_BALANCE": null,
        "CLOSING_BALANCE": null,
        "Transation_ID": "10000001",
        "DTMF": "",
        "ID": "1725675650"
        }
    
    """
    campaignId = models.ForeignKey(CampaignCreation, on_delete=models.CASCADE)
    campaignCode = models.CharField('CampaignCode', max_length=30, blank=True)
    campaignName = models.CharField("Campaign Name", max_length=30, blank=True)
    campaignScheduleTime = models.CharField('Campaign Schedule Time', max_length=30)
    c_status = models.CharField(max_length=50, blank=True)
    scheduleType = models.CharField(max_length=30, blank=True)
    enddate = models.CharField("EndDate", max_length=30, blank=True)
    msisdn = models.CharField(max_length=10)
    cli = models.CharField(max_length=10)
    flag = models.CharField(max_length=2)
    status = models.CharField(max_length=30)
    starttime=models.DateTimeField('START TIME')
    endtime = models.DateTimeField('END TIME')
    valid_dn = models.CharField(max_length=20, blank=True)
    invalid_dn = models.CharField(max_length=20, blank=True)
    error = models.CharField(max_length=30, blank=True)
    duration = models.IntegerField()
    projected_amount = models.CharField(max_length=20, blank=True)
    consumed_amount = models.CharField(max_length=20, blank=True)
    opening_balance = models.CharField(max_length=20, blank=True)
    closing_balance = models.CharField(max_length=20, blank=True)
    transaction_id = models.CharField(max_length=20, blank=True)
    dtmf = models.CharField(max_length=20, blank=True)
    id = models.BigIntegerField(primary_key=True)
    sms_required = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)

    def __str__(self):
        return '%s %s %s' %(self.status, self.msisdn, self.id)

        




