"""URLs for the preview views.

Include them from your project's ``urls.py``:

.. code-block:: python

    urlpatterns = [
        path("og-images/", include("html2img_django.urls")),
    ]

That gives you ``/og-images/preview/`` for a sample card and
``/og-images/preview/blog.Post/1/`` for a real object. Both are staff-only.
"""

from __future__ import annotations

from django.urls import path

from html2img_django import views

app_name = "html2img_django"

urlpatterns = [
    path("preview/", views.preview, name="preview"),
    path("preview/<str:label>/<str:pk>/", views.preview_object, name="preview-object"),
]
