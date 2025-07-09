from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode
from django.contrib import messages
from functools import wraps
from .models import UserAuth, PostImage, SampleWork, Payment
from .forms import SampleWorkForm, SampleWorkImageForm 

def session_auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('ostadkar:login')
        
        # Get user auth from database
        try:
            user_auth = UserAuth.objects.get(user_id=request.session['user_id'])
            request.user_auth = user_auth
        except UserAuth.DoesNotExist:
            # Clear session if user not found in database
            request.session.flush()
            return redirect('ostadkar:login')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Create your views here.

def home(request):
    return render(request, 'ostadkar/home.html')

def login(request):
    """Show login page"""
    # If user is already authenticated, redirect to add sample work
    if 'user_id' in request.session:
        try:
            UserAuth.objects.get(user_id=request.session['user_id'])
            return redirect('ostadkar:post_images', post_token='default1')
        except UserAuth.DoesNotExist:
            request.session.flush()
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
            
            # Create or update user auth in database
            user_auth, created = UserAuth.objects.update_or_create(
                user_id=user_id,
                defaults={'access_token': access_token}
            )
            
            # Store user_id in session
            request.session['user_id'] = user_id
            
            # Set session expiry
            request.session.set_expiry(3600)  # 1 hour
            
            # Redirect to add post image page
            return redirect('ostadkar:add_sample_work')
            
        except requests.RequestException as e:
            return render(request, 'ostadkar/error.html', {'error': f'Failed to get user info: {str(e)}'})
            
    except requests.RequestException as e:
        return render(request, 'ostadkar/error.html', {'error': f'Failed to get access token: {str(e)}'})

@session_auth_required
def add_sample_work(request):
    post_token = 'default1'
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
    
    return render(request, 'ostadkar/add_sample_work.html', {'form': form})

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
                    'sample_work': sample_work
                })
            
            # Validate total upload size (max 60MB for 24 images * 2.5MB each)
            total_size = sum(file.size for file in files)
            if total_size > 62914560:  # 60MB in bytes
                messages.error(request, 'حجم کل فایل‌ها بیش از ۶۰ مگابایت است.')
                return render(request, 'ostadkar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work
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
                    'sample_work': sample_work
                })
    else:
        form = SampleWorkImageForm()
    
    return render(request, 'ostadkar/upload_sample_work_images.html', {
        'form': form,
        'sample_work': sample_work
    })

def post_images(request, post_token):
    # For public access, we need to find the sample work by post_token only
    # without requiring user authentication
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/post_images.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token
    })

@session_auth_required
def post_images_preview(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.'
        }, status=403)
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/post_images_preview.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token
    })

@session_auth_required
def sample_work_preview(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/sample_work_preview.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token
    })

@session_auth_required
def sample_works(request):
    sample_works = SampleWork.objects.filter(user=request.user_auth)
    return render(request, 'ostadkar/sample_works.html', {
        'sample_works': sample_works
    })

@session_auth_required
def pre_payment(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.'
        }, status=403)
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'ostadkar/pre_payment.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token
    })

@session_auth_required
def initiate_payment(request, post_token):
    """Initiate ZarinPal payment"""
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'ostadkar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.'
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
                'post_token': post_token
            })
    
    # Create new payment record
    payment = Payment.objects.create(
        sample_work=sample_work,
        amount=settings.PAYMENT_AMOUNT
    )
    
    # Prepare payment request data
    payment_data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': payment.amount,
        'description': f'پرداخت برای نمونه کار: {sample_work.title}',
        'callback_url': settings.ZARINPAL_CALLBACK_URL,
        'metadata': {
            'mobile': '',
            'email': ''
        }
    }
    
    try:
        # Send payment request to ZarinPal
        print(f"Payment request data: {payment_data}")  # Debug info
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.post(settings.ZARINPAL_REQUEST_URL, json=payment_data, headers=headers)
        print(f"Response status: {response.status_code}")  # Debug info
        print(f"Response content: {response.text}")  # Debug info
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
                'post_token': post_token
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
    
    return render(request, 'ostadkar/payment_success.html', {
        'sample_work': sample_work,
        'payment': payment,
        'post_token': post_token
    })

def payment_failed(request, post_token):
    """Show payment failed page"""
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    payment = Payment.objects.filter(sample_work=sample_work).order_by('-created_at').first()
    
    return render(request, 'ostadkar/payment_failed.html', {
        'sample_work': sample_work,
        'payment': payment,
        'post_token': post_token
    })