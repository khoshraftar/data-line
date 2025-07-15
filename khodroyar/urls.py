from django.urls import path
from . import views

app_name = 'khodroyar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('oauth/login/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Chatbot API endpoints
    path('api/chat/receive/', views.receive_message, name='receive_message'),
] 