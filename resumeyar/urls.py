from django.urls import path
from . import views

app_name = 'resumeyar'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-resumes/', views.my_resumes, name='my_resumes'),
    path('create/', views.create_resume, name='create_resume'),
    path('edit/<int:resume_id>/', views.edit_resume, name='edit_resume'),
    path('templates/', views.resume_templates, name='resume_templates'),
    path('settings/', views.settings, name='settings'),
] 