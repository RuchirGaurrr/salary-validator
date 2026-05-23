"""
config/urls.py — Master URL router"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),               # Built-in admin panel
    path("api/", include("validation.urls")),       # Our API lives here
]
