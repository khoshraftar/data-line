from django.urls import path, include
from .admin_review import review_site

urlpatterns = [
    path('', review_site.urls),
] 