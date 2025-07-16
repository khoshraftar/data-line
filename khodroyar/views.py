from django.shortcuts import render, redirect, get_object_or_404
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
from datetime import datetime, timedelta
from .models import UserAuth, Conversation, Message, Payment

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
    
    request.session.flush()
    # Generate a random state parameter (at least 8 characters)
    state = str(uuid.uuid4())
 
    # Store state in session for validation in callback
    request.session['oauth_state'] = state
    
    # Prepare OAuth parameters
    params = {
        'client_id': oauth_settings['oauth_client_id'],
        'redirect_uri': oauth_settings['oauth_redirect_uri'],
        'response_type': 'code',
        'scope': oauth_settings['oauth_scope'],
        'state': state,
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
    
    # Validate state parameter
    if 'state' not in request.GET:
        return render(request, 'khodroyar/error.html', {
            'error': 'State parameter not received',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    # Get stored state from session
    stored_state = request.session.get('oauth_state')
    if not stored_state:
        return render(request, 'khodroyar/error.html', {
            'error': 'No stored state found in session',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    # Validate state parameter
    received_state = request.GET['state']
    if received_state != stored_state:
        return render(request, 'khodroyar/error.html', {
            'error': 'State parameter validation failed',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    # Clear the state from session after successful validation
    if 'oauth_state' in request.session:
        del request.session['oauth_state']
    
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
            
            # Store user_auth in session for payment flow
            request.session['user_auth_id'] = user_auth.id
            
            # Show success message and redirect to pre-payment page
            messages.success(request, 'ورود با موفقیت انجام شد!')
            return redirect('khodroyar:pre_payment')
            
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

def pre_payment(request):
    """Pre-payment page - describes Khodroyar and offers 7-day subscription"""
    # Get user_auth from session
    user_auth_id = request.session.get('user_auth_id')
    if not user_auth_id:
        return redirect('khodroyar:login')
    
    try:
        user_auth = UserAuth.objects.get(id=user_auth_id)
    except UserAuth.DoesNotExist:
        return redirect('khodroyar:login')
    
    return render(request, 'khodroyar/pre_payment.html', {
        'user_auth': user_auth,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def initiate_payment(request):
    """Initiate ZarinPal payment for Khodroyar subscription"""
    # Get user_auth from session
    user_auth_id = request.session.get('user_auth_id')
    if not user_auth_id:
        return redirect('khodroyar:login')
    
    try:
        user_auth = UserAuth.objects.get(id=user_auth_id)
    except UserAuth.DoesNotExist:
        return redirect('khodroyar:login')
    
    # Check if ZarinPal merchant ID is configured
    if not settings.ZARINPAL_MERCHANT_ID:
        messages.error(request, 'خطا در پیکربندی درگاه پرداخت. لطفاً با پشتیبانی تماس بگیرید.')
        return redirect('khodroyar:pre_payment')
    
    # Check if payment already exists and is pending
    existing_payment = Payment.objects.filter(
        user_auth=user_auth, 
        status='pending'
    ).first()
    
    if existing_payment:
        # If there's a pending payment, redirect to ZarinPal with existing authority
        if existing_payment.authority:
            payment_url = f"{settings.ZARINPAL_GATEWAY_URL}{existing_payment.authority}"
            return render(request, 'khodroyar/payment_loading.html', {
                'payment_url': payment_url,
                'user_auth': user_auth,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
    
    # Create new payment record
    payment = Payment.objects.create(
        user_auth=user_auth,
        amount=settings.KHODROYAR_PAYMENT_AMOUNT
    )
    
    # Prepare payment request data
    payment_data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': str(payment.amount),
        'description': f'اشتراک ۷ روزه خودرویار - {user_auth.user_id}',
        'callback_url': 'https://data-lines.ir/khodroyar/payment/callback/',
        'metadata': {
            'mobile': user_auth.phone or '09199187529',
            'email': ''
        }
    }
    
    try:
        # Send payment request to ZarinPal
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.post(settings.ZARINPAL_REQUEST_URL, json=payment_data, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if result['data']['code'] == 100:
            # Payment request successful
            authority = result['data']['authority']
            payment.authority = authority
            payment.save()
            
            # Show loading page with redirect to ZarinPal payment gateway
            payment_url = f"{settings.ZARINPAL_GATEWAY_URL}{authority}"
            return render(request, 'khodroyar/payment_loading.html', {
                'payment_url': payment_url,
                'user_auth': user_auth,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
        else:
            # Payment request failed
            payment.status = 'failed'
            payment.save()
            error_message = result.get('errors', {}).get('message', 'خطای نامشخص')
            messages.error(request, f'خطا در ایجاد درخواست پرداخت: {error_message}')
            return redirect('khodroyar:pre_payment')
            
    except requests.RequestException as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطا در ارتباط با درگاه پرداخت: {str(e)}')
        return redirect('khodroyar:pre_payment')
    except Exception as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطای غیرمنتظره: {str(e)}')
        return redirect('khodroyar:pre_payment')

def payment_callback(request):
    """Handle ZarinPal payment callback"""
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    
    if not authority:
        messages.error(request, 'کد مرجع پرداخت یافت نشد.')
        return redirect('khodroyar:home')
    
    try:
        payment = Payment.objects.get(authority=authority)
    except Payment.DoesNotExist:
        messages.error(request, 'پرداخت یافت نشد.')
        return redirect('khodroyar:home')
    
    if status == 'OK':
        # Payment was successful, verify with ZarinPal
        verify_data = {
            'merchant_id': settings.ZARINPAL_MERCHANT_ID,
            'amount': payment.amount,
            'authority': authority
        }
        
        try:
            response = requests.post(settings.ZARINPAL_VERIFY_URL, json=verify_data)
            response.raise_for_status()
            result = response.json()
            
            if result['data']['code'] == 100:
                # Payment verified successfully
                payment.status = 'completed'
                payment.ref_id = result['data']['ref_id']
                payment.subscription_start = datetime.now()
                payment.subscription_end = datetime.now() + timedelta(days=7)
                payment.save()
                
                messages.success(request, f'پرداخت با موفقیت انجام شد. شماره پیگیری: {payment.ref_id}')
                return redirect('khodroyar:payment_success')
            else:
                # Payment verification failed
                payment.status = 'failed'
                payment.save()
                messages.error(request, f'تایید پرداخت ناموفق بود: {result["errors"]["message"]}')
                return redirect('khodroyar:payment_failed')
                
        except requests.RequestException as e:
            payment.status = 'failed'
            payment.save()
            messages.error(request, f'خطا در تایید پرداخت: {str(e)}')
            return redirect('khodroyar:payment_failed')
    else:
        # Payment was cancelled or failed
        payment.status = 'cancelled'
        payment.save()
        messages.error(request, 'پرداخت لغو شد.')
        return redirect('khodroyar:payment_failed')

def payment_success(request):
    """Show payment success page"""
    # Get user_auth from session
    user_auth_id = request.session.get('user_auth_id')
    if not user_auth_id:
        return redirect('khodroyar:login')
    
    try:
        user_auth = UserAuth.objects.get(id=user_auth_id)
        payment = Payment.objects.filter(user_auth=user_auth, status='completed').first()
    except UserAuth.DoesNotExist:
        return redirect('khodroyar:login')
    
    return render(request, 'khodroyar/payment_success.html', {
        'user_auth': user_auth,
        'payment': payment,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def payment_failed(request):
    """Show payment failed page"""
    # Get user_auth from session
    user_auth_id = request.session.get('user_auth_id')
    if not user_auth_id:
        return redirect('khodroyar:login')
    
    try:
        user_auth = UserAuth.objects.get(id=user_auth_id)
        payment = Payment.objects.filter(user_auth=user_auth).order_by('-created_at').first()
    except UserAuth.DoesNotExist:
        return redirect('khodroyar:login')
    
    return render(request, 'khodroyar/payment_failed.html', {
        'user_auth': user_auth,
        'payment': payment,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })


# Chatbot API Views

@csrf_exempt
@require_http_methods(["POST"])
def receive_message(request):
    """API endpoint to receive messages from users"""
    try:
        data = json.loads(request.body)
        print(f"Received message: {data}")
        
        # Handle the new message format
        new_message = data.get('new_chatbot_message', {})
        
        # Extract fields from the new message format
        message_id = new_message.get('id')
        conversation_data = new_message.get('conversation', {})
        conversation_id = conversation_data.get('id')
        sender = new_message.get('sender', {})
        message_type = new_message.get('type')
        sent_at = new_message.get('sent_at')
        text = new_message.get('text')
        
        # Validate required fields
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Message text is required'
            }, status=400)
        
        if not conversation_id:
            return JsonResponse({
                'success': False,
                'error': 'Conversation ID is required'
            }, status=400)
        
        # Get existing conversation (assume it exists)
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
            user_auth = conversation.user_auth
        except Conversation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Conversation with ID {conversation_id} not found'
            }, status=404)
        
        # Save user message with metadata from the new format
        user_message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=text,
            metadata={
                'message_id': message_id,
                'sent_at': sent_at,
                'message_type': message_type,
                'sender_type': sender.get('type'),
                'conversation_type': conversation_data.get('type'),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Process message and generate bot response
        bot_response = generate_response(text, user_auth)
        
        # Save bot response
        bot_message = Message.objects.create(
            conversation=conversation,
            message_type='bot',
            content=bot_response,
            metadata={
                'sent_at': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        return JsonResponse({'success': True}, status=200)
        
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

