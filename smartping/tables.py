import django_tables2 as tables
from smartping.models import VoxUpload, CampaignCreation, SingleVoiceCreation
from django.utils.html import  format_html
from django.urls import reverse
from django_tables2.utils import A

class VoxUploadTable(tables.Table):
    delete = tables.LinkColumn("smartping:audio_delete", text="delete", args=[A("pk")], 
                               attrs={
        "a": {"class": "btn btn-danger"}})
    class Meta:
        model = VoxUpload
        template_name = "django_tables2/bootstrap5-responsive.html"
        fields = ('plantype', 'filename', 'status', 'voiceid', 'media_play', 'delete')
        

    def render_status(self, value, record):
        
        if value.lower() != 'approved' and record.voiceid:
            # need to generate update_url
            if value.lower() == 'rejected':
                return format_html(f"<b class='text-success'>{value}</b>")
            else:
                return format_html(f"""{value} <a class='btn btn-warning' href='{reverse("smartping:audio_refresh", kwargs={"voiceid": record.voiceid})}'>Refresh</a>""")
        else:
            return format_html(f"<b class='text-success'>{value}</b>")
        


class CampaignCreationTable(tables.Table):
    class Meta:
        model = CampaignCreation
        fields = ('id', 'created_at', 'voiceId', 'campaignData', 'obd_type', 'status_fetched','is_sent', 'valid_count', 'invalid_count', 'status', 'reportData')


    def render_status(self, value, record):
        if value.lower() in ['processing', 'act', 'open']:
            # we need to send button for refresh
            return format_html(f"""{value} <a class='btn btn-warning' href='{reverse("smartping:campaign_status")}?mode=bulk&campaignid={record.id}'>Refresh</a>""")
        elif value.lower() == 'close' and not record.status_fetched:
            # need to download report
            return format_html(f"""{value} <a class='btn btn-warning' href='{reverse("smartping:campaign_report")}?campaignid={record.id}'>Get Report</a>""")
        else:
            return value
        

    def render_is_sent(self, value, record):
        if value:
            return format_html("<span class='success'>✔</span>")
        else:
            return format_html(f"""<span class="danger">✘</span> <a class='btn btn-info' href='{reverse("smartping:campaign_send")}?campaignid={record.id}'>Start</a>""")

class SingleVoiceCreationTable(tables.Table):
    class Meta:
        model = SingleVoiceCreation
        fields = ('id', 'campg_id', 'voiceId', 'dn', 'obd_type', 'trans_id', 'status_fetched', 'err_code', 'err_desc', 'status', 'dtmf')

    
    def render_status(self, value, record):
        if value.lower() == 'processing':
            # we need to send button for refresh
            return format_html(f"""{value} <a class='btn btn-warning' href='{reverse("smartping:campaign_status")}?mode=single&campaignid={record.campg_id}'>Refresh</a>""")
        else:
            return value