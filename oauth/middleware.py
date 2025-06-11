import requests
from django.shortcuts import redirect
from django.conf import settings

class SessionVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user_id = request.session.get('user_id')
            
            if user_id:
                # Verify user ID with Divar API
                headers = {
                    'X-API-KEY': settings.API_KEY,
                }
                try:
                    response = requests.post(
                        'https://open-api.divar.ir/v1/open-platform/users',
                        headers=headers,
                        json={}
                    )
                    response.raise_for_status()
                    api_user_id = response.json().get('user_id')
                    
                    if api_user_id != user_id:
                        # User ID mismatch, clear session and redirect to login
                        request.session.flush()
                        return redirect('oauth:login')
                except requests.exceptions.RequestException:
                    # If API call fails, keep the session
                    pass
            
        response = self.get_response(request)
        return response 