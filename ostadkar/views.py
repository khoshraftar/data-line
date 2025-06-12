from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SampleWork
from .forms import SampleWorkForm

# Create your views here.

def home(request):
    return render(request, 'ostadkar/home.html')

def login(request):
    """Show login page"""
    return render(request, 'ostadkar/login.html')

def oauth_login(request):
    """Initiate OAuth login process"""
    oauth_settings = settings.OAUTH_APPS_SETTINGS['ostadkar']
    
    # Prepare OAuth parameters
    params = {
        'client_id': oauth_settings['oauth_client_id'],
        'redirect_uri': oauth_settings['oauth_redirect_uri'],
        'response_type': 'code',
        'scope': oauth_settings['oauth_scope'],
    }
    
    # Construct authorization URL
    auth_url = f"{settings.OAUTH_AUTHORIZATION_URL}?{urlencode(params)}"
    return redirect(auth_url)

def oauth_callback(request):
    """Handle OAuth callback"""
    if 'code' not in request.GET:
        return render(request, 'ostadkar/error.html', {'error': 'Authorization code not received'})
    
    oauth_settings = settings.OAUTH_APPS_SETTINGS['ostadkar']
    code = request.GET['code']
    
    # Exchange code for access token
    token_data = {
        'client_id': oauth_settings['oauth_client_id'],
        'client_secret': oauth_settings['oauth_client_secret'],
        'code': code,
        'redirect_uri': oauth_settings['oauth_redirect_uri'],
        'grant_type': 'authorization_code',
    }
    
    try:
        response = requests.post(settings.OAUTH_TOKEN_URL, data=token_data)
        response.raise_for_status()
        token_info = response.json()
        
        # Store token info in session
        request.session['access_token'] = token_info.get('access_token')
        request.session['refresh_token'] = token_info.get('refresh_token')
        
        return redirect('ostadkar:dashboard')
    except requests.RequestException as e:
        return render(request, 'ostadkar/error.html', {'error': f'Failed to get access token: {str(e)}'})

def dashboard(request):
    """Protected dashboard view"""
    if 'access_token' not in request.session:
        return redirect('ostadkar:login')
    
    return render(request, 'ostadkar/dashboard.html')

@login_required(login_url='ostadkar:login')
def sample_works(request):
    works = SampleWork.objects.filter(user=request.user)
    return render(request, 'ostadkar/sample_works.html', {'works': works})

@login_required(login_url='ostadkar:login')
def add_sample_work(request):
    if request.method == 'POST':
        form = SampleWorkForm(request.POST, request.FILES)
        if form.is_valid():
            work = form.save(commit=False)
            work.user = request.user
            work.save()
            messages.success(request, 'Sample work added successfully!')
            return redirect('ostadkar:sample_works')
    else:
        form = SampleWorkForm()
    return render(request, 'ostadkar/add_sample_work.html', {'form': form})

@login_required(login_url='ostadkar:login')
def edit_sample_work(request, work_id):
    work = get_object_or_404(SampleWork, id=work_id, user=request.user)
    if request.method == 'POST':
        form = SampleWorkForm(request.POST, request.FILES, instance=work)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sample work updated successfully!')
            return redirect('ostadkar:sample_works')
    else:
        form = SampleWorkForm(instance=work)
    return render(request, 'ostadkar/edit_sample_work.html', {'form': form, 'work': work})

@login_required(login_url='ostadkar:login')
def delete_sample_work(request, work_id):
    work = get_object_or_404(SampleWork, id=work_id, user=request.user)
    if request.method == 'POST':
        work.delete()
        messages.success(request, 'Sample work deleted successfully!')
        return redirect('ostadkar:sample_works')
    return render(request, 'ostadkar/delete_sample_work.html', {'work': work})
