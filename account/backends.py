from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache

class TokenBasedBackend(BaseBackend):
    def authenticate(self, request, token=None):
        # check the token and return user
        User = get_user_model()

        # get user from cache
        if cache.get(token):
            # user exist
            return cache.get(token)
        else:
            # authenticate and validate token
            try:
                if User.objects.get(token=token):
                    
                    u =  User.objects.get(token=token)
                    cache.set(token,u,600)
                    return cache.get(token)
            except User.DoesNotExist:
                return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
