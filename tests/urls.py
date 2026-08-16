"""URLs for the test project."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("og-images/", include("html2img_django.urls")),
]
