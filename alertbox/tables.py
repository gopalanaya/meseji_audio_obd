import django_tables2 as tables
from alertbox.models import VoiceTemplate

class VoiceTemplateTable(tables.Table):
    
    class Meta:
        model = VoiceTemplate
        template_name = "django_tables2/bootstrap5-responsive.html"
        fields = ('id', 'voiceid', 'name', 'media_play', 'status')