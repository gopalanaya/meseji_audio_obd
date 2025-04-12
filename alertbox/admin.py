from django.contrib import admin
from alertbox.models import VoiceTemplate

# Register your models here.
class VoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ('voiceid', 'filetype', 'name', 'media_play','status')


admin.site.register(VoiceTemplate, VoiceTemplateAdmin)