from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

def home(request):
    """Khodroyar home page view"""
    return render(request, 'khodroyar/home.html')
