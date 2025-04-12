from django.urls import path
from smartping import views
app_name = 'smartping'

urlpatterns = [
    path('', views.dashboard, name="dashboard_home"),
    path('audios/', views.VoxuploadListView.as_view(), name="audio_list"),
    path('audio/create', views.VoxuploadFormView.as_view(), name="audio_create"),
    path('audio/<str:voiceid>/refresh', views.refresh_voice_status, name="audio_refresh"),
    path('audio/<str:pk>/delete', views.VoxuploadDeleteView.as_view(), name="audio_delete"),

    # Single voice Creation
    path('singlevoices/', views.SingleVoiceCreationListView.as_view(), name="singlevoice_list" ),
    path('singlevoice/create', views.SingleVoiceCreationCreateView.as_view(), name="singlevoice_create" ),


    # Bulk voice creation
    path('bulkvoices/', views.CampaignCreationListView.as_view(), name="campaign_list"),
    path('bulkvoice/create', views.CampaignCreationCreateView.as_view(), name="campaign_create"),

    # Get summary
    path('campaignstatus/', views.get_campaign_status, name="campaign_status"),
    path('generate_report/', views.download_campaign_report, name='campaign_report'),
    path('runcampaign/', views.run_campaign, name="campaign_send"),
]