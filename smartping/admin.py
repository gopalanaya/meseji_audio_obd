from django.contrib import admin
from smartping.models import VoxUpload, SingleVoiceCreation, CampaignCreation
# Register your models here.

@admin.action(description="Upload to smartping")
def upload_to_smartping(modeladmin, request, queryset):
    for obj in queryset:
        if obj.voiceid:
            # we will not be regenerating voiceid
            continue
        obj.upload_to_vox()


@admin.action(description="Update the voice status")
def update_voice_status(modeladmin, request, queryset):
    """ This will bulk check and update the status. irrespective of current status"""
    for obj in queryset:
        obj.fetch_status()


class VoxUploadAdmin(admin.ModelAdmin):
    list_display = ["id","user", "voiceid", "plantype", "filename","media_play", "status"]
    ordering = ['-voiceid']
    actions = [upload_to_smartping, update_voice_status]
    readonly_fields = ['media_play']



admin.site.register(VoxUpload, VoxUploadAdmin)


class SingleVoiceCreationAdmin(admin.ModelAdmin):
    list_display = ['voiceId', 'dn', 'campg_id', 'status', 'user', 'created_at', 'err_code']

admin.site.register(SingleVoiceCreation, SingleVoiceCreationAdmin)


class CampaignCreationAdmin(admin.ModelAdmin):
    list_display = ['user', 'voiceId', 'created_at', 'status', 'status_fetched', 'is_sent', 'valid_count', 'invalid_count', 'campaignData', 'processedData']

admin.site.register(CampaignCreation, CampaignCreationAdmin)