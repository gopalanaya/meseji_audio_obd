from django import forms
from smartping.models import VoxUpload, CampaignCreation, SingleVoiceCreation
from django.forms import ValidationError
from smartping.ffmpeg_utils import convert_audio_file, construct_output_filename

class VoxUploadForm(forms.ModelForm):
    class Meta:
        model = VoxUpload
        fields = ('plantype', 'filename', 'uploadedfile',)
    
    
    def clean_uploadedfile(self):
        uploadedfile = self.cleaned_data.get('uploadedfile')
        content_type = uploadedfile.content_type

        if content_type.split('/')[0] != 'audio':
            raise ValidationError("Given file is not audio media type", 'wrong_media')

        return uploadedfile
    

    def clean_filename(self):
        filename = self.cleaned_data.get('filename')
        if self.Meta.model.objects.filter(filename=filename).count() > 0:
            raise ValidationError('Filename Exists. Please choose different Name', 'duplicate filename')
        
        return filename
    
        
class CampaignCreationForm(forms.ModelForm):
    """ This form will allow user to choose voice and CampaignData to start basic OBD
    Campaign.
    Extra Fields:
        CampaignType:
        SINGLE_VOICE : (This will be just a call),
        INTERACTIVE : Here if audio played with minimum seconds, it will
                      send sms,
                      provided: sms_template (approved),
                      minimum_duration: num of seconds

        Response OBD: Here DTMF Response will be collected
    """
    class Meta:
        model = CampaignCreation
        fields = ('voiceId', 'campaignData','obd_type', 'sms_required', 'duration', 'sms_template')
        
        labels = {
            'campaignData': "Campaign Base",
        }
        help_texts= {
            'sms_required': 'It will be activated when Sms Template is approved',
            'voiceId': 'All approved voice file will be shown here',
            'obd_type': "SINGLE_VOICE option will just play audio to User while DTMF will capture response too..",
        }
        

    
    def clean(self):
        super(CampaignCreationForm, self).clean()

        # check if sms_required is checked
        if self.cleaned_data.get('sms_required'):
            duration = self.cleaned_data.get('duration')
            sms_template = self.cleaned_data.get('sms_template')
            if int(duration) < 5:
                raise ValidationError('Duration cannot be less than 5 sec')
            if not sms_template:
                raise ValidationError('Not a valid Template Choice')
        
        return self.cleaned_data
    
    
    def clean_obd_type(self):
        obd_type = self.cleaned_data.get('obd_type')
        if obd_type.lower() == 'callpatch':
            raise ValidationError("Sorry, Call Patch feature is not available currently. Please choose either SINGLE_VOICE or DTMF")
        
        return obd_type
    

class SingleVoiceCreationForm(forms.ModelForm):
    class Meta:
        model = SingleVoiceCreation
        fields = ('voiceId','dn','obd_type', 'sms_required', 'duration', 'sms_template')

        help_texts= {
            'sms_required': 'It will be activated when Sms Template is approved',
            'voiceId': 'All approved voice file will be shown here',
            'obd_type': "SINGLE_VOICE option will just play audio to User while DTMF will capture response too..",
        }
        

    
    def clean(self):
        super(SingleVoiceCreationForm, self).clean()

        # check if sms_required is checked
        if self.cleaned_data.get('sms_required'):
            duration = self.cleaned_data.get('duration')
            sms_template = self.cleaned_data.get('sms_template')
            if int(duration) < 5:
                raise ValidationError('Duration cannot be less than 5 sec')
            if not sms_template:
                raise ValidationError('Not a valid Template Choice')
        
        return self.cleaned_data
    

    def clean_dn(self):
        dn = self.cleaned_data.get('dn')
        if not dn.isnumeric() or len(dn) != 10:
            raise ValidationError('Invalid 10 digit mobile number!')
        
        return dn
    
    def clean_obd_type(self):
        obd_type = self.cleaned_data.get('obd_type')
        if obd_type.lower() == 'callpatch':
            raise ValidationError("Sorry, Call Patch feature is not available currently. Please choose SINGLE_VOICE or DTMF")
        
        return obd_type