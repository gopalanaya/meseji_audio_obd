from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required
def confirm_logout(request):
    return render(request, template_name="account/confirm-logout.html")
    
