from django.shortcuts import render, redirect
from django.conf import settings
from django.views import View
from django.http import HttpResponse
import requests
import json
from urllib.parse import urlencode
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
import hashlib

# Create your views here.

class OAuthLoginView(View):
    def get(self, request):
        # Show the loading page first
        return render(request, 'oauth/redirect.html')

class OAuthRedirectView(View):
    def get(self, request):
        # Prepare OAuth parameters
        params = {
            'client_id': settings.OAUTH_CLIENT_ID,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'response_type': 'code',
            'scope': settings.OAUTH_SCOPE,
            'state': 'random_state_string'  # You should generate and validate this
        }
        # Redirect to Divar's authorization page
        auth_url = f"{settings.OAUTH_AUTHORIZATION_URL}?{urlencode(params)}"
        return redirect(auth_url)

class OAuthCallbackView(View):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return HttpResponse('No code provided', status=400)

        # Exchange code for token
        token_url = settings.OAUTH_TOKEN_URL
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'client_id': settings.OAUTH_CLIENT_ID,
            'client_secret': settings.OAUTH_CLIENT_SECRET,
        }
        headers = {
            'X-API-Key': settings.API_KEY,
        }

        try:
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            
            # Get user ID from Divar API using access token
            user_id_url = 'https://open-api.divar.ir/v1/open-platform/users'
            headers = {
                'X-API-Key': settings.API_KEY,
                'Authorization': f'Bearer {token_data["access_token"]}'
            }
            user_id_response = requests.post(user_id_url, headers=headers, json={})
            user_id_response.raise_for_status()
            user_id_data = user_id_response.json()
            user_id = user_id_data.get('user_id')

            if not user_id:
                return HttpResponse('Failed to get user ID', status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                username=user_id,  # Use user_id as username
                defaults={
                    'is_active': True,
                }
            )

            # Set session data with user ID only
            request.session['user_id'] = user_id

            # Log the user in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            return redirect('dashboard:dashboard')

        except requests.exceptions.RequestException as e:
            return HttpResponse(f'Error: {str(e)}', status=500)

def logout(request):
    # Clear session data
    request.session.flush()
    return redirect('home')
