from django.urls import path
from . import views

app_name = 'ostadkar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('oauth/login/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('sample-work/add/', views.add_sample_work, name='add_sample_work'),
    path('sample-work/upload-images/<uuid:work_id>/', views.upload_sample_work_images, name='upload_sample_work_images'),
    path('sample-work/post-images/<str:post_token>/', views.post_images, name='post_images'),
    path('sample-works/', views.sample_works, name='sample_works'),
] 