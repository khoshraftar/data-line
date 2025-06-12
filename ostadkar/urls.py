from django.urls import path
from . import views

app_name = 'ostadkar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('oauth/login/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('sample-works/', views.sample_works, name='sample_works'),
    path('sample-works/add/', views.add_sample_work, name='add_sample_work'),
    path('sample-works/<int:work_id>/edit/', views.edit_sample_work, name='edit_sample_work'),
    path('sample-works/<int:work_id>/delete/', views.delete_sample_work, name='delete_sample_work'),
] 