from django.urls import path
from . import views

app_name = 'ostadkar'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.oauth_login, name='oauth_login'),
    path('callback/', views.oauth_callback, name='oauth_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
] 