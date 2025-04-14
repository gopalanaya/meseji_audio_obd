from django.contrib import admin
from smscampaign.models import KannelSMSC, SmsTemplate, SmsReport

# Register your models here.
class KannelSMSCAdmin(admin.ModelAdmin):
    list_display = ('name', 'smsc_sent_url', 'smsc', 'username')

admin.site.register(KannelSMSC,KannelSMSCAdmin)


class SmsTemplateAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_status', 'name', 'header', 'message', 'is_verified')


admin.site.register(SmsTemplate, SmsTemplateAdmin)


class SmsReportAdmin(admin.ModelAdmin):
    list_display = ('track_code', 'user', 'header', 'message', 'is_sent', 'is_delivered', 'msg_status', 'updated_at')


admin.site.register(SmsReport, SmsReportAdmin)