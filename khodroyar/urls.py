from django.urls import path
from . import views

app_name = 'khodroyar'

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.settings, name='settings'),
] 