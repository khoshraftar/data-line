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
from django.http import JsonResponse
import os

def session_auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session:
            # Check if we have post_token in kwargs to pass to login
            post_token = kwargs.get('post_token')
            if post_token:
                return redirect('nemoonekar:login_with_token', post_token=post_token)
            else:
                return redirect('nemoonekar:login')
        
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
                return redirect('nemoonekar:login_with_token', post_token=post_token)
            else:
                return redirect('nemoonekar:login')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Create your views here.

def home(request, post_token=None):
    # Clear session every time home is accessed
    request.session.flush()
    
    # If post_token is provided via GET parameter, redirect to the URL with post_token
    if not post_token and 'post_token' in request.GET:
        post_token = request.GET['post_token'].strip()
        if post_token:  # Only redirect if post_token is not empty
            return redirect('nemoonekar:home_with_token', post_token=post_token)
    
    # Clean up post_token if it exists
    if post_token:
        post_token = post_token.strip()
        # Decode URL-encoded characters in post_token if present
        post_token = unquote(post_token)
    
    return render(request, 'nemoonekar/home.html', {
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
                return redirect('nemoonekar:add_sample_work', post_token=post_token)
            else:
                return redirect('nemoonekar:post_images', post_token='default1')
        except UserAuth.DoesNotExist:
            request.session.flush()
    
    return render(request, 'nemoonekar/login.html', {
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

def oauth_login(request, post_token):
    """Initiate OAuth login process"""
    oauth_settings = settings.OAUTH_APPS_SETTINGS['nemoonekar']
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
        return render(request, 'nemoonekar/error.html', {
            'error': 'Authorization code not received',
            'post_token': request.GET.get('state', ''),
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    oauth_settings = settings.OAUTH_APPS_SETTINGS['nemoonekar']
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
            return render(request, 'nemoonekar/error.html', {
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
                return render(request, 'nemoonekar/error.html', {
                    'error': 'User ID not found in user info response',
                    'post_token': post_token,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            # Extract phone number from user info
            phone = user_info.get('phone_number', '')
            
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
            request.session.set_expiry(1200)  # 20 minutes
            
            # Redirect to add post image page with post_token
            return redirect('nemoonekar:add_sample_work', post_token=post_token)
            
        except requests.RequestException as e:
            return render(request, 'nemoonekar/error.html', {
                'error': f'Failed to get user info: {str(e)}',
                'post_token': post_token,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
            
    except requests.RequestException as e:
        return render(request, 'nemoonekar/error.html', {
            'error': f'Failed to get access token: {str(e)}',
            'post_token': post_token,
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })

@session_auth_required
def add_sample_work(request, post_token):
    if request.method == 'POST':
        form = SampleWorkForm(request.POST)
        if form.is_valid():
            # Check if sample work already exists for this token
            existing_sample_work = SampleWork.objects.filter(post_token=post_token).first()
            
            if existing_sample_work:
                # Check if the current user owns this sample work
                if existing_sample_work.user != request.user_auth:
                    return render(request, 'nemoonekar/permission_denied.html', {
                        'message': 'شما اجازه ویرایش این نمونه کار را ندارید.',
                        'divar_completion_url': settings.DIVAR_COMPLETION_URL,
                        'post_token': post_token
                    }, status=403)
                
                # Update existing sample work
                existing_sample_work.title = form.cleaned_data['title']
                existing_sample_work.description = form.cleaned_data['description']
                existing_sample_work.save()
                sample_work = existing_sample_work
            else:
                # Create new sample work
                sample_work = form.save(commit=False)
                sample_work.user = request.user_auth
                sample_work.post_token = post_token
                sample_work.save()
            
            return redirect('nemoonekar:upload_sample_work_images', work_id=sample_work.uuid)
    else:
        # Check if sample work already exists for this token
        existing_sample_work = SampleWork.objects.filter(post_token=post_token).first()
        
        if existing_sample_work:
            # Check if the current user owns this sample work
            if existing_sample_work.user != request.user_auth:
                return render(request, 'nemoonekar/permission_denied.html', {
                    'message': 'شما اجازه ویرایش این نمونه کار را ندارید.',
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL,
                    'post_token': post_token
                }, status=403)
            
            # Prefill form with existing data
            form = SampleWorkForm(instance=existing_sample_work)
            # Pass existing sample work to template for context
            return render(request, 'nemoonekar/add_sample_work.html', {
                'form': form,
                'existing_sample_work': existing_sample_work,
                'divar_completion_url': settings.DIVAR_COMPLETION_URL
            })
        else:
            form = SampleWorkForm()
    
    return render(request, 'nemoonekar/add_sample_work.html', {
        'form': form,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def upload_sample_work_images(request, work_id):
    sample_work = get_object_or_404(SampleWork, uuid=work_id, user=request.user_auth)
    
    # Get existing images for this sample work
    existing_images = PostImage.objects.filter(sample_work=sample_work).order_by('created_at')
    existing_image_count = existing_images.count()
    
    if request.method == 'POST':
        form = SampleWorkImageForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('images')
            
            # Check if adding new images would exceed the maximum of 24
            if existing_image_count + len(files) > 24:
                messages.error(request, f'با {existing_image_count} تصویر موجود، حداکثر {24 - existing_image_count} تصویر جدید می‌توانید اضافه کنید.')
                return render(request, 'nemoonekar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'existing_images': existing_images,
                    'existing_image_count': existing_image_count,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            # Validate total upload size (max 60MB for 24 images * 2.5MB each)
            total_size = sum(file.size for file in files)
            if total_size > 62914560:  # 60MB in bytes
                messages.error(request, 'حجم کل فایل‌ها بیش از ۶۰ مگابایت است.')
                return render(request, 'nemoonekar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'existing_images': existing_images,
                    'existing_image_count': existing_image_count,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
            
            try:
                for image_file in files:
                    PostImage.objects.create(
                        sample_work=sample_work,
                        image=image_file
                    )
                
                # Always redirect to preview page, which will handle edit vs new mode
                return redirect('nemoonekar:post_images_preview', post_token=sample_work.post_token)
                
            except Exception as e:
                messages.error(request, f'خطا در آپلود تصاویر: {str(e)}')
                return render(request, 'nemoonekar/upload_sample_work_images.html', {
                    'form': form,
                    'sample_work': sample_work,
                    'existing_images': existing_images,
                    'existing_image_count': existing_image_count,
                    'divar_completion_url': settings.DIVAR_COMPLETION_URL
                })
    else:
        form = SampleWorkImageForm()
    
    return render(request, 'nemoonekar/upload_sample_work_images.html', {
        'form': form,
        'sample_work': sample_work,
        'existing_images': existing_images,
        'existing_image_count': existing_image_count,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def upload_single_image(request, work_id):
    """AJAX endpoint for uploading a single image"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    sample_work = get_object_or_404(SampleWork, uuid=work_id, user=request.user_auth)
    
    # Check if we've reached the maximum number of images
    current_image_count = PostImage.objects.filter(sample_work=sample_work).count()
    if current_image_count >= 24:
        return JsonResponse({
            'error': 'حداکثر ۲۴ تصویر مجاز است. لطفاً ابتدا برخی تصاویر را حذف کنید.'
        }, status=400)
    
    # Get the uploaded file
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'هیچ فایلی ارسال نشده است'}, status=400)
    
    image_file = request.FILES['image']
    
    # Validate file size (2.5MB limit)
    if image_file.size > 2621440:  # 2.5MB in bytes
        return JsonResponse({
            'error': f'حجم فایل {image_file.name} بیش از ۲.۵ مگابایت است.'
        }, status=400)
    
    # Validate file extension
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
    file_extension = os.path.splitext(image_file.name)[1].lower().lstrip('.')
    
    if file_extension not in allowed_extensions:
        return JsonResponse({
            'error': f'فرمت فایل {image_file.name} پشتیبانی نمی‌شود. فرمت‌های مجاز: {", ".join(allowed_extensions)}'
        }, status=400)
    
    try:
        # Create the PostImage object
        post_image = PostImage.objects.create(
            sample_work=sample_work,
            image=image_file
        )
        
        return JsonResponse({
            'success': True,
            'image_id': post_image.id,
            'image_url': post_image.image.url,
            'filename': image_file.name,
            'filesize': image_file.size,
            'created_at': post_image.created_at.isoformat(),
            'current_count': current_image_count + 1,
            'max_count': 24
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'خطا در آپلود تصویر: {str(e)}'
        }, status=500)

@session_auth_required
def delete_single_image(request, work_id, image_id):
    """AJAX endpoint for deleting a single image"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    sample_work = get_object_or_404(SampleWork, uuid=work_id, user=request.user_auth)
    post_image = get_object_or_404(PostImage, id=image_id, sample_work=sample_work)
    
    try:
        # Delete the image file from storage
        post_image.image.delete(save=False)
        # Delete the database record
        post_image.delete()
        
        current_count = PostImage.objects.filter(sample_work=sample_work).count()
        
        return JsonResponse({
            'success': True,
            'current_count': current_count,
            'max_count': 24
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'خطا در حذف تصویر: {str(e)}'
        }, status=500)

@session_auth_required
def get_uploaded_images(request, work_id):
    """AJAX endpoint for getting current uploaded images"""
    sample_work = get_object_or_404(SampleWork, uuid=work_id, user=request.user_auth)
    
    images = PostImage.objects.filter(sample_work=sample_work).order_by('created_at')
    
    image_list = []
    for image in images:
        image_list.append({
            'id': image.id,
            'url': image.image.url,
            'filename': os.path.basename(image.image.name),
            'created_at': image.created_at.isoformat()
        })
    
    return JsonResponse({
        'success': True,
        'images': image_list,
        'current_count': len(image_list),
        'max_count': 24
    })

def post_images(request, post_token):
    # For public access, we need to find the sample work by post_token only
    # without requiring user authentication
    # Use all_including_archived() to get archived sample works too
    sample_work = get_object_or_404(SampleWork.all_including_archived(), post_token=post_token)
    
    # Check if the sample work is archived
    if sample_work.is_archived:
        return render(request, 'nemoonekar/post_images.html', {
            'sample_work': sample_work,
            'post_images': [],
            'post_token': post_token,
            'is_archived': True,
            'hide_navigation': True,
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        })
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'nemoonekar/post_images.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token,
        'is_archived': False,
        'hide_navigation': True,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })

@session_auth_required
def post_images_preview(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'nemoonekar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL,
            'post_token': post_token
        }, status=403)
    
    # Check if this is an edit mode (if images already exist or payment is completed)
    is_edit_mode = PostImage.objects.filter(sample_work=sample_work).exists() or Payment.objects.filter(sample_work=sample_work, status='completed').exists()
    
    # Check if there's a successful payment
    has_successful_payment = Payment.objects.filter(sample_work=sample_work, status='completed').exists()
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'nemoonekar/post_images_preview.html', {
        'sample_work': sample_work,
        'post_images': post_images,
        'post_token': post_token,
        'is_edit_mode': is_edit_mode,
        'has_successful_payment': has_successful_payment,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })


@session_auth_required
def pre_payment(request, post_token):
    # For authenticated users, find the sample work by post_token
    sample_work = get_object_or_404(SampleWork, post_token=post_token)
    
    # Check if the current user owns this sample work
    if sample_work.user != request.user_auth:
        return render(request, 'nemoonekar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        }, status=403)
    
    post_images = PostImage.objects.filter(sample_work=sample_work)
    return render(request, 'nemoonekar/pre_payment.html', {
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
        return render(request, 'nemoonekar/permission_denied.html', {
            'message': 'شما اجازه دسترسی به این نمونه کار را ندارید.',
            'divar_completion_url': settings.DIVAR_COMPLETION_URL
        }, status=403)
    
    # Check if ZarinPal merchant ID is configured
    if not settings.ZARINPAL_MERCHANT_ID:
        messages.error(request, 'خطا در پیکربندی درگاه پرداخت. لطفاً با پشتیبانی تماس بگیرید.')
        return redirect('nemoonekar:pre_payment', post_token=post_token)
    
    # Check if payment already exists and is pending
    existing_payment = Payment.objects.filter(
        sample_work=sample_work, 
        status='pending'
    ).first()
    
    if existing_payment:
        # If there's a pending payment, redirect to ZarinPal with existing authority
        if existing_payment.authority:
            payment_url = f"{settings.ZARINPAL_GATEWAY_URL}{existing_payment.authority}"
            return render(request, 'nemoonekar/payment_loading.html', {
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
            return render(request, 'nemoonekar/payment_loading.html', {
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
            return redirect('nemoonekar:pre_payment', post_token=post_token)
            
    except requests.RequestException as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطا در ارتباط با درگاه پرداخت: {str(e)}')
        return redirect('nemoonekar:pre_payment', post_token=post_token)
    except Exception as e:
        payment.status = 'failed'
        payment.save()
        messages.error(request, f'خطای غیرمنتظره: {str(e)}')
        return redirect('nemoonekar:pre_payment', post_token=post_token)

def payment_callback(request):
    """Handle ZarinPal payment callback"""
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    
    if not authority:
        messages.error(request, 'کد مرجع پرداخت یافت نشد.')
        return redirect('nemoonekar:home')
    
    try:
        payment = Payment.objects.get(authority=authority)
    except Payment.DoesNotExist:
        messages.error(request, 'پرداخت یافت نشد.')
        return redirect('nemoonekar:home')
    
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
                return redirect('nemoonekar:payment_success', post_token=payment.sample_work.post_token)
            else:
                # Payment verification failed
                payment.status = 'failed'
                payment.save()
                messages.error(request, f'تایید پرداخت ناموفق بود: {result["errors"]["message"]}')
                return redirect('nemoonekar:payment_failed', post_token=payment.sample_work.post_token)
                
        except requests.RequestException as e:
            payment.status = 'failed'
            payment.save()
            messages.error(request, f'خطا در تایید پرداخت: {str(e)}')
            return redirect('nemoonekar:payment_failed', post_token=payment.sample_work.post_token)
    else:
        # Payment was cancelled or failed
        payment.status = 'cancelled'
        payment.save()
        messages.warning(request, 'پرداخت لغو شد.')
        return redirect('nemoonekar:payment_failed', post_token=payment.sample_work.post_token)

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
    
    return render(request, 'nemoonekar/payment_success.html', {
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
                        "text": "مشاهده آلبوم کامل تصاویر نمونه کار های تایید شده در سایت نمونه کار"
                }},
                {
                    "button_bar": {
                        "title": "آلبوم نمونه کار",
                        "action": {
                            "open_direct_link": f"https://data-lines.ir/nemoonekar/sample-work/post-images/{sample_work.post_token}"
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
            'X-API-Key': settings.OAUTH_APPS_SETTINGS['nemoonekar']['api_key']
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
    
    return render(request, 'nemoonekar/payment_failed.html', {
        'sample_work': sample_work,
        'payment': payment,
        'post_token': post_token,
        'divar_completion_url': settings.DIVAR_COMPLETION_URL
    })
