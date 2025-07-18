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
from .utils import to_shamsi_date, check_subscription_status
from .ai_agent import get_ai_agent

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
    """Pre-payment page - describes Khodroyar and offers 1-day and 1-week subscription options"""
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
    
    # Get plan from query parameters
    plan = request.GET.get('plan', 'golden')  # Default to golden plan
    
    # Set payment amount and description based on plan
    if plan == 'diamond':
        payment_amount = settings.KHODROYAR_DIAMOND_PAYMENT_AMOUNT
        plan_name = 'اشتراک الماس ۷ روزه'
        subscription_days = 7
    else:
        payment_amount = settings.KHODROYAR_PAYMENT_AMOUNT
        plan_name = 'اشتراک طلایی ۱ روزه'
        subscription_days = 1
    
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
        amount=payment_amount
    )
    
    # Store plan information in payment metadata
    payment.metadata = {
        'plan': plan,
        'subscription_days': subscription_days,
        'plan_name': plan_name
    }
    payment.save()
    
    # Prepare payment request data
    payment_data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': str(payment.amount),
        'description': f'{plan_name} خودرویار - {user_auth.user_id}',
        'callback_url': 'https://data-lines.ir/khodroyar/payment/callback/',
        'metadata': {
            'mobile': user_auth.phone or '09199187529',
            'email': '',
            'plan': plan,
            'subscription_days': subscription_days
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
                
                # Get subscription days from payment metadata
                subscription_days = payment.metadata.get('subscription_days', 1) if payment.metadata else 1
                payment.subscription_end = datetime.now() + timedelta(days=subscription_days)
                payment.save()
                
                # Send welcome message to user after successful payment
                try:
                    send_welcome_message_after_payment(payment.user_auth, payment)
                except Exception as e:
                    print(f"Failed to send welcome message after payment: {str(e)}")
                    # Don't fail the payment process if message sending fails
                
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
        bot_response = generate_response(text, user_auth, conversation_id)
        
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


def generate_response(message, user_auth, conversation_id=None):
    """Process user message using AI agent and send bot response"""
    try:
        # Get conversation if conversation_id is provided
        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(conversation_id=conversation_id)
            except Conversation.DoesNotExist:
                print(f"Conversation {conversation_id} not found")
        
        # Check subscription status first
        if user_auth:
            # Use the utility function to check subscription status
            has_ended, subscription_message = check_subscription_status(user_auth)
            
            if has_ended:
                # Subscription has ended or doesn't exist - return predefined message without engaging AI
                if conversation_id:
                    send_bot_message(user_auth, conversation_id, subscription_message)
                return subscription_message
        
        # Get user context (subscription info, etc.) for active subscriptions
        user_context = {}
        if user_auth:
            # Get active subscription
            active_payment = Payment.objects.filter(
                user_auth=user_auth,
                status='completed',
                subscription_end__gt=datetime.now()
            ).first()
            
            if active_payment:
                user_context = {
                    'subscription_end': to_shamsi_date(active_payment.subscription_end),
                    'plan_name': active_payment.metadata.get('plan_name', 'اشتراک طلایی'),
                    'subscription_days': active_payment.metadata.get('subscription_days', 1)
                }
        
        # Use the AI agent to generate the response
        ai_agent = get_ai_agent()
        
        if conversation:
            bot_response = ai_agent.generate_response(message, conversation, user_context)
        else:
            # Fallback response if no conversation context
            bot_response = "سلام! من ربات خودرویار هستم. برای شروع مکالمه، لطفاً پیام خود را ارسال کنید."
        
        # Send bot response using conversation_id if available
        if conversation_id:
            send_bot_message(user_auth, conversation_id, bot_response)
            
        return bot_response
            
    except Exception as e:
        error_response = f"متأسفانه مشکلی در پردازش پیام شما پیش آمد: {str(e)}"
        if conversation_id:
            send_bot_message(user_auth, conversation_id, error_response)
        return error_response


def send_bot_message(user_auth, conversation_id, message_text):
    """Send a bot message using the conversation_id"""
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
        
        # Prepare message data for Divar Chat API
        message_data = {
            "conversation_id": conversation_id,
            "text_message": message_text
        }
        
        # Send message using Divar Chat API
        chat_api_url = settings.DIVAR_CHAT_API_URL.format(conversation_id=conversation_id)
        
        response = requests.post(
            chat_api_url,
            headers=headers,
            json=message_data
        )
        
        if response.status_code == 200:
            print(f"Bot message sent successfully to conversation {conversation_id}")
            return True
        else:
            print(f"Failed to send bot message. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending bot message: {str(e)}")
        return False


def send_welcome_message_after_payment(user_auth, payment):
    """
    Send a welcome message to the user after successful payment using Divar Chat API
    First sends message using user_id to get conversation_id, then creates conversation in database
    """
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
        
        # Prepare welcome message
        welcome_message = f"""🎉 تبریک! اشتراک خودرویار شما با موفقیت فعال شد!

✅ پرداخت شما تایید شد
💰 مبلغ: {payment.amount:,} ریال
📅 شروع اشتراک: {to_shamsi_date(payment.subscription_start)}
📅 پایان اشتراک: {to_shamsi_date(payment.subscription_end)}
🔢 شماره پیگیری: {payment.ref_id}

🚗 حالا می‌توانید از خدمات خودرویار استفاده کنید:
• جستجوی خودرو
• اطلاعات قیمت
• مقایسه خودروها
• راهنمای خرید

برای شروع، پیام خود را بنویسید!"""

        # First, send welcome message using user_id to get conversation_id
        # Use a different endpoint that accepts user_id instead of conversation_id
        initial_message_data = {
            "user_id": user_auth.user_id,
            "text_message": welcome_message
        }
        
        # Use the experimental endpoint for initial message with user_id
        initial_chat_api_url = 'https://open-api.divar.ir/v1/open-platform/chat/bot/users/{user_id}/messages'
        
        response = requests.post(
            initial_chat_api_url,
            headers=headers,
            json=initial_message_data
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract conversation_id from the response
            conversation_id = response_data.get('conversation_id')
            
            if conversation_id:
                # Create conversation in our database with the received conversation_id
                conversation = Conversation.objects.create(
                    user_auth=user_auth,
                    conversation_id=conversation_id,
                    title='خودرویار - اشتراک جدید',
                    is_active=True
                )
                
                # Save the bot message to our database
                Message.objects.create(
                    conversation=conversation,
                    message_type='bot',
                    content=welcome_message,
                    metadata={
                        'sent_at': datetime.now().isoformat(),
                        'timestamp': datetime.now().isoformat(),
                        'payment_ref_id': payment.ref_id,
                        'subscription_start': payment.subscription_start.isoformat(),
                        'subscription_end': payment.subscription_end.isoformat(),
                        'conversation_id': conversation_id
                    }
                )
                
                print(f"Welcome message sent successfully to user {user_auth.user_id} with conversation_id: {conversation_id}")
                return True
            else:
                print(f"Failed to get conversation_id from response: {response_data}")
                return False
        else:
            print(f"Failed to send welcome message. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending welcome message: {str(e)}")
        return False

