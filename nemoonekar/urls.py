from django.urls import path
from . import views

app_name = 'nemoonekar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('login/<str:post_token>/', views.login, name='login_with_token'),
    path('oauth/login/<str:post_token>/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('sample-work/add/<str:post_token>/', views.add_sample_work, name='add_sample_work'),
    path('sample-work/upload-images/<uuid:work_id>/', views.upload_sample_work_images, name='upload_sample_work_images'),
    path('sample-work/upload-single-image/<uuid:work_id>/', views.upload_single_image, name='upload_single_image'),
    path('sample-work/delete-image/<uuid:work_id>/<int:image_id>/', views.delete_single_image, name='delete_single_image'),
    path('sample-work/get-images/<uuid:work_id>/', views.get_uploaded_images, name='get_uploaded_images'),
    path('sample-work/post-images/<str:post_token>/', views.post_images, name='post_images'),
    path('sample-work/post-images-preview/<str:post_token>/', views.post_images_preview, name='post_images_preview'),
    path('sample-work/pre-payment/<str:post_token>/', views.pre_payment, name='pre_payment'),
    path('sample-work/initiate-payment/<str:post_token>/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/success/<str:post_token>/', views.payment_success, name='payment_success'),
    path('payment/failed/<str:post_token>/', views.payment_failed, name='payment_failed'),
    # This should be last to avoid catching other URLs
    path('<str:post_token>/', views.home, name='home_with_token'),
] 