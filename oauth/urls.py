from django.urls import path
from . import views

app_name = 'oauth'

urlpatterns = [
    path('', views.OAuthLoginView.as_view(), name='login'),
    path('redirect/', views.OAuthRedirectView.as_view(), name='login_redirect'),
    path('callback/', views.OAuthCallbackView.as_view(), name='callback'),
] 