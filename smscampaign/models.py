from django.db import models
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

import uuid

class KannelSMSC(models.Model):
    """ Just tried to make the smsc editable from database 
    Reason: As we will be creating number of User for Voice OBD,
    So, there will be requirement that multiple SMSC may be used.
    """
    name = models.CharField('Provider Name', max_length=100)
    host = models.URLField()
    port = models.IntegerField(default=14013)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    smsc = models.CharField(max_length=50)
    is_https = models.BooleanField(default=False)


    def __str__(self) -> str:
        return self.name
    
    # create the sms_sent_url
    def smsc_sent_url(self):
        if self.host.startswith('http'):
            host = self.host.split('//')[1]
        if self.is_https:
            return f'https://{host}:{self.port}/cgi-bin/sendsms'
        else:
            return f'http://{host}:{self.port}/cgi-bin/sendsms'
    

TEST_STATUS_CHOICES = (
    ('na', 'Not Available'),
    ('sent', 'Sent'),
    ('failed', 'Failed'),
    ('delvrd', 'Delivered'),
    ('reject', 'Rejected'),
)
# Create your models here.
class SmsTemplate(models.Model):
    """ SmsTemplate models allow user to fill the approved message details:
        SENDERID, PE_ID, TEMPLATE_MSG, TEMPLATE_ID

       This class have verify_function as property to auto send a test message
       and check the status of number, if its pass, then it will mark as verified
       if not, it will send the details of not verified.

       if template is already verified and we found sms is not getting delivered,
       we need to check out the reports too.

       and mark it as not verified also.

       Need to track the verification
      
    """
    # Who created this template
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='sms_templates')
    name = models.CharField(max_length=50)
    
    # Template related settings
    header = models.CharField(verbose_name='SMS HEADER', max_length=6)
    pe_id = models.CharField(verbose_name='Personal Entity ID', max_length=20)
    message = models.TextField(verbose_name='Message Content', help_text="Approved Message Content")
    template_id = models.CharField(verbose_name='Template ID', max_length=20)

    # Now verify the message field
    is_verified = models.BooleanField(default=False)
    test_status = models.CharField(max_length=50, choices=TEST_STATUS_CHOICES, default='na')

    created_at = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)


    def __str__(self) -> str:
        return 'SENDER:(%s) template:(%s)' % (self.header, self.message)
    

    def get_test_data(self, number) -> dict:
        """ This functions will send a test message to the number
        Basically run a task in the background.
        and automatically update the states
        """
        data = {
            'username': self.user.username,
            'smstemplate_id': self.id,
            'header': self.header,
            'pe_id': self.pe_id,
            'template_id': self.template_id,
            'message': self.message,
            'to': number
        }

        return data
    

SMS_REPORT_TYPE_CHOICE = (
    ('approve', 'Approval'),
    ('normal', 'Normal'),
)
class SmsReport(models.Model):
    """This tables will keep records of SMS sent and their status
    Below information is stored
    User: who sent this message
    message related field
    header, pe_id, template_id, message

    Creation related details and status
    Will it send sms also? No, this will just keep records. to make it simple

    """
    track_code = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, related_name='sms_test_reports')
    
    header = models.CharField(verbose_name='SMS HEADER', max_length=6)
    pe_id = models.CharField(verbose_name='Personal Entity ID', max_length=20)
    message = models.TextField(verbose_name='Message Content', help_text="Approved Message Content")
    template_id = models.CharField(verbose_name='Template ID', max_length=20)
    
    # status
    is_sent = models.BooleanField('Sent?', default=False)
    is_delivered = models.BooleanField('Delivered?', default=False)
    msg_status = models.CharField('Status', max_length=50)

    created_at = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    # Need to set which route use to send sms
    sms_route = models.ForeignKey(KannelSMSC, on_delete=models.DO_NOTHING, default=1)

    # type of sms
    sms_type = models.CharField(max_length=10, choices=SMS_REPORT_TYPE_CHOICE, default='normal')

    def __str__(self):
        return f'{self.user.username} {self.header} {self.msg_status}'
    
    def get_dlr_url(self):
        # this need to prepare smartly
        if not cache.get('dlr_host'):
            from django.conf import settings
            host_list = getattr(settings, 'ALLOWED_HOSTS')
            dlr_host = host_list[0]
            cache.set('dlr_host', dlr_host, timeout=3600)
        else:
            dlr_host = cache.get('dlr_host')

        if dlr_host in ['localhost', '127.0.0.1']:
            host = f'http://{dlr_host}:8000'
        else:
            host = f'http://{dlr_host}'
        return f'{host}{reverse("smscampaign:dlr-url")}?track_code={self.track_code}&dlr_status=%d&dlr_msg=%A'
        
    


