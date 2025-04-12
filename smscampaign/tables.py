from smscampaign.models import SmsTemplate, SmsReport
import django_tables2 as tables


class SmsTemplateTable(tables.Table):
    action = tables.TemplateColumn("""<a class="btn btn-danger" href="{% url 'smscampaign:smstemplate_delete' record.pk %}">Delete</a>
                                   <a class="btn btn-primary" href="{% url 'smscampaign:smstemplate_approve' record.pk %}"> Approve</a>
                                    """)
    class Meta:
        model = SmsTemplate
        fields = ('name', 'header','updated_at', 'pe_id', 'template_id', 'message', 'is_verified', 'test_status')


class SmsReportTable(tables.Table):
    class Meta:
        model = SmsReport
        fields = ('track_code', 'sms_route', 'user', 'header', 'pe_id', 'template_id', 'message', 'is_sent', 'is_delivered', 'msg_status')