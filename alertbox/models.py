from django.db import models
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from alertbox.ffmpeg_utils import construct_output_filename, convert_audio_file
from pathlib import Path
from django.core.files import File


STATUS_CHOICES = (
    ('approved', "APPROVED"),
    ('pending', "PENDING"),
    ('rejected', "REJECTED"),
)

class BaseModel(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, default='1')
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        abstract = True



# Create your models here.
class VoiceTemplate(BaseModel):
    voiceid = models.CharField(max_length=10, blank=True)
    name = models.CharField(max_length=50)
    filetype = models.CharField(max_length=20, default="promo")
    uploadedfile = models.FileField(upload_to="alertbox_media")
    processed_file = models.FileField(upload_to="alertbox_media", blank=True)
    status = models.CharField(max_length=10, default='pending', choices=STATUS_CHOICES)
    
    def __str__(self):
        return f'{self.name}: {self.status}'
    
    def media_play(self):
        return mark_safe(f"""<span><audio controls >
                           <source src="{self.processed_file.url}" type="audio/mp3">
                           </audio></span>""")


@receiver(post_save, sender=VoiceTemplate)
def transcode_file(sender, instance, created, **kwargs):
    if created:
        uploadedfile = instance.uploadedfile.path
        convert_audio_file(uploadedfile) # its converted now
        processedfile_path = Path(construct_output_filename(uploadedfile))

        with processedfile_path.open(mode='rb') as f:
            instance.processedfile = File(f, name=processedfile_path.name)
            instance.save()
        
        # Now cleanup the temproary file
        processedfile_path.unlink()


@receiver(pre_delete, sender=VoiceTemplate)
def remove_uploaded_media(sender, instance, **kwargs):
    if instance.processedfile:
        instance.processedfile.delete()
    if instance.uploadedfile:
        instance.uploadedfile.delete()



CAMPAIGN_STATUS_CHOICES = (
    ('pending', 'PENDING'),
    ('processing', 'PROCESSING'),
    ('running', 'RUNNING'),
    ('completed', 'COMPLETED'),
)

class VoiceCampaign(BaseModel):
    voiceid = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    filename = models.FileField(upload_to='voicecampaign')
    reports = models.FileField(upload_to="voicecampaign_report", blank=True)
    status = models.CharField(max_length=10, default='pending', choices=CAMPAIGN_STATUS_CHOICES)


    def __str__(self):
        return f'{self.created_at}{self.name} {self.status}'


    def run_campaign(self):
        """ This function will run campaign """ 
        # pass
        # split the base and run and update the status
        pass 