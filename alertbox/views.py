from django.shortcuts import render
from alertbox.models import VoiceTemplate
from alertbox.tables import VoiceTemplateTable
from django_tables2 import SingleTableView
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

class VoiceTemplateListView(LoginRequiredMixin, SingleTableView):
    model = VoiceTemplate
    template_name = "alertbox/voicetemplate_list.html"
    table_class = VoiceTemplateTable


    def get_queryset(self):
        if self.request.user.is_staff:
            return VoiceTemplate.objects.all()
        
        return VoiceTemplate.objects.filter(user=self.request.user)