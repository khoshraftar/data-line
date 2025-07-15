from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode, unquote
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
from datetime import datetime
from .models import UserAuth, Conversation, Message

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


# Chatbot API Views

@csrf_exempt
@require_http_methods(["POST"])
def receive_message(request):
    """API endpoint to receive messages from users"""
    try:
        data = json.loads(request.body)
        
        # Extract required fields
        user_id = data.get('user_id')
        message_content = data.get('message')
        conversation_id = data.get('conversation_id')
        
        if not user_id or not message_content:
            return JsonResponse({
                'success': False,
                'error': 'user_id and message are required'
            }, status=400)
        
        # Get or create user auth
        try:
            user_auth = UserAuth.objects.get(user_id=user_id)
        except UserAuth.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not authenticated'
            }, status=401)
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=conversation_id,
                    user_auth=user_auth
                )
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create(
                    user_auth=user_auth,
                    conversation_id=conversation_id,
                    title=message_content[:100]  # Use first 100 chars as title
                )
        else:
            # Create new conversation
            conversation = Conversation.objects.create(
                user_auth=user_auth,
                conversation_id=str(uuid.uuid4()),
                title=message_content[:100]
            )
        
        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=message_content,
            metadata={'timestamp': datetime.now().isoformat()}
        )
        
        # Process message and generate bot response
        bot_response = generate_response(message_content, user_auth)
        
        # Save bot response
        bot_message = Message.objects.create(
            conversation=conversation,
            message_type='bot',
            content=bot_response,
            metadata={'timestamp': datetime.now().isoformat()}
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'conversation_id': conversation.conversation_id,
                'bot_response': bot_response,
                'message_id': bot_message.id
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def generate_response(message, user_auth):
    """Process user message using Divar APIs"""
    try:
        # Get user's access token
        access_token = user_auth.access_token
        oauth_settings = settings.OAUTH_APPS_SETTINGS['khodroyar']
        
        # Prepare headers for Divar API calls
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': oauth_settings['api_key'],
            'Content-Type': 'application/json'
        }
        
        # Simple message processing logic
        # You can extend this based on your specific chatbot requirements
        
        # Check if message contains keywords for specific actions
        message_lower = message.lower()
        
        if 'help' in message_lower or 'راهنما' in message_lower:
            return "سلام! من ربات خودرویار هستم. می‌توانم در موارد زیر به شما کمک کنم:\n- جستجوی خودرو\n- اطلاعات قیمت\n- مقایسه خودروها\n\n چه کمکی از دستم بر می‌آید؟"
        
        elif 'search' in message_lower or 'جستجو' in message_lower:
            # Here you would integrate with Divar's search API
            return "برای جستجوی خودرو، لطفاً مشخصات مورد نظر خود را وارد کنید (مثل: برند، مدل، سال ساخت)"
        
        elif 'price' in message_lower or 'قیمت' in message_lower:
            return "برای دریافت اطلاعات قیمت، لطفاً مدل خودروی مورد نظر را مشخص کنید."
        
        else:
            # Default response - you can integrate with AI services here
            return "متوجه پیام شما شدم. لطفاً بفرمایید چه کمکی از دستم بر می‌آید؟"
            
    except Exception as e:
        return f"متأسفانه مشکلی در پردازش پیام شما پیش آمد: {str(e)}"

