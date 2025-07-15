from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode, unquote
from django.contrib import messages
from .models import UserAuth

# Create your views here.

def home(request):
    """Khodroyar home page view"""
    return render(request, 'khodroyar/home.html')

def login(request):
    """Show login page"""
    return render(request, 'khodroyar/login.html', {
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def oauth_login(request):
    """Initiate OAuth login process"""
    oauth_settings = settings.OAUTH_APPS_SETTINGS['khodroyar']
    
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
        return render(request, 'khodroyar/error.html', {
            'error': 'Authorization code not received',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    oauth_settings = settings.OAUTH_APPS_SETTINGS['khodroyar']
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
            return render(request, 'khodroyar/error.html', {
                'error': 'Access token not received from OAuth provider',
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
        
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
                return render(request, 'khodroyar/error.html', {
                    'error': 'User ID not found in user info response',
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            # Extract phone number from user info
            phone = user_info.get('phone_number', '')
            
            # Create or update user auth in database (no session management)
            user_auth, created = UserAuth.objects.update_or_create(
                user_id=user_id,
                defaults={
                    'access_token': access_token,
                    'phone': phone
                }
            )
            
            # Show success message and redirect to home
            messages.success(request, 'ورود با موفقیت انجام شد!')
            return redirect('khodroyar:home')
            
        except requests.RequestException as e:
            return render(request, 'khodroyar/error.html', {
                'error': f'Failed to get user info: {str(e)}',
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
            
    except requests.RequestException as e:
        return render(request, 'khodroyar/error.html', {
            'error': f'Failed to get access token: {str(e)}',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })

def dashboard(request):
    """Dashboard view - shows user's stored tokens"""
    # Get all user auth records (in a real app, you might want to filter by some criteria)
    user_auths = UserAuth.objects.all().order_by('-created_at')
    
    return render(request, 'khodroyar/dashboard.html', {
        'user_auths': user_auths,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })
