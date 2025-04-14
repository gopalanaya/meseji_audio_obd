from django.core.management.base import BaseCommand 
from django.db.models import Count 
from smartping.utils import run_audio_obd
from datetime import timedelta, datetime 
from smartping.models import CampaignCreation
from django.core.files.base import ContentFile
  
  
def now(): 
    return datetime.now() 
  
  
class Command(BaseCommand): 
    help = 'Run given campaign with status and audio file'

    def add_arguments(self, parser): 
        parser.add_argument('-i', '--campgid', type=int, help='Campaign id to run') 
  
  
    def handle(self, *args, **kwargs): 
        campgid = kwargs['campgid']
        camp_instance = CampaignCreation.objects.get(id=campgid )
        run_audio_obd(camp_instance)
          
        print(f"Campaign: {campgid} is processed") 
