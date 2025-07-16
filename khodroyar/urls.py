from django.urls import path
from . import views

app_name = 'khodroyar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('oauth/login/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('pre-payment/', views.pre_payment, name='pre_payment'),
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    
    # Chatbot API endpoints
    path('api/chat/receive/', views.receive_message, name='receive_message'),
] 