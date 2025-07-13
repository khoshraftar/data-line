from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode, unquote
from django.contrib import messages
from functools import wraps
from .models import UserAuth, PostImage, SampleWork, Payment, PostAddon
from .forms import SampleWorkForm, SampleWorkImageForm 
import json

def session_auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session:
            # Check if we have post_token in kwargs to pass to login
            post_token = kwargs.get('post_token')
            if post_token:
                return redirect('ostadkar:login_with_token', post_token=post_token)
            else:
                return redirect('ostadkar:login')
        
        # Get user auth from database
        try:
            user_auth = UserAuth.objects.get(user_id=request.session['user_id'])
            request.user_auth = user_auth
        except UserAuth.DoesNotExist:
            # Clear session if user not found in database
            request.session.flush()
            # Check if we have post_token in kwargs to pass to login
            post_token = kwargs.get('post_token')
            if post_token:
                return redirect('ostadkar:login_with_token', post_token=post_token)
            else:
                return redirect('ostadkar:login')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Create your views here.

def home(request, post_token=None):
    # If post_token is provided via GET parameter, redirect to the URL with post_token
    if not post_token and 'post_token' in request.GET:
        post_token = request.GET['post_token'].strip()
        if post_token:  # Only redirect if post_token is not empty
            return redirect('ostadkar:home_with_token', post_token=post_token)
    
    # Clean up post_token if it exists
    if post_token:
        post_token = post_token.strip()
        # Decode URL-encoded characters in post_token if present
        post_token = unquote(post_token)
    
    return render(request, 'ostadkar/home.html', {
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def login(request, post_token=None):
    """Show login page"""
    # If user is already authenticated, redirect to add sample work
    if 'user_id' in request.session:
        try:
            UserAuth.objects.get(user_id=request.session['user_id'])
            if post_token:
                return redirect('ostadkar:add_sample_work', post_token=post_token)
            else:
                return redirect('ostadkar:post_images', post_token='default1')
        except UserAuth.DoesNotExist:
            request.session.flush()
    
    return render(request, 'ostadkar/login.html', {
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def oauth_login(request, post_token):
    """Initiate OAuth login process"""
    oauth_settings = settings.OAUTH_APPS_SETTINGS['ostadkar']
    post_token = post_token.strip()
    
    # Decode URL-encoded characters in post_token if present
    # This prevents double encoding when the scope is URL-encoded
    decoded_post_token = unquote(post_token)
    
    # Store post_token in session for callback
    request.session['post_token'] = decoded_post_token
    
    # Format the scope with decoded post_token before URL encoding
    scope = oauth_settings['oauth_scope'].format(post_token=decoded_post_token)
    
    # Prepare OAuth parameters
    params = {
        'client_id': oauth_settings['oauth_client_id'],
        'redirect_uri': oauth_settings['oauth_redirect_uri'],
        'response_type': 'code',
        'scope': scope,
        'state': decoded_post_token,
    }
    
    # Construct authorization URL
    auth_url = f"{settings.OAUTH_AUTHORIZATION_URL}?{urlencode(params)}"
    return redirect(auth_url)

def oauth_callback(request):
    """Handle OAuth callback"""
    if 'code' not in request.GET:
        return render(request, 'ostadkar/error.html', {
            'error': 'Authorization code not received',
            'post_token': request.GET.get('state', ''),
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    oauth_settings = settings.OAUTH_APPS_SETTINGS['ostadkar']
    code = request.GET['code']
    
    # Get post_token from state parameter
    state = request.GET.get('state', '')
    
    post_token = state
    
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
            return render(request, 'ostadkar/error.html', {
                'error': 'Access token not received from OAuth provider',
                'post_token': post_token,
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
                return render(request, 'ostadkar/error.html', {
                    'error': 'User ID not found in user info response',
                    'post_token': post_token,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            # Extract phone number from user info
            phone = user_info.get('phone', '')
            
            # Create or update user auth in database
            user_auth, created = UserAuth.objects.update_or_create(
                user_id=user_id,
                defaults={
                    'access_token': access_token,
                    'phone': phone
                }
            )
            
            # Store user_id in session
            request.session['user_id'] = user_id
            
            # Set session expiry
            request.session.set_expiry(600)  # 10 minutes
            
            # Redirect to add post image page with post_token
            return redirect('ostadkar:add_sample_work', post_token=post_token)
            
        except requests.RequestException as e:
            return render(request, 'ostadkar/error.html', {
                'error': f'Failed to get user info: {str(e)}',
                'post_token': post_token,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
            
    except requests.RequestException as e:
        return render(request, 'ostadkar/error.html', {
            'error': f'Failed to get access token: {str(e)}',
            'post_token': post_token,
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })

@session_auth_required
def add_sample_work(request, post_token='AaxBDckp'):
    if request.method == 'POST':
        form = SampleWorkForm(request.POST)
        if form.is_valid():
            # Delete existing sample work with this token if it exists
            existing_sample_work = SampleWork.objects.filter(post_token=post_token).first()
            if existing_sample_work:
                # Delete associated images first (due to foreign key constraint)
                PostImage.objects.filter(sample_work=existing_sample_work).delete()
                # Delete the sample work
                existing_sample_work.delete()
            
            # Create new sample work
            sample_work = form.save(commit=False)
            sample_work.user = request.user_auth
            sample_work.post_token = post_token
            sample_work.save()
            
            return redirect('ostadkar:upload_sample_work_images', work_id=sample_work.uuid)
    else:
        form = SampleWorkForm()
    
    return render(request, 'ostadkar/add_sample_work.html', {
        'form': form,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def upload_sample_work_images(request, work_id):
    sample_work = get_object_or_404(SampleWork, uuid=work_id, user=request.user_auth)
    
    if request.method == 'POST':
        form = SampleWorkImageForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('images')
            
            # Additional validation for maximum 24 images
            if len(files) > 24:
                messages.error(request, 'حداکثر ۲۴ تصویر می‌توانید آپلود کنید.')
                return render(request, 'ostadkar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            # Validate total upload size (max 60MB for 24 images * 2.5MB each)
            total_size = sum(file.size for file in files)
            if total_size > 62914560:  # 60MB in bytes
                messages.error(request, 'حجم کل فایل‌ها بیش از ۶۰ مگابایت است.')
                return render(request, 'ostadkar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            try:
                for image_file in files:
                    PostImage.objects.create(
                        sample_work=sample_work,
                        image=image_file
                    )
                
                return redirect('ostadkar:post_images_preview', post_token=sample_work.post_token)
                
            except Exception as e:
                messages.error(request, f'خطا در آپلود تصاویر: {str(e)}')
                return render(request, 'ostadkar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
    else:
        form = SampleWorkImageForm()
    
    return render(request, 'ostadkar/upload_sample_work_images.html', {
        'form': form,
        'sample_work': sample_work,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def post_images(request, post_token):
    # For public access, we need to find the sample work by post_token only
    # without requiring user authentication
    # Use all_including_archived() to get archived sample works too
    sample_work = get_object_or_404(SampleWork.all_including_archived(), post_token=post_token)
    
    # Check if the sample work is archived
    if sample_work.is_archived:
        return render(request, 'ostadkar/post_images.html', {
            'sample_work': sample_work,
            'post_images': [],
            'post_token': post_token,
            'is_archived': True,
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/post_images.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token,
        'is_archived': False,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def post_images_preview(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        }, status=403)
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/post_images_preview.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })


@session_auth_required
def pre_payment(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        }, status=403)
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/pre_payment.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def initiate_payment(request, post_token):
    """Initiate ZarinPal payment"""
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        }, status=403)
    
    # Check if ZarinPal merchant ID is configured
    if not settings.ZARINPAL_MERCHANT_ID:
        messages.error(request, 'خطا در پیکربندی درگاه پرداخت. لطفاً با پشتیبانی تماس بگیرید.')
        return redirect('ostadkar:pre_payment', post_token=post_token)
    
    # Check if payment already exists and is pending
    existing_payment = Payment.objects.filter(
        sample_work=sample_work, 
        status='pending'
    ).first()
    
    if existing_payment:
        # If there's a pending payment, redirect to ZarinPal with existing authority
        if existing_payment.authority:
            payment_url = f"{settings.ZARINPAL_GATEWAY_URL}{existing_payment.authority}"
            return render(request, 'ostadkar/payment_loading.html', {
                'payment_url': payment_url,
                'sample_work': sample_work,
                'post_token': post_token,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
    
    # Create new payment record
    payment = Payment.objects.create(
        sample_work=sample_work,
        amount=settings.PAYMENT_AMOUNT
    )
    
    # Prepare payment request data
    payment_data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': str(payment.amount),
        'description': f'پرداخت برای نمونه کار: {sample_work.title}',
        'callback_url': settings.ZARINPAL_CALLBACK_URL,
        'metadata': {
            'mobile': sample_work.user.phone or '09199187529',  # Use stored phone or fallback
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
            return render(request, 'ostadkar/payment_loading.html', {
                'payment_url': payment_url,
                'sample_work': sample_work,
                'post_token': post_token,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
        else:
            
            # Payment request failed
            payment.status = 'failed'
            payment.save()
            error_message = result.get('errors', {}).get('message', 'خطای نامشخص')
            messages.error(request, f'خطا در ایجاد درخواست پرداخت: {error_message}')
            return redirect('ostadkar:pre_payment', post_token=post_token)
            
    except requests.RequestException as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطا در ارتباط با درگاه پرداخت: {str(e)}')
        return redirect('ostadkar:pre_payment', post_token=post_token)
    except Exception as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطای غیرمنتظره: {str(e)}')
        return redirect('ostadkar:pre_payment', post_token=post_token)

def payment_callback(request):
    """Handle ZarinPal payment callback"""
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    
    if not authority:
        messages.error(request, 'کد مرجع پرداخت یافت نشد.')
        return redirect('ostadkar:home')
    
    try:
        payment = Payment.objects.get(authority=authority)
    except Payment.DoesNotExist:
        messages.error(request, 'پرداخت یافت نشد.')
        return redirect('ostadkar:home')
    
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
                payment.save()
                
                messages.success(request, f'پرداخت با موفقیت انجام شد. شماره پیگیری: {payment.ref_id}')
                return redirect('ostadkar:payment_success', post_token=payment.sample_work.post_token)
            else:
                # Payment verification failed
                payment.status = 'failed'
                payment.save()
                messages.error(request, f'تایید پرداخت ناموفق بود: {result["errors"]["message"]}')
                return redirect('ostadkar:payment_failed', post_token=payment.sample_work.post_token)
                
        except requests.RequestException as e:
            payment.status = 'failed'
            payment.save()
            messages.error(request, f'خطا در تایید پرداخت: {str(e)}')
            return redirect('ostadkar:payment_failed', post_token=payment.sample_work.post_token)
    else:
        # Payment was cancelled or failed
        payment.status = 'cancelled'
        payment.save()
        messages.warning(request, 'پرداخت لغو شد.')
        return redirect('ostadkar:payment_failed', post_token=payment.sample_work.post_token)

def payment_success(request, post_token):
    """Show payment success page"""
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    payment = Payment.objects.filter(sample_work=sample_work, status='completed').first()
    
    # Create addon for the post using Divar API
    if payment and sample_work.user.access_token:
        addon_result = create_post_addon(sample_work)
        if addon_result.get('success'):
            messages.success(request, 'افزونه پست با موفقیت ایجاد شد.')
        else:
            messages.warning(request, f'خطا در ایجاد افزونه پست: {addon_result.get("error", "خطای نامشخص")}')
    
    return render(request, 'ostadkar/payment_success.html', {
        'sample_work': sample_work,
        'payment': payment,
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def create_post_addon(sample_work):
    """
    Create an addon for a post using Divar API
    Based on: https://divar-ir.github.io/kenar-docs/openapi-doc/addons-create-post-addon-v-2
    """
    # Check if addon already exists for this payment
    existing_addon = PostAddon.objects.filter(sample_work=sample_work).first()
    if existing_addon:
        if existing_addon.status == 'created':
            return {
                'success': True,
                'addon_id': existing_addon.addon_id,
                'message': 'Addon already exists'
            }
        elif existing_addon.status == 'failed':
            # Try again if previous attempt failed
            existing_addon.delete()
    
    # Create a new addon record
    addon = PostAddon.objects.create(
        sample_work=sample_work,
        duration=30,  # Default duration in days
        status='pending'
    )
    
    try:
        # Prepare the addon data according to Divar API documentation
        addon_data = {
            "widgets": [
                {
                    "description_row": {
                        "expandable": False,
                        "has_divider": True,
                        "text": "مشاهده آلبوم کامل تصاویر نمونه کار های تایید شده در سایت استادکار"
                }},
                {
                    "button_bar": {
                        "title": "آلبوم نمونه کار",
                        "action": {
                            "open_direct_link": f"https://data-lines.ir/ostadkar/sample-work/post-images/{sample_work.post_token}"
                        }
                    }
                }

            ]
        }
        
        
        # Get user's access token
        access_token = sample_work.user.access_token
        
        # Prepare headers with authorization
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': settings.OAUTH_APPS_SETTINGS['ostadkar']['api_key']
        }
        
        # Make API request to create addon
        response = requests.post(
            settings.DIVAR_ADDON_CREATE_URL.format(post_token=sample_work.post_token),
            json=addon_data,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Check if the addon was created successfully
        if response.status_code == 200:
            # Update addon record with success
            addon.status = 'created'
            addon.addon_id = result.get('data', {}).get('addon_id')
            addon.save()
            
            return {
                'success': True,
                'addon_id': addon.addon_id,
                'message': 'Addon created successfully'
            }
        else:
            # Update addon record with failure
            error_message = result.get('error', {}).get('message', 'Unknown error')
            addon.status = 'failed'
            addon.error_message = error_message
            addon.save()
            
            return {
                'success': False,
                'error': error_message
            }
            
    except requests.RequestException as e:
        # Update addon record with network error
        error_message = f'Network error: {str(e)}'
        addon.status = 'failed'
        addon.error_message = error_message
        addon.save()
        
        return {
            'success': False,
            'error': error_message
        }
    except Exception as e:
        # Update addon record with unexpected error
        error_message = f'Unexpected error: {str(e)}'
        addon.status = 'failed'
        addon.error_message = error_message
        addon.save()
        
        return {
            'success': False,
            'error': error_message
        }

def payment_failed(request, post_token):
    """Show payment failed page"""
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    payment = Payment.objects.filter(sample_work=sample_work).order_by('-created_at').first()
    
    return render(request, 'ostadkar/payment_failed.html', {
        'sample_work': sample_work,
        'payment': payment,
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })
