from django.urls import path
from smscampaign import views

app_name = "smscampaign"

urlpatterns = [
    path('sms_dlr/', views.sms_dlr, name='dlr-url'),
    path('templates/', views.SmsTemplateTableView.as_view(), name="smstemplate_list"),
    path('template_create', views.SmsTemplateCreateView.as_view(), name="smstemplate_create"),
    path('template/<str:pk>/delete', views.SmsTemplateDeleteView.as_view(), name="smstemplate_delete"),
    path('template/<str:pk>/approve', views.SmsApproveView.as_view(), name="smstemplate_approve" ),
    path('reports/', views.SmsReportTableView.as_view(), name="smsreport_list" ),
    path('unicodetoascii', views.unicodetoascii, name='unicodetoascii'),
]
