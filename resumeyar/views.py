from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
import requests
from urllib.parse import urlencode

def home(request):
    return render(request, 'resumeyar/home.html')

def login(request):
    """Show login page"""
    return render(request, 'resumeyar/login.html')

def oauth_login(request):
    """Initiate OAuth login process"""
    oauth_settings = settings.OAUTH_APPS_SETTINGS['resumeyar']
    
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
        return render(request, 'resumeyar/error.html', {'error': 'Authorization code not received'})
    
    oauth_settings = settings.OAUTH_APPS_SETTINGS['resumeyar']
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
        
        return redirect('resumeyar:dashboard')
    except requests.RequestException as e:
        return render(request, 'resumeyar/error.html', {'error': f'Failed to get access token: {str(e)}'})

def about(request):
    return render(request, 'about.html')

@login_required
def dashboard(request):
    if 'access_token' not in request.session:
        return redirect('resumeyar:login')
    return render(request, 'resumeyar/dashboard.html')

@login_required
def my_resumes(request):
    # TODO: Add resume list logic
    return render(request, 'resumeyar/my_resumes.html')

@login_required
def create_resume(request):
    # TODO: Add resume creation logic
    return render(request, 'resumeyar/create_resume.html')

@login_required
def edit_resume(request, resume_id):
    # TODO: Add resume editing logic
    return render(request, 'resumeyar/edit_resume.html')

@login_required
def resume_templates(request):
    # TODO: Add templates list logic
    return render(request, 'resumeyar/templates.html')

@login_required
def settings(request):
    # TODO: Add settings logic
    return render(request, 'resumeyar/settings.html')
