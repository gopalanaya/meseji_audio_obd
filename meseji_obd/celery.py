import os
from celery import Celery

# set the django default settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meseji_obd.settings')

app = Celery('meseji_obd')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')