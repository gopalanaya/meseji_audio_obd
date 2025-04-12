from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string

# Create your models here.

def get_unique_id(l=20):
    return get_random_string(length=l)


class User(AbstractUser):
    token = models.CharField(max_length=20, default=get_unique_id)
    balance = models.IntegerField(default=100)
 
