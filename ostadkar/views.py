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
    # If user is already authenticated, redirect to add sample work
    if 'user_id' in request.session:
        return redirect('ostadkar:add_sample_work')
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
        'state': '1234567890',
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
        # First try to get access token
        response = requests.post(settings.OAUTH_TOKEN_URL, data=token_data)
        response.raise_for_status()
        token_info = response.json()
        
        access_token = token_info.get('access_token')
        if not access_token:
            return render(request, 'ostadkar/error.html', {'error': 'Access token not received from OAuth provider'})
        
        # Then try to get user info
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-API-Key': oauth_settings['api_key']
            }
            user_info_response = requests.get(
                settings.OAUTH_USER_INFO_URL,
                headers=headers
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
            
            user_id = user_info.get('user_id')
            if not user_id:
                return render(request, 'ostadkar/error.html', {'error': 'User ID not found in user info response'})
            
            # Store only user_id in session
            request.session['user_id'] = user_id
            
            # Set session expiry
            request.session.set_expiry(3600)  # 1 hour
            
            # Redirect to add sample work page
            return redirect('ostadkar:add_sample_work')
            
        except requests.RequestException as e:
            return render(request, 'ostadkar/error.html', {'error': f'Failed to get user info: {str(e)}'})
            
    except requests.RequestException as e:
        return render(request, 'ostadkar/error.html', {'error': f'Failed to get access token: {str(e)}'})

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
