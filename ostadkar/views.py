from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode
from django.contrib import messages
from functools import wraps
from .models import UserAuth, PostImage, SampleWork
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
            sample_work = form.save(commit=False)
            sample_work.user = request.user_auth
            sample_work.post_token = post_token
            sample_work.save()
            messages.success(request, 'Sample work added successfully!')
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
                
                messages.success(request, f'{len(files)} تصویر با موفقیت آپلود شد!')
                return redirect('ostadkar:post_images', post_token=sample_work.post_token)
                
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
def sample_works(request):
    sample_works = SampleWork.objects.filter(user=request.user_auth)
    return render(request, 'ostadkar/sample_works.html', {
        'sample_works': sample_works
    })