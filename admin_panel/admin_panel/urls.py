from django.contrib import admin
from django.urls import path
from django_otp.admin import OTPAdminSite

from . import settings

if not settings.DEBUG:
    admin.site.__class__ = OTPAdminSite

urlpatterns = [
    path("admin/", admin.site.urls),
]
