from django.urls import path
from . import views

app_name = 'resumeyar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('oauth/login/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-resumes/', views.my_resumes, name='my_resumes'),
    path('create-resume/', views.create_resume, name='create_resume'),
    path('edit-resume/<int:resume_id>/', views.edit_resume, name='edit_resume'),
    path('templates/', views.resume_templates, name='templates'),
    path('settings/', views.settings, name='settings'),
] 